"""
Rayna Tours API client and tour card formatting.
"""
from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import quote  # noqa: F401

import aiohttp
from cachetools import TTLCache

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://data-projects-flax.vercel.app/api"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

KNOWN_LOCATIONS = [
    "Dubai", "Abu Dhabi", "Sharjah", "Ras Al Khaimah", "Ajman",
    "Jeddah", "Riyadh", "Makkah", "Dammam", "Madinah",
    "Muscat", "Khasab",
    "Bangkok", "Phuket", "Krabi", "Koh Samui", "Pattaya", "Chiang Mai",
    "Bali", "Jakarta",
    "Kuala Lumpur", "Langkawi", "Penang",
    "Singapore",
]

# Map country/region/state names to their cities (for holiday lookups)
REGION_TO_CITIES: dict[str, list[str]] = {
    "thailand": ["Bangkok", "Phuket", "Koh Samui"],
    "kerala": ["MUNNAR", "Madurai", "Mysore"],
    "india": ["Delhi", "Mumbai", "Jaipur", "Darjeeling", "Gangtok", "Leh", "Port Blair", "Jaisalmer", "Udaipur", "MUNNAR", "Madurai", "Mysore", "Srinagar"],
    "uae": ["Dubai City", "Abu Dhabi", "Ras al Khaimah"],
    "emirates": ["Dubai City", "Abu Dhabi", "Ras al Khaimah"],
    "turkey": ["Istanbul", "Cappadocia"],
    "saudi": ["Jeddah", "Makkah", "Dammam", "Riyadh", "TABUK", "Al Ula", "UMLUJ"],
    "saudi arabia": ["Jeddah", "Makkah", "Dammam", "Riyadh", "TABUK", "Al Ula", "UMLUJ"],
    "sri lanka": ["Colombo", "Kandy"],
    "vietnam": ["Danang", "Hanoi", "Phu Quoc"],
    "malaysia": ["Kuala Lumpur"],
    "indonesia": ["Bali"],
    "japan": ["Tokyo"],
    "europe": ["Paris", "Rome", "Barcelona", "Madrid", "Amsterdam", "Prague", "Vienna", "Zurich", "Berlin", "Frankfurt", "Budapest", "Riga", "Athens", "Rovaniemi"],
    "rajasthan": ["Jaipur", "Jaisalmer", "Udaipur"],
    "kashmir": ["Srinagar"],
    "ladakh": ["Leh"],
    "andaman": ["Port Blair"],
    "georgia": ["Tbilisi"],
    "egypt": ["Cairo"],
    "maldives": ["Maldives"],
    "singapore": ["Singapore City"],
    "russia": ["Moscow"],
    "uzbekistan": ["Tashkent"],
    # Indian states/regions
    "sikkim": ["Gangtok"],
    "west bengal": ["Darjeeling"],
    "darjeeling": ["Darjeeling"],
    "himachal": ["MUNNAR"],
    "tamil nadu": ["Madurai", "Mysore"],
    "karnataka": ["Mysore"],
    "goa": ["Mumbai"],
    # Middle East / Africa
    "azerbaijan": ["Baku"],
    "armenia": ["Yerevan"],
    "bahrain": ["Manama"],
    "jordan": ["Amman"],
    "oman": ["Salalah"],
    "kenya": ["Nairobi"],
    "mauritius": ["Mauritius"],
    "seychelles": ["Mahe"],
    # Central / East Asia
    "kazakhstan": ["Almaty"],
    "kyrgyzstan": ["Bishkek"],
    "philippines": ["Manila"],
    # European countries (standalone)
    "spain": ["Barcelona", "Madrid"],
    "france": ["Paris"],
    "italy": ["Rome"],
    "germany": ["Berlin", "Frankfurt"],
    "czech republic": ["Prague"],
    "austria": ["Vienna"],
    "switzerland": ["Zurich"],
    "netherlands": ["Amsterdam"],
    "hungary": ["Budapest"],
    "latvia": ["Riga"],
    "greece": ["Athens"],
    "finland": ["Rovaniemi"],
}

# Keywords in tour names that hint at a specific city (for auto-detection)
TOUR_NAME_CITY_HINTS: dict[str, str] = {
    "pink city": "Jaipur",
    "tiger safari": "Jaipur",
    "jaipur": "Jaipur",
    "rajasthan": "Jaipur",
    "ranthambore": "Jaipur",
    "taj mahal": "Delhi",
    "agra": "Delhi",
    "delhi": "Delhi",
    "golden triangle": "Delhi",
    "kerala": "MUNNAR",
    "munnar": "MUNNAR",
    "kashmir": "Srinagar",
    "srinagar": "Srinagar",
    "ladakh": "Leh",
    "leh": "Leh",
    "darjeeling": "Darjeeling",
    "gangtok": "Gangtok",
    "sikkim": "Gangtok",
    "andaman": "Port Blair",
    "port blair": "Port Blair",
    "manali": "Manali",
    "shimla": "Shimla",
    "udaipur": "Udaipur",
    "jaisalmer": "Jaisalmer",
    "amritsar": "Amritsar",
    "golden temple": "Amritsar",
    "mysore": "Mysore",
    "madurai": "Madurai",
    "bali": "Bali",
    "bangkok": "Bangkok",
    "phuket": "Phuket",
    "singapore": "Singapore City",
    "kuala lumpur": "Kuala Lumpur",
    "istanbul": "Istanbul",
    "cappadocia": "Cappadocia",
    "dubai": "Dubai",
    "abu dhabi": "Abu Dhabi",
    "sharjah": "Sharjah",
    "muscat": "Muscat",
    "jeddah": "Jeddah",
    "riyadh": "Riyadh",
    "makkah": "Makkah",
    "cairo": "Cairo",
    "tbilisi": "Tbilisi",
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Desert Safari": ["desert", "safari", "dune", "camel"],
    "City Tour": ["city tour", "sightseeing", "hop on", "hop off"],
    "Theme Park": ["theme park", "ferrari world", "legoland", "motiongate", "img", "universal", "fantasea"],
    "Water Park": ["aquaventure", "waterworld", "water park", "splash"],
    "Adventure": ["zipline", "skydiving", "bungee", "quad bike", "buggy", "mountain", "trek", "jais flight", "atv", "rafting", "swing", "paragliding", "parasailing", "jet ski", "flyboard", "wakeboard", "surf", "diving", "climb", "kayak", "canyoning", "rappel", "adventure"],
    "Cruise": ["cruise", "dhow", "dinner cruise", "boat", "sailing"],
    "Attraction": ["burj khalifa", "museum", "aquarium", "frame", "tower", "flyer", "cable car"],
    "Cultural": ["mosque", "heritage", "cultural", "traditional", "temple", "palace", "fort"],
    "Religious": ["umrah", "religious", "spiritual", "holy"],
    "Island": ["island", "beach", "marine park", "coral", "snorkeling"],
    "Entertainment": ["show", "cabaret", "nightlife", "entertainment"],
    "Nature": ["gardens", "nature", "wildlife", "elephant", "rice terrace"],
    "Shopping": ["shopping", "mall", "souq", "market"],
    "Food": ["food", "culinary", "street food", "dining"],
}

CATEGORY_EMOJIS: dict[str, str] = {
    "desert safari": "\U0001f3dc\ufe0f",
    "adventure": "\U0001f681",
    "cultural": "\U0001f3db\ufe0f",
    "religious": "\U0001f54c",
    "theme park": "\U0001f3a2",
    "water park": "\U0001f30a",
    "cruise": "\U0001f6a2",
    "island": "\U0001f3dd\ufe0f",
    "entertainment": "\U0001f3ad",
    "nature": "\U0001f33a",
    "shopping": "\U0001f6cd\ufe0f",
    "food": "\U0001f35c",
    "attraction": "\U0001f5fc",
    "city tour": "\U0001f3d9\ufe0f",
}

HIGHLIGHT_KEYWORDS = [
    "Burj Khalifa", "Dubai Mall", "Palm Jumeirah", "Dubai Marina", "Desert Safari",
    "Camel Riding", "Dune Bashing", "BBQ Dinner", "Belly Dance", "Henna Painting",
    "Gold Souk", "Spice Souk", "Dubai Creek", "Miracle Garden", "Global Village",
    "Sheikh Zayed Mosque", "Ferrari World", "Yas Waterworld", "Louvre Abu Dhabi",
    "Corniche", "Masmak Fortress", "Kingdom Centre", "Historical District",
    "Grand Mosque", "Twin Forts", "Mutrah Souq", "Dhow Cruise",
    "Floating Markets", "Grand Palace", "Elephant Sanctuary", "Phi Phi Island",
    "Fantasea", "Tiffany Show", "Four Islands", "Tiger Temple",
    "Mount Batur", "Sunrise Trek", "Rice Terraces", "Water Temple",
    "Petronas Towers", "Batu Caves", "Street Food", "Cable Car",
    "Singapore Flyer", "Gardens by the Bay", "Universal Studios", "Night Safari",
    "Snorkeling", "Sunset Cruise", "Island Hopping", "Temple Tour",
]



def detect_city_from_tour_name(tour_name: str) -> str | None:
    """Detect city from keywords in a tour name using TOUR_NAME_CITY_HINTS."""
    name_lower = tour_name.lower()
    # Try longest keyword first for more specific matches
    sorted_hints = sorted(TOUR_NAME_CITY_HINTS.items(), key=lambda x: len(x[0]), reverse=True)
    for keyword, city in sorted_hints:
        if keyword in name_lower:
            return city
    return None


def _is_transfers_only(tours: list[dict]) -> bool:
    if not tours:
        return False
    transfer_kws = ("transfer", "pickup", "drop")
    return all(
        any(kw in (t.get("name", "") + t.get("title", "") + t.get("category", "")).lower() for kw in transfer_kws)
        for t in tours
    )


# ---------------------------------------------------------------------------
# Tour card formatting
# ---------------------------------------------------------------------------

def _extract_price(raw: Any) -> float:
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).replace(",", "")
    s = re.sub(r"[A-Za-z$€£¥]", "", s).strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _categorize_activity(name: str) -> str:
    name_lower = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category
    return "Experience"


def _extract_location(name: str) -> str:
    name_lower = name.lower()
    for loc in KNOWN_LOCATIONS:
        if loc.lower() in name_lower:
            return loc
    return "Middle East"


def _extract_duration(text: str) -> str | None:
    if not text:
        return None
    patterns = [
        (r"(\d+)\s*hours?", lambda m: f"{m.group(1)} hours"),
        (r"(\d+)\s*hrs?", lambda m: f"{m.group(1)} hrs"),
        (r"(\d+)\s*days?", lambda m: f"{m.group(1)} days"),
        (r"full\s*day", lambda _: "Full Day"),
        (r"half\s*day", lambda _: "Half Day"),
    ]
    for pattern, formatter in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return formatter(m)
    return None


def _extract_highlights(text: str) -> list[str] | None:
    if not text:
        return None
    found = [kw for kw in HIGHLIGHT_KEYWORDS if kw.lower() in text.lower()]
    return found[:4] if found else None


def _calc_rpoints(price: float) -> int:
    return int(round(price * 0.01 / 100) * 100)


def _build_tour_url(slug: str | None) -> str:
    if not slug:
        return "https://www.raynatours.com"
    if slug.startswith("http"):
        return slug
    return f"https://www.raynatours.com/{slug.lstrip('/')}"


def _extract_image(raw: dict[str, Any]) -> str:
    """Extract image URL from various API response formats."""
    # Flat fields
    img = raw.get("image")
    if isinstance(img, dict):
        img = img.get("src", "")
    img = img or raw.get("imageUrl") or raw.get("thumbnail") or raw.get("banner_image") or raw.get("bannerImage") or ""
    if img:
        return img
    # Rayna holiday format: imageProps[0].image.src
    image_props = raw.get("imageProps")
    if isinstance(image_props, list) and image_props:
        first = image_props[0]
        if isinstance(first, dict):
            inner = first.get("image", {})
            if isinstance(inner, dict):
                return inner.get("src", "")
    return ""


def _extract_url(raw: dict[str, Any]) -> str:
    """Extract product URL from various API response formats."""
    def _ensure_absolute(u: str) -> str:
        if not u:
            return ""
        return u if u.startswith("http") else f"https://www.raynatours.com{u}" if u.startswith("/") else f"https://www.raynatours.com/{u}"

    # Direct url field
    url = raw.get("url") or ""
    if url:
        return _ensure_absolute(url)
    # productUrl (can be dict with href, or string)
    product_url = raw.get("productUrl")
    if isinstance(product_url, dict):
        href = product_url.get("href", "") or product_url.get("url", "")
        if href:
            return _ensure_absolute(href)
    elif product_url and isinstance(product_url, str):
        return _ensure_absolute(product_url)
    # Rayna holiday format: productLink.href
    link = raw.get("productLink")
    if isinstance(link, dict):
        href = link.get("href", "") or link.get("url", "")
        if href:
            return _ensure_absolute(href)
    # Additional URL fields
    for key in ("detailUrl", "pageUrl", "link", "detailLink"):
        val = raw.get(key)
        if val and isinstance(val, str):
            return _ensure_absolute(val)
        if isinstance(val, dict):
            href = val.get("href", "") or val.get("url", "")
            if href:
                return _ensure_absolute(href)
    # source — only use if it looks like a specific product page (3+ path segments)
    source = raw.get("source", "")
    if source and isinstance(source, str):
        path = source.replace("https://www.raynatours.com", "").strip("/")
        if path.count("/") >= 2:
            return _ensure_absolute(source)
    # slug fallback
    slug = raw.get("slug") or raw.get("urlSlug") or ""
    if slug:
        return _build_tour_url(slug)
    return "https://www.raynatours.com"


def _extract_holiday_duration(raw: dict[str, Any]) -> str | None:
    """Extract duration, handling holiday-specific noOfDays/noOfNights fields."""
    # Standard duration field
    dur_raw = raw.get("duration")
    if isinstance(dur_raw, list) and dur_raw:
        return dur_raw[0].get("label") if isinstance(dur_raw[0], dict) else str(dur_raw[0])
    if isinstance(dur_raw, str) and dur_raw:
        return dur_raw

    # Holiday format: noOfNights/noOfDays
    # API may return pre-formatted strings like "3N / 4D" or plain numbers
    nights = raw.get("noOfNights")
    days = raw.get("noOfDays")
    if nights or days:
        # If already formatted (e.g. "3N / 4D"), return as-is
        nights_str = str(nights) if nights else ""
        days_str = str(days) if days else ""
        if nights_str and ("N" in nights_str.upper() or "D" in nights_str.upper()):
            return nights_str
        if days_str and ("N" in days_str.upper() or "D" in days_str.upper()):
            return days_str
        # Build from numbers
        parts = []
        if nights_str:
            parts.append(f"{nights_str}N")
        if days_str:
            parts.append(f"{days_str}D")
        return "/".join(parts)

    return _extract_duration(raw.get("description", "") or raw.get("name", "") or "")


def format_tour_card(raw: dict[str, Any], city_name: str = "") -> dict[str, Any]:
    """Convert a raw API product into a standardised TourCard dict."""
    # Price extraction chain — handle holiday fields (priceCents, normalPrice, salePrice)
    current_price = _extract_price(
        raw.get("discountedAmount")
        or raw.get("salePrice")
        or raw.get("discountedPrice")
        or raw.get("price")
        or raw.get("priceCents")
        or raw.get("current_price")
        or raw.get("amount")
        or 0
    )
    original_price = _extract_price(
        raw.get("amount")
        or raw.get("normalPrice")
        or raw.get("originalPrice")
        or raw.get("original_price")
        or raw.get("normal_price")
        or raw.get("priceCents")
    )
    if original_price <= current_price:
        original_price = None

    discount = None
    discount_pct = None
    if original_price and original_price > current_price > 0:
        discount = round(original_price - current_price, 2)
        discount_pct = round((discount / original_price) * 100)

    title = raw.get("name") or raw.get("title") or raw.get("packageName") or raw.get("productName") or "Tour"
    location = raw.get("city") or raw.get("cityName") or raw.get("location") or city_name or _extract_location(title)
    category_raw = raw.get("category") or raw.get("variant") or raw.get("productCategory") or raw.get("type") or ""
    if isinstance(category_raw, list):
        category_raw = category_raw[0].get("label", "") if category_raw else ""
    category = category_raw or _categorize_activity(title)

    # Duration (with holiday support)
    duration = _extract_holiday_duration(raw)

    # Image (with holiday imageProps support)
    image = _extract_image(raw)

    # Rating
    rating_raw = raw.get("averageRating") or raw.get("rating")
    rating = None
    if rating_raw is not None:
        try:
            rating = float(rating_raw)
        except (ValueError, TypeError):
            pass

    # Highlights
    highlights = raw.get("highlights")
    if not highlights:
        highlights = _extract_highlights(raw.get("description", "") or title)

    # URL (with holiday productLink.href support)
    url = _extract_url(raw)
    slug = url.replace("https://www.raynatours.com/", "").replace("https://www.raynatours.com", "")

    return {
        "id": str(raw.get("id") or raw.get("productId") or raw.get("slug") or f"tour_{id(raw)}"),
        "title": title,
        "slug": slug,
        "image": image,
        "location": location,
        "category": category,
        "originalPrice": original_price,
        "currentPrice": current_price,
        "currency": raw.get("currency", "AED"),
        "discount": discount,
        "discountPercentage": discount_pct,
        "isRecommended": rating is not None and rating >= 4.8 or bool(raw.get("is_featured")),
        "isNew": bool(raw.get("is_new")),
        "rPoints": _calc_rpoints(current_price),
        "rating": rating,
        "reviewCount": raw.get("reviewCount"),
        "duration": duration,
        "highlights": highlights,
        "url": url,
    }


# ---------------------------------------------------------------------------
# Enriched-feed formatters (scraped data → TourCard / TourDetailOutput)
# ---------------------------------------------------------------------------


def _enriched_image(raw: dict[str, Any]) -> str:
    """Extract best image from an enriched-feed product."""
    img = raw.get("image") or ""
    if img:
        return img
    all_imgs = raw.get("all_image_links") or ""
    if all_imgs and isinstance(all_imgs, str):
        return all_imgs.split(",")[0].strip()
    return ""


def _enriched_price(raw: dict[str, Any]) -> tuple[float, float | None]:
    """Return (current_price, original_price|None) from enriched-feed fields."""
    current = _extract_price(
        raw.get("price_discountedPrice")
        or raw.get("salePrice")
        or raw.get("price_totalPrice")
        or raw.get("normalPrice")
        or raw.get("discountedAmount")
        or raw.get("amount")
        or 0,
    )
    original = _extract_price(
        raw.get("normalPrice")
        or raw.get("price_totalPrice")
        or raw.get("amount")
        or 0,
    )
    if original <= current:
        original = None
    return current, original


def _enriched_url(raw: dict[str, Any]) -> str:
    """Extract URL from enriched-feed product."""
    url = raw.get("detail_shareUrl") or raw.get("price_bookingUrl") or raw.get("url") or ""
    if url and not url.startswith("http"):
        url = f"https://www.raynatours.com/{url.lstrip('/')}"
    return url or "https://www.raynatours.com"


def _enriched_rating(raw: dict[str, Any]) -> tuple[float | None, int | None]:
    """Return (rating, review_count) from enriched-feed fields."""
    rating = None
    # Try review_averageRating first, then listing_rating (city enriched-feed)
    for key in ("review_averageRating", "listing_rating", "averageRating", "rating"):
        r = raw.get(key)
        if r is not None:
            try:
                val = float(r)
                if val > 0:
                    rating = val
                    break
            except (ValueError, TypeError):
                pass
    review_count = None
    # Try review_totalCount first, then listing_reviewCount (city enriched-feed)
    for key in ("review_totalCount", "listing_reviewCount", "reviewCount"):
        rc = raw.get(key)
        if rc is not None:
            try:
                val = int(float(rc))
                if val > 0:
                    review_count = val
                    break
            except (ValueError, TypeError):
                pass
    return rating, review_count


def format_enriched_tour_card(raw: dict[str, Any], city_name: str = "") -> dict[str, Any]:
    """Convert an enriched-feed product into a standardised TourCard dict."""
    title = raw.get("detail_title") or raw.get("name") or "Tour"
    current_price, original_price = _enriched_price(raw)

    discount = None
    discount_pct = None
    if original_price and original_price > current_price > 0:
        discount = round(original_price - current_price, 2)
        discount_pct = round((discount / original_price) * 100)

    location = raw.get("city") or raw.get("location_title") or city_name or ""
    cat_raw = raw.get("type") or raw.get("price_variant") or ""
    category = cat_raw.capitalize() if cat_raw else _categorize_activity(title)

    duration = raw.get("amenity_duration") or None
    if not duration:
        duration = _extract_duration(raw.get("description_text", "") or title)
    if not duration and raw.get("amenity_nights"):
        duration = raw["amenity_nights"]

    image = _enriched_image(raw)
    rating, review_count = _enriched_rating(raw)
    url = _enriched_url(raw)
    slug = url.replace("https://www.raynatours.com/", "").replace("https://www.raynatours.com", "")
    highlights = _extract_highlights(raw.get("description_text", "") or title)

    return {
        "id": str(raw.get("productId") or raw.get("id") or f"tour_{id(raw)}"),
        "title": title,
        "slug": slug,
        "image": image,
        "location": location,
        "category": category,
        "originalPrice": original_price,
        "currentPrice": current_price,
        "currency": raw.get("currency") or raw.get("price_currency") or "AED",
        "discount": discount,
        "discountPercentage": discount_pct,
        "isRecommended": rating is not None and rating >= 4.8,
        "isNew": False,
        "rPoints": _calc_rpoints(current_price),
        "rating": rating,
        "reviewCount": review_count,
        "duration": duration,
        "highlights": highlights,
        "url": url,
    }


def _parse_pipe_section_items(section: str) -> list[str]:
    """Split a pipe-section into individual list items, handling various delimiters."""
    # Remove common header words like "Inclusions:", "Exclusions:", etc.
    cleaned = re.sub(r"^(inclusions?|exclusions?|what'?s\s+included|what'?s\s+not\s+included|not\s+included)\s*:?\s*", "", section, flags=re.IGNORECASE).strip()
    if not cleaned:
        return []
    # Split on newlines, bullets, numbered lists
    items = re.split(r"[\n•\u2022\u2023\u25aa\u25cf]|\d+[.)]\s", cleaned)
    return [s.strip() for s in items if s.strip() and len(s.strip()) > 2][:12]


def format_enriched_tour_detail(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert an enriched-feed product into a TourDetailOutput dict."""
    title = raw.get("detail_title") or raw.get("name") or "Tour"
    description = raw.get("description_text") or ""

    # Parse inclusions / exclusions from description_text (pipe-separated sections)
    # Format: section0 = description | section1 = inclusions | section2 = exclusions | section3 = redemption | ...
    inclusions: list[str] = []
    exclusions: list[str] = []
    clean_desc = description
    if description and "|" in description:
        sections = [p.strip() for p in description.split("|")]
        # Section 0 = main description
        clean_desc = sections[0] if sections else description
        # Section 1 = inclusions (if exists)
        if len(sections) > 1 and sections[1]:
            inclusions = _parse_pipe_section_items(sections[1])
        # Section 2 = exclusions (if exists)
        if len(sections) > 2 and sections[2]:
            exclusions = _parse_pipe_section_items(sections[2])

    if len(clean_desc) > 2000:
        clean_desc = clean_desc[:2000]

    # Highlights from amenities
    highlights: list[str] = []
    amenity_all = raw.get("amenities_all") or ""
    if amenity_all:
        highlights = [a.strip() for a in amenity_all.split("|") if a.strip()][:8]
    if not highlights:
        highlights = _extract_highlights(description or title) or []

    current_price, original_price = _enriched_price(raw)
    image = _enriched_image(raw)
    rating, review_count = _enriched_rating(raw)
    url = _enriched_url(raw)

    location = raw.get("city") or raw.get("location_title") or raw.get("location_address") or ""
    cat_raw = raw.get("type") or raw.get("price_variant") or ""
    category = cat_raw.capitalize() if cat_raw else _categorize_activity(title)
    duration = raw.get("amenity_duration") or _extract_duration(description or title)

    return {
        "title": title,
        "description": clean_desc,
        "image": image,
        "location": location,
        "category": category,
        "currentPrice": current_price,
        "originalPrice": original_price,
        "currency": raw.get("currency") or raw.get("price_currency") or "AED",
        "duration": duration,
        "highlights": highlights,
        "inclusions": inclusions,
        "exclusions": exclusions,
        "rating": rating,
        "reviewCount": review_count,
        "url": url,
        "rPoints": _calc_rpoints(current_price),
    }


# ---------------------------------------------------------------------------
# Recursive product finder (handles various API response shapes)
# ---------------------------------------------------------------------------


def _is_product_item(item: dict[str, Any]) -> bool:
    """Check if a dict looks like a real product (tour, holiday, cruise, etc.)."""
    has_name = bool(
        item.get("name") or item.get("title") or item.get("packageName")
    )
    has_price = any(
        item.get(k)
        for k in (
            "normalPrice", "salePrice", "price", "currentPrice",
            "originalPrice", "priceCents", "discountedPrice",
            "amount", "discountedAmount",
        )
    )
    has_url = bool(
        item.get("url") or item.get("productUrl") or item.get("productLink")
    )
    return has_name and (has_price or has_url)


def _find_product_list(data: Any, depth: int = 0) -> list[dict[str, Any]]:
    """Recursively search for a list of product-like dicts in nested API response."""
    if depth > 6:
        return []

    if isinstance(data, list) and data:
        if isinstance(data[0], dict) and _is_product_item(data[0]):
            return data
        for item in data:
            if isinstance(item, dict):
                result = _find_product_list(item, depth + 1)
                if result:
                    return result
        return []

    if isinstance(data, dict):
        # Check known keys first
        for key in ("products", "packages", "holidays", "cruises", "yachts", "items", "results"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict) and _is_product_item(val[0]):
                return val
        # Recurse into "data" key
        for key in ("data",):
            val = data.get(key)
            if isinstance(val, (dict, list)):
                result = _find_product_list(val, depth + 1)
                if result:
                    return result

    return []


# ---------------------------------------------------------------------------
# Async API Client
# ---------------------------------------------------------------------------

_city_cache: TTLCache = TTLCache(maxsize=32, ttl=300)  # 5 min


class RaynaApiClient:
    """Async HTTP client for the Rayna Tours API."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def _get(self, session: aiohttp.ClientSession, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with session.get(url, params=params, timeout=REQUEST_TIMEOUT) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_available_cities(self, session: aiohttp.ClientSession, product_type: str = "tour") -> list[dict]:
        cache_key = f"cities_{product_type}"
        if cache_key in _city_cache:
            return _city_cache[cache_key]

        data = await self._get(session, "available-cities", {"productType": product_type})
        cities: list[dict] = []
        try:
            options = data.get("data", {}).get("data", {}).get("options", [])
            for opt in options:
                for city in opt.get("cities", []):
                    cities.append({
                        "id": city.get("id"),
                        "name": city.get("name", ""),
                        "country": opt.get("name", ""),
                    })
        except Exception:
            pass
        _city_cache[cache_key] = cities
        return cities

    async def resolve_city_id(
        self, session: aiohttp.ClientSession, city_name: str, product_type: str = "tour"
    ) -> int | None:
        """Resolve city name to ID. Checks given product_type first, then falls back to others."""
        info = await self.resolve_city_info(session, city_name, product_type)
        return info[0] if info else None

    async def resolve_city_info(
        self, session: aiohttp.ClientSession, city_name: str, product_type: str = "tour"
    ) -> tuple[int, str, str] | None:
        """Resolve city name to (city_id, city_name, country_name). Returns None if not found."""
        city_lower = city_name.lower().strip()

        # Try the requested product type first, then fall back to others
        product_types = [product_type] + [
            pt for pt in ("holiday", "tour", "cruise", "yacht") if pt != product_type
        ]

        for pt in product_types:
            cities = await self.get_available_cities(session, pt)
            # Exact match
            for c in cities:
                if c["name"].lower() == city_lower:
                    return (c["id"], c["name"], c.get("country", ""))
            # Fuzzy match
            for c in cities:
                if city_lower in c["name"].lower() or c["name"].lower() in city_lower:
                    return (c["id"], c["name"], c.get("country", ""))
        return None

    async def resolve_region_city_ids(
        self, session: aiohttp.ClientSession, name: str, product_type: str = "holiday"
    ) -> list[tuple[int, str]]:
        """Resolve a region/country/state name to a list of (city_id, city_name) pairs.

        First tries direct city match, then falls back to REGION_TO_CITIES mapping.
        """
        # Try direct city match first
        city_id = await self.resolve_city_id(session, name, product_type)
        if city_id:
            return [(city_id, name)]

        # Try region/country mapping
        region_lower = name.lower().strip()
        city_names = REGION_TO_CITIES.get(region_lower, [])
        if not city_names:
            # Fuzzy region match
            for region_key, city_list in REGION_TO_CITIES.items():
                if region_lower in region_key or region_key in region_lower:
                    city_names = city_list
                    break

        if not city_names:
            return []

        results: list[tuple[int, str]] = []
        for cn in city_names:
            cid = await self.resolve_city_id(session, cn, product_type)
            if cid:
                results.append((cid, cn))
        return results

    async def get_city_products(self, session: aiohttp.ClientSession, city_id: int, limit: int = 20) -> list[dict]:
        data = await self._get(session, "city/products", {"cityId": city_id})
        try:
            products = _find_product_list(data)
            if products:
                return products[:limit]
        except Exception:
            pass
        return []

    async def get_city_holiday(self, session: aiohttp.ClientSession, city_id: int) -> list[dict]:
        data = await self._get(session, "city/holiday", {"cityId": city_id})
        try:
            products = _find_product_list(data)
            if products:
                return products[:20]
        except Exception:
            pass
        return []

    async def get_city_yacht(self, session: aiohttp.ClientSession, city_id: int, limit: int = 20) -> list[dict]:
        data = await self._get(session, "city/yacht", {"cityId": city_id})
        try:
            products = _find_product_list(data)
            if products:
                return products[:limit]
        except Exception:
            pass
        return []

    async def get_city_cruise(self, session: aiohttp.ClientSession, city_id: int, limit: int = 20) -> list[dict]:
        data = await self._get(session, "city/cruise", {"cityId": city_id})
        try:
            products = _find_product_list(data)
            if products:
                return products[:limit]
        except Exception:
            pass
        return []

    async def get_enriched_product(self, session: aiohttp.ClientSession, product_id: int | str, product_type: str = "tour") -> dict | None:
        """Fetch a single enriched product via the enriched-feed endpoint."""
        data = await self._get(session, "enriched-feed", {
            "productId": str(product_id),
            "productType": product_type,
            "format": "json",
        })
        if isinstance(data, dict):
            products = data.get("products", [])
            if isinstance(products, list) and products:
                return products[0]
        return None

    async def get_enriched_city_products(
        self,
        session: aiohttp.ClientSession,
        city_id: int,
        city_name: str,
        country_name: str,
        product_type: str = "tour",
        limit: int = 200,
    ) -> list[dict]:
        """Fetch enriched products for a city via the enriched-feed endpoint.

        Calls /enriched-feed?cityId=X&cityName=Y&countryName=Z&types=TYPE&format=json
        Returns fully enriched products with scraped images, reviews, descriptions.
        """
        data = await self._get(session, "enriched-feed", {
            "cityId": str(city_id),
            "cityName": city_name,
            "countryName": country_name,
            "types": product_type,
            "format": "json",
        })
        products: list[dict] = []
        if isinstance(data, dict):
            products = data.get("products", [])
        elif isinstance(data, list):
            products = data
        if not isinstance(products, list):
            products = []
        # Filter to only enriched products
        enriched = [p for p in products if isinstance(p, dict) and p.get("_enriched")]
        if enriched:
            return enriched[:limit]
        # Fallback: return all products if none marked as enriched
        return [p for p in products if isinstance(p, dict)][:limit]

    async def get_visas(self, session: aiohttp.ClientSession, country: str | None = None, limit: int = 10) -> list[dict]:
        params = {}
        if country:
            params["country"] = country
        data = await self._get(session, "visas", params if params else None)
        try:
            visas = data.get("data", {}).get("data", [])
            if not isinstance(visas, list):
                visas = data.get("data", [])
            if not isinstance(visas, list):
                visas = []
        except Exception:
            visas = []
        return visas[:limit]
