"""
Rayna Tours API client, static tour database, and tour card formatting.
"""
from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import quote

import aiohttp
from cachetools import TTLCache

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://earnest-panda-e8edbd.netlify.app/api"
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
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Desert Safari": ["desert", "safari", "dune", "camel"],
    "City Tour": ["city tour", "sightseeing", "hop on", "hop off"],
    "Theme Park": ["theme park", "ferrari world", "legoland", "motiongate", "img", "universal", "fantasea"],
    "Water Park": ["aquaventure", "waterworld", "water park", "splash"],
    "Adventure": ["zipline", "skydiving", "bungee", "quad bike", "buggy", "mountain", "trek", "jais flight"],
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

# ---------------------------------------------------------------------------
# Static Tour Database (54 tours)
# ---------------------------------------------------------------------------

TOUR_DATABASE: list[dict[str, Any]] = [
    # UAE — Dubai
    {"id": "dubai-desert-safari", "title": "Dubai Desert Safari", "category": "Adventure & Culture", "location": "Dubai", "country": "UAE", "price": 165.00, "currency": "AED", "duration": "6 hrs", "description": "Experience the ultimate desert adventure with dune bashing, camel riding, BBQ dinner and live entertainment.", "highlights": ["Dune Bashing", "Camel Riding", "BBQ Dinner", "Belly Dance"], "url": "https://www.raynatours.com/dubai/adventure/desert-safari-e-509001", "rating": 4.8, "is_popular": True, "image": ""},
    {"id": "burj-khalifa-at-the-top", "title": "Burj Khalifa At The Top", "category": "Attractions", "location": "Dubai", "country": "UAE", "price": 189.00, "currency": "AED", "duration": "2 hrs", "description": "Visit the world's tallest building and enjoy breathtaking views of Dubai from the observation deck.", "highlights": ["Burj Khalifa", "Dubai Mall", "Observation Deck"], "url": "https://www.raynatours.com/dubai/attractions/burj-khalifa-at-the-top-e-509002", "rating": 4.9, "is_popular": True, "image": ""},
    {"id": "dubai-marina-dhow-cruise", "title": "Dubai Marina Dhow Cruise", "category": "Cruise", "location": "Dubai", "country": "UAE", "price": 89.25, "currency": "AED", "duration": "2 hrs", "description": "Enjoy a traditional dhow cruise along the stunning Dubai Marina with dinner and live entertainment.", "highlights": ["Dubai Marina", "Dhow Cruise", "BBQ Dinner"], "url": "https://www.raynatours.com/dubai/cruise/marina-dhow-cruise-e-509003", "rating": 4.7, "is_popular": True, "image": ""},
    {"id": "global-village-dubai", "title": "Global Village Dubai", "category": "Entertainment", "location": "Dubai", "country": "UAE", "price": 25.00, "currency": "AED", "duration": "4 hrs", "description": "Explore the world's largest tourism, leisure, shopping and entertainment project.", "highlights": ["Global Village", "Shopping", "Entertainment"], "url": "https://www.raynatours.com/dubai/entertainment/global-village-e-509004", "rating": 4.5, "is_popular": True, "image": ""},
    {"id": "atlantis-aquaventure", "title": "Atlantis Aquaventure Waterpark", "category": "Water Park", "location": "Dubai", "country": "UAE", "price": 315.00, "currency": "AED", "duration": "Full Day", "description": "The Middle East's largest waterpark with thrilling rides and marine encounters.", "highlights": ["Palm Jumeirah", "Water Park", "Marine Encounters"], "url": "https://www.raynatours.com/dubai/waterpark/atlantis-aquaventure-e-509005", "rating": 4.6, "is_popular": True, "image": ""},
    # UAE — Abu Dhabi
    {"id": "sheikh-zayed-grand-mosque", "title": "Sheikh Zayed Grand Mosque Tour", "category": "Cultural", "location": "Abu Dhabi", "country": "UAE", "price": 125.00, "currency": "AED", "duration": "3 hrs", "description": "Visit one of the world's largest and most beautiful mosques with stunning Islamic architecture.", "highlights": ["Sheikh Zayed Mosque", "Grand Mosque", "Cultural Tour"], "url": "https://www.raynatours.com/abudhabi/cultural/sheikh-zayed-mosque-e-509006", "rating": 4.9, "is_popular": True, "image": ""},
    {"id": "ferrari-world-abu-dhabi", "title": "Ferrari World Abu Dhabi", "category": "Theme Park", "location": "Abu Dhabi", "country": "UAE", "price": 345.00, "currency": "AED", "duration": "Full Day", "description": "The world's first Ferrari-branded theme park featuring thrilling rides and attractions.", "highlights": ["Ferrari World", "Theme Park", "Yas Island"], "url": "https://www.raynatours.com/abudhabi/themepark/ferrari-world-e-509007", "rating": 4.7, "is_popular": True, "image": ""},
    # UAE — Ras Al Khaimah
    {"id": "jais-flight-zipline", "title": "Jais Flight - World's Longest Zipline", "category": "Adventure", "location": "Ras Al Khaimah", "country": "UAE", "price": 150.00, "currency": "AED", "duration": "3 hrs", "description": "Experience the world's longest zipline at Jebel Jais mountain.", "highlights": ["Jais Flight", "Zipline", "Mountain"], "url": "https://www.raynatours.com/rasalkhaimah/adventure/jais-flight-e-509008", "rating": 4.8, "is_popular": True, "image": ""},
    # Saudi Arabia
    {"id": "jeddah-historical-district", "title": "Jeddah Historical District Tour", "category": "Cultural", "location": "Jeddah", "country": "Saudi Arabia", "price": 145.00, "currency": "AED", "duration": "4 hrs", "description": "Explore Al-Balad, Jeddah's historic district with UNESCO World Heritage status.", "highlights": ["Historical District", "Al-Balad", "Heritage Tour"], "url": "https://www.raynatours.com/jeddah/cultural/historical-district-e-509009", "rating": 4.5, "is_popular": False, "image": ""},
    {"id": "masmak-fortress-riyadh", "title": "Masmak Fortress & Riyadh City Tour", "category": "Cultural", "location": "Riyadh", "country": "Saudi Arabia", "price": 85.00, "currency": "AED", "duration": "2 hrs", "description": "Visit the iconic Masmak Fortress and explore the rich history of Riyadh.", "highlights": ["Masmak Fortress", "Kingdom Centre", "Cultural Tour"], "url": "https://www.raynatours.com/riyadh/cultural/masmak-fortress-e-509010", "rating": 4.3, "is_popular": False, "image": ""},
    {"id": "umrah-package-makkah", "title": "Umrah Package - Makkah", "category": "Religious", "location": "Makkah", "country": "Saudi Arabia", "price": 1250.00, "currency": "AED", "duration": "3 Days", "description": "Complete Umrah package with guided spiritual journey to the holiest sites in Islam.", "highlights": ["Umrah", "Holy Sites", "Spiritual Journey"], "url": "https://www.raynatours.com/makkah/religious/umrah-package-e-509011", "rating": 5.0, "is_popular": False, "image": ""},
    # Oman
    {"id": "sultan-qaboos-grand-mosque", "title": "Sultan Qaboos Grand Mosque Tour", "category": "Cultural", "location": "Muscat", "country": "Oman", "price": 115.00, "currency": "AED", "duration": "2 hrs", "description": "Visit Oman's magnificent Grand Mosque, a masterpiece of Islamic architecture.", "highlights": ["Grand Mosque", "Cultural Tour", "Muscat"], "url": "https://www.raynatours.com/muscat/cultural/grand-mosque-e-509012", "rating": 4.7, "is_popular": False, "image": ""},
    {"id": "khasab-dhow-cruise", "title": "Khasab Musandam Dhow Cruise", "category": "Cruise", "location": "Khasab", "country": "Oman", "price": 195.00, "currency": "AED", "duration": "6 hrs", "description": "Cruise through the stunning fjords of Musandam with snorkeling and dolphin watching.", "highlights": ["Dhow Cruise", "Snorkeling", "Dolphin Watching"], "url": "https://www.raynatours.com/khasab/cruise/musandam-dhow-e-509013", "rating": 4.8, "is_popular": True, "image": ""},
    # Thailand — Bangkok
    {"id": "bangkok-floating-markets", "title": "Bangkok Floating Markets Tour", "category": "Cultural", "location": "Bangkok", "country": "Thailand", "price": 434.98, "currency": "AED", "duration": "6 hrs", "description": "Visit the iconic floating markets of Bangkok with local food tasting.", "highlights": ["Floating Markets", "Street Food", "Cultural Tour"], "url": "https://www.raynatours.com/bangkok/cultural/floating-markets-e-509014", "rating": 4.6, "is_popular": True, "image": ""},
    {"id": "chaophraya-dinner-cruise", "title": "Chaophraya Princess Dinner Cruise", "category": "Cruise", "location": "Bangkok", "country": "Thailand", "price": 123.53, "currency": "AED", "duration": "2.5 hrs", "description": "Enjoy a luxurious dinner cruise along the Chao Phraya River with stunning views.", "highlights": ["Dhow Cruise", "Dinner Cruise", "River Views"], "url": "https://www.raynatours.com/bangkok/cruise/chaophraya-dinner-e-509015", "rating": 4.5, "is_popular": False, "image": ""},
    {"id": "bangkok-grand-palace", "title": "Bangkok Grand Palace & Temples Tour", "category": "Cultural", "location": "Bangkok", "country": "Thailand", "price": 189.00, "currency": "AED", "duration": "4 hrs", "description": "Explore Thailand's most sacred temple complex and the opulent Grand Palace.", "highlights": ["Grand Palace", "Temple Tour", "Cultural Tour"], "url": "https://www.raynatours.com/bangkok/cultural/grand-palace-e-509016", "rating": 4.8, "is_popular": True, "image": ""},
    {"id": "bangkok-elephant-sanctuary", "title": "Bangkok Elephant Sanctuary Visit", "category": "Nature", "location": "Bangkok", "country": "Thailand", "price": 245.75, "currency": "AED", "duration": "5 hrs", "description": "Visit an ethical elephant sanctuary and interact with these gentle giants.", "highlights": ["Elephant Sanctuary", "Nature", "Wildlife"], "url": "https://www.raynatours.com/bangkok/nature/elephant-sanctuary-e-509017", "rating": 4.7, "is_popular": False, "image": ""},
    # Thailand — Phuket
    {"id": "phi-phi-island-tour", "title": "Phi Phi Island Day Trip", "category": "Island", "location": "Phuket", "country": "Thailand", "price": 185.50, "currency": "AED", "duration": "Full Day", "description": "Visit the stunning Phi Phi Islands with snorkeling, swimming and beach time.", "highlights": ["Phi Phi Island", "Snorkeling", "Island Hopping"], "url": "https://www.raynatours.com/phuket/island/phi-phi-island-e-509018", "rating": 4.7, "is_popular": True, "image": ""},
    {"id": "phuket-sunset-cruise", "title": "Phuket Sunset Cruise", "category": "Cruise", "location": "Phuket", "country": "Thailand", "price": 165.00, "currency": "AED", "duration": "3 hrs", "description": "Sail along the Andaman Sea coast and enjoy a spectacular sunset.", "highlights": ["Sunset Cruise", "Andaman Sea", "Snorkeling"], "url": "https://www.raynatours.com/phuket/cruise/sunset-cruise-e-509019", "rating": 4.6, "is_popular": False, "image": ""},
    # Thailand — Krabi
    {"id": "four-islands-krabi", "title": "Krabi Four Islands Tour", "category": "Island", "location": "Krabi", "country": "Thailand", "price": 145.25, "currency": "AED", "duration": "Full Day", "description": "Visit four stunning islands with snorkeling, swimming and beach activities.", "highlights": ["Island Hopping", "Snorkeling", "Beach"], "url": "https://www.raynatours.com/krabi/island/four-islands-e-509020", "rating": 4.6, "is_popular": False, "image": ""},
    # Thailand — Koh Samui
    {"id": "ang-thong-marine-park", "title": "Ang Thong National Marine Park", "category": "Island", "location": "Koh Samui", "country": "Thailand", "price": 195.50, "currency": "AED", "duration": "Full Day", "description": "Explore 42 islands of Ang Thong National Marine Park with kayaking and snorkeling.", "highlights": ["Marine Park", "Island Hopping", "Snorkeling"], "url": "https://www.raynatours.com/kohsamui/island/ang-thong-e-509021", "rating": 4.7, "is_popular": False, "image": ""},
    # Thailand — Pattaya
    {"id": "tiffany-cabaret-pattaya", "title": "Tiffany's Cabaret Show Pattaya", "category": "Entertainment", "location": "Pattaya", "country": "Thailand", "price": 85.25, "currency": "AED", "duration": "2 hrs", "description": "Watch the world-famous Tiffany's Cabaret Show with dazzling performances.", "highlights": ["Tiffany Show", "Entertainment", "Cabaret"], "url": "https://www.raynatours.com/pattaya/entertainment/tiffany-cabaret-e-509022", "rating": 4.4, "is_popular": False, "image": ""},
    {"id": "pattaya-coral-island", "title": "Pattaya Coral Island Tour", "category": "Island", "location": "Pattaya", "country": "Thailand", "price": 125.50, "currency": "AED", "duration": "Full Day", "description": "Visit Coral Island with water sports, snorkeling and beach activities.", "highlights": ["Coral Island", "Snorkeling", "Water Sports"], "url": "https://www.raynatours.com/pattaya/island/coral-island-e-509023", "rating": 4.5, "is_popular": False, "image": ""},
    {"id": "phuket-fantasea", "title": "Phuket FantaSea Show", "category": "Entertainment", "location": "Phuket", "country": "Thailand", "price": 195.00, "currency": "AED", "duration": "4 hrs", "description": "A spectacular cultural theme park and show celebrating Thai heritage.", "highlights": ["Fantasea", "Entertainment", "Cultural Show"], "url": "https://www.raynatours.com/phuket/entertainment/fantasea-e-509024", "rating": 4.5, "is_popular": False, "image": ""},
    {"id": "krabi-tiger-cave-temple", "title": "Krabi Tiger Cave Temple Tour", "category": "Cultural", "location": "Krabi", "country": "Thailand", "price": 95.00, "currency": "AED", "duration": "3 hrs", "description": "Visit the famous Tiger Cave Temple and climb 1,260 steps for panoramic views.", "highlights": ["Temple Tour", "Tiger Temple", "Panoramic Views"], "url": "https://www.raynatours.com/krabi/cultural/tiger-cave-temple-e-509025", "rating": 4.4, "is_popular": False, "image": ""},
    {"id": "koh-samui-temple-tour", "title": "Koh Samui Temple & Culture Tour", "category": "Cultural", "location": "Koh Samui", "country": "Thailand", "price": 115.00, "currency": "AED", "duration": "4 hrs", "description": "Explore the island's most sacred temples including the Big Buddha.", "highlights": ["Temple Tour", "Big Buddha", "Cultural Tour"], "url": "https://www.raynatours.com/kohsamui/cultural/temple-tour-e-509026", "rating": 4.5, "is_popular": False, "image": ""},
    {"id": "bangkok-street-food", "title": "Bangkok Street Food Tour", "category": "Food", "location": "Bangkok", "country": "Thailand", "price": 135.00, "currency": "AED", "duration": "3 hrs", "description": "Taste authentic Thai street food with a local guide through Bangkok's best food spots.", "highlights": ["Street Food", "Food Tour", "Local Guide"], "url": "https://www.raynatours.com/bangkok/food/street-food-tour-e-509027", "rating": 4.6, "is_popular": False, "image": ""},
    # Indonesia — Bali
    {"id": "mount-batur-sunrise-trek", "title": "Mount Batur Sunrise Trek", "category": "Adventure", "location": "Bali", "country": "Indonesia", "price": 185.00, "currency": "AED", "duration": "8 hrs", "description": "Trek to the summit of Mount Batur for a spectacular sunrise over Bali.", "highlights": ["Mount Batur", "Sunrise Trek", "Volcano"], "url": "https://www.raynatours.com/bali/adventure/mount-batur-e-509028", "rating": 4.8, "is_popular": True, "image": ""},
    {"id": "ubud-rice-terraces", "title": "Ubud Rice Terraces & Temple Tour", "category": "Nature", "location": "Bali", "country": "Indonesia", "price": 125.75, "currency": "AED", "duration": "6 hrs", "description": "Visit the iconic Tegallalang Rice Terraces and ancient temples of Ubud.", "highlights": ["Rice Terraces", "Temple Tour", "Ubud"], "url": "https://www.raynatours.com/bali/nature/ubud-rice-terraces-e-509029", "rating": 4.7, "is_popular": False, "image": ""},
    {"id": "bali-water-temple", "title": "Bali Water Temple Tour", "category": "Cultural", "location": "Bali", "country": "Indonesia", "price": 95.50, "currency": "AED", "duration": "4 hrs", "description": "Visit Bali's most sacred water temples including Tirta Empul.", "highlights": ["Water Temple", "Cultural Tour", "Tirta Empul"], "url": "https://www.raynatours.com/bali/cultural/water-temple-e-509030", "rating": 4.6, "is_popular": False, "image": ""},
    {"id": "bali-uluwatu-sunset", "title": "Bali Uluwatu Sunset & Kecak Dance", "category": "Cultural", "location": "Bali", "country": "Indonesia", "price": 110.00, "currency": "AED", "duration": "4 hrs", "description": "Watch the sunset at Uluwatu Temple and enjoy a traditional Kecak fire dance.", "highlights": ["Uluwatu Temple", "Kecak Dance", "Sunset"], "url": "https://www.raynatours.com/bali/cultural/uluwatu-sunset-e-509031", "rating": 4.7, "is_popular": True, "image": ""},
    {"id": "bali-nusa-penida", "title": "Nusa Penida Island Day Trip", "category": "Island", "location": "Bali", "country": "Indonesia", "price": 215.00, "currency": "AED", "duration": "Full Day", "description": "Visit the stunning Nusa Penida island with its dramatic cliffs and crystal-clear waters.", "highlights": ["Nusa Penida", "Island Hopping", "Snorkeling"], "url": "https://www.raynatours.com/bali/island/nusa-penida-e-509032", "rating": 4.6, "is_popular": False, "image": ""},
    # Malaysia — Kuala Lumpur
    {"id": "petronas-twin-towers", "title": "Petronas Twin Towers Visit", "category": "Attraction", "location": "Kuala Lumpur", "country": "Malaysia", "price": 89.50, "currency": "AED", "duration": "2 hrs", "description": "Visit the iconic Petronas Twin Towers and skybridge for panoramic city views.", "highlights": ["Petronas Towers", "Skybridge", "Observation Deck"], "url": "https://www.raynatours.com/kualalumpur/attraction/petronas-towers-e-509033", "rating": 4.5, "is_popular": True, "image": ""},
    {"id": "batu-caves-temple", "title": "Batu Caves Temple Tour", "category": "Cultural", "location": "Kuala Lumpur", "country": "Malaysia", "price": 65.25, "currency": "AED", "duration": "3 hrs", "description": "Visit the iconic Batu Caves limestone temple complex.", "highlights": ["Batu Caves", "Temple Tour", "Hindu Temple"], "url": "https://www.raynatours.com/kualalumpur/cultural/batu-caves-e-509034", "rating": 4.4, "is_popular": False, "image": ""},
    {"id": "kl-food-walk", "title": "Kuala Lumpur Street Food Walk", "category": "Food", "location": "Kuala Lumpur", "country": "Malaysia", "price": 75.00, "currency": "AED", "duration": "3 hrs", "description": "Explore KL's famous street food scene with a local guide.", "highlights": ["Street Food", "Food Tour", "Jalan Alor"], "url": "https://www.raynatours.com/kualalumpur/food/street-food-walk-e-509035", "rating": 4.5, "is_popular": False, "image": ""},
    # Malaysia — Langkawi
    {"id": "langkawi-cable-car", "title": "Langkawi Cable Car & Sky Bridge", "category": "Attraction", "location": "Langkawi", "country": "Malaysia", "price": 85.75, "currency": "AED", "duration": "3 hrs", "description": "Ride the steepest cable car in the world and walk the Sky Bridge.", "highlights": ["Cable Car", "Sky Bridge", "Panoramic Views"], "url": "https://www.raynatours.com/langkawi/attraction/cable-car-e-509036", "rating": 4.6, "is_popular": True, "image": ""},
    {"id": "langkawi-island-hopping", "title": "Langkawi Island Hopping Tour", "category": "Island", "location": "Langkawi", "country": "Malaysia", "price": 75.00, "currency": "AED", "duration": "4 hrs", "description": "Visit multiple islands around Langkawi including Pulau Dayang Bunting.", "highlights": ["Island Hopping", "Lake of the Pregnant Maiden", "Eagles"], "url": "https://www.raynatours.com/langkawi/island/island-hopping-e-509037", "rating": 4.5, "is_popular": False, "image": ""},
    # Malaysia — Penang
    {"id": "george-town-heritage-walk", "title": "George Town Heritage Walk", "category": "Cultural", "location": "Penang", "country": "Malaysia", "price": 55.25, "currency": "AED", "duration": "3 hrs", "description": "Walk through UNESCO-listed George Town with its vibrant street art and heritage buildings.", "highlights": ["Street Art", "Heritage Walk", "UNESCO"], "url": "https://www.raynatours.com/penang/cultural/heritage-walk-e-509038", "rating": 4.3, "is_popular": False, "image": ""},
    {"id": "penang-food-trail", "title": "Penang Food Trail Tour", "category": "Food", "location": "Penang", "country": "Malaysia", "price": 65.00, "currency": "AED", "duration": "3 hrs", "description": "Taste the best food in Asia's food capital with a local culinary guide.", "highlights": ["Street Food", "Food Tour", "Char Kway Teow"], "url": "https://www.raynatours.com/penang/food/food-trail-e-509039", "rating": 4.6, "is_popular": False, "image": ""},
    # Singapore
    {"id": "singapore-flyer", "title": "Singapore Flyer Experience", "category": "Attraction", "location": "Singapore", "country": "Singapore", "price": 125.50, "currency": "AED", "duration": "1.5 hrs", "description": "Ride Asia's largest observation wheel for stunning views of the city skyline.", "highlights": ["Singapore Flyer", "Observation Wheel", "City Views"], "url": "https://www.raynatours.com/singapore/attraction/singapore-flyer-e-509040", "rating": 4.5, "is_popular": True, "image": ""},
    {"id": "gardens-by-the-bay", "title": "Gardens by the Bay", "category": "Nature", "location": "Singapore", "country": "Singapore", "price": 85.25, "currency": "AED", "duration": "3 hrs", "description": "Explore the futuristic gardens with Supertree Grove and Cloud Forest.", "highlights": ["Gardens by the Bay", "Supertree Grove", "Cloud Forest"], "url": "https://www.raynatours.com/singapore/nature/gardens-bay-e-509041", "rating": 4.7, "is_popular": True, "image": ""},
    {"id": "universal-studios-singapore", "title": "Universal Studios Singapore", "category": "Theme Park", "location": "Singapore", "country": "Singapore", "price": 275.00, "currency": "AED", "duration": "Full Day", "description": "Southeast Asia's first and only Universal Studios theme park.", "highlights": ["Universal Studios", "Theme Park", "Sentosa Island"], "url": "https://www.raynatours.com/singapore/themepark/universal-studios-e-509042", "rating": 4.6, "is_popular": True, "image": ""},
    {"id": "singapore-night-safari", "title": "Singapore Night Safari", "category": "Nature", "location": "Singapore", "country": "Singapore", "price": 145.75, "currency": "AED", "duration": "4 hrs", "description": "The world's first nocturnal wildlife park with over 900 animals.", "highlights": ["Night Safari", "Wildlife", "Tram Ride"], "url": "https://www.raynatours.com/singapore/nature/night-safari-e-509043", "rating": 4.7, "is_popular": True, "image": ""},
    # Additional UAE tours
    {"id": "dubai-miracle-garden", "title": "Dubai Miracle Garden Visit", "category": "Nature", "location": "Dubai", "country": "UAE", "price": 99.00, "currency": "AED", "duration": "3 hrs", "description": "The world's largest natural flower garden with over 150 million flowers.", "highlights": ["Miracle Garden", "Flower Garden", "Photography"], "url": "https://www.raynatours.com/dubai/nature/miracle-garden-e-509044", "rating": 4.4, "is_popular": False, "image": ""},
    {"id": "dubai-frame", "title": "Dubai Frame Visit", "category": "Attraction", "location": "Dubai", "country": "UAE", "price": 55.00, "currency": "AED", "duration": "1.5 hrs", "description": "Visit the world's largest picture frame offering Old and New Dubai views.", "highlights": ["Dubai Frame", "Observation Deck", "City Views"], "url": "https://www.raynatours.com/dubai/attraction/dubai-frame-e-509045", "rating": 4.5, "is_popular": False, "image": ""},
    {"id": "abu-dhabi-city-tour", "title": "Abu Dhabi Full Day City Tour", "category": "City Tour", "location": "Abu Dhabi", "country": "UAE", "price": 175.00, "currency": "AED", "duration": "Full Day", "description": "Explore the capital of the UAE including Sheikh Zayed Mosque, Corniche, and Yas Island.", "highlights": ["Sheikh Zayed Mosque", "Corniche", "Yas Island"], "url": "https://www.raynatours.com/abudhabi/citytour/full-day-e-509046", "rating": 4.6, "is_popular": False, "image": ""},
    {"id": "img-worlds-adventure", "title": "IMG Worlds of Adventure", "category": "Theme Park", "location": "Dubai", "country": "UAE", "price": 299.00, "currency": "AED", "duration": "Full Day", "description": "The world's largest indoor themed entertainment destination.", "highlights": ["Theme Park", "Indoor Park", "Marvel Zone"], "url": "https://www.raynatours.com/dubai/themepark/img-worlds-e-509047", "rating": 4.5, "is_popular": False, "image": ""},
    # Additional Thailand
    {"id": "phuket-james-bond-island", "title": "Phuket James Bond Island Tour", "category": "Island", "location": "Phuket", "country": "Thailand", "price": 175.00, "currency": "AED", "duration": "Full Day", "description": "Visit the famous James Bond Island in Phang Nga Bay with canoeing.", "highlights": ["James Bond Island", "Canoeing", "Phang Nga Bay"], "url": "https://www.raynatours.com/phuket/island/james-bond-island-e-509048", "rating": 4.6, "is_popular": True, "image": ""},
    {"id": "pattaya-sanctuary-truth", "title": "Pattaya Sanctuary of Truth Visit", "category": "Cultural", "location": "Pattaya", "country": "Thailand", "price": 95.00, "currency": "AED", "duration": "2 hrs", "description": "Visit the magnificent all-wood temple filled with intricate carvings.", "highlights": ["Sanctuary of Truth", "Cultural Tour", "Wood Carving"], "url": "https://www.raynatours.com/pattaya/cultural/sanctuary-truth-e-509049", "rating": 4.4, "is_popular": False, "image": ""},
    # Additional Bali
    {"id": "bali-white-water-rafting", "title": "Bali White Water Rafting", "category": "Adventure", "location": "Bali", "country": "Indonesia", "price": 135.00, "currency": "AED", "duration": "4 hrs", "description": "Experience thrilling white water rafting on the Ayung River through tropical jungle.", "highlights": ["White Water Rafting", "Ayung River", "Adventure"], "url": "https://www.raynatours.com/bali/adventure/white-water-rafting-e-509050", "rating": 4.5, "is_popular": False, "image": ""},
    # Additional Singapore
    {"id": "sentosa-island-day", "title": "Sentosa Island Day Pass", "category": "Entertainment", "location": "Singapore", "country": "Singapore", "price": 95.00, "currency": "AED", "duration": "Full Day", "description": "Full day access to Sentosa Island attractions including beaches and entertainment.", "highlights": ["Sentosa Island", "Beach", "Entertainment"], "url": "https://www.raynatours.com/singapore/entertainment/sentosa-island-e-509051", "rating": 4.4, "is_popular": False, "image": ""},
    {"id": "singapore-river-cruise", "title": "Singapore River Cruise", "category": "Cruise", "location": "Singapore", "country": "Singapore", "price": 65.00, "currency": "AED", "duration": "40 mins", "description": "Cruise along the Singapore River past iconic landmarks.", "highlights": ["River Cruise", "Marina Bay Sands", "Merlion"], "url": "https://www.raynatours.com/singapore/cruise/river-cruise-e-509052", "rating": 4.3, "is_popular": False, "image": ""},
    # Dammam
    {"id": "dammam-corniche-tour", "title": "Dammam Corniche & Heritage Tour", "category": "City Tour", "location": "Dammam", "country": "Saudi Arabia", "price": 95.00, "currency": "AED", "duration": "3 hrs", "description": "Explore Dammam's beautiful Corniche and heritage village.", "highlights": ["Corniche", "Heritage Village", "City Tour"], "url": "https://www.raynatours.com/dammam/citytour/corniche-heritage-e-509053", "rating": 4.2, "is_popular": False, "image": ""},
    {"id": "half-moon-bay-dammam", "title": "Half Moon Bay Beach Day", "category": "Island", "location": "Dammam", "country": "Saudi Arabia", "price": 120.00, "currency": "AED", "duration": "Full Day", "description": "Enjoy a relaxing day at Half Moon Bay with water sports and beach activities.", "highlights": ["Beach", "Water Sports", "Half Moon Bay"], "url": "https://www.raynatours.com/dammam/beach/half-moon-bay-e-509054", "rating": 4.3, "is_popular": False, "image": ""},
]


# ---------------------------------------------------------------------------
# Helper functions for static database
# ---------------------------------------------------------------------------

def get_tours_by_location(location: str) -> list[dict[str, Any]]:
    loc_lower = location.lower()
    return [t for t in TOUR_DATABASE if t["location"].lower() == loc_lower]


def get_tours_by_country(country: str) -> list[dict[str, Any]]:
    c_lower = country.lower()
    return [t for t in TOUR_DATABASE if t["country"].lower() == c_lower]


def get_tours_by_category(category: str) -> list[dict[str, Any]]:
    cat_lower = category.lower()
    return [t for t in TOUR_DATABASE if cat_lower in t["category"].lower()]


def get_popular_tours(limit: int = 6) -> list[dict[str, Any]]:
    popular = [t for t in TOUR_DATABASE if t.get("is_popular")]
    return popular[:limit]


def search_tours(query: str) -> list[dict[str, Any]]:
    tokens = query.lower().split()
    results: list[dict[str, Any]] = []
    for tour in TOUR_DATABASE:
        searchable = f"{tour['title']} {tour['category']} {tour['location']} {tour['country']}".lower()
        if all(tok in searchable for tok in tokens):
            results.append(tour)
    return results


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


def format_static_tour(tour: dict[str, Any]) -> dict[str, Any]:
    """Convert a static DB tour into the same TourCard shape."""
    price = tour["price"]
    return {
        "id": tour["id"],
        "title": tour["title"],
        "slug": tour.get("url", ""),
        "image": tour.get("image", ""),
        "location": tour["location"],
        "category": tour["category"],
        "originalPrice": None,
        "currentPrice": price,
        "currency": tour.get("currency", "AED"),
        "discount": None,
        "discountPercentage": None,
        "isRecommended": tour.get("is_popular", False),
        "isNew": False,
        "rPoints": _calc_rpoints(price),
        "rating": tour.get("rating"),
        "reviewCount": None,
        "duration": tour.get("duration"),
        "highlights": tour.get("highlights"),
        "url": tour.get("url", "https://www.raynatours.com"),
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
                    return c["id"]
            # Fuzzy match
            for c in cities:
                if city_lower in c["name"].lower() or c["name"].lower() in city_lower:
                    return c["id"]
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

    async def get_city_products(self, session: aiohttp.ClientSession, city_id: int) -> list[dict]:
        data = await self._get(session, "city/products", {"cityId": city_id})
        try:
            products = _find_product_list(data)
            if products:
                return products[:20]
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

    async def get_product_details(self, session: aiohttp.ClientSession, url: str) -> dict:
        data = await self._get(session, "product-details", {"url": quote(url, safe="")})
        try:
            return data.get("data", {}).get("data", {}) or data.get("data", {})
        except Exception:
            return data or {}

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
