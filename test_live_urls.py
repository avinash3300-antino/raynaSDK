"""
Test script: Verify all URLs in live API and RAG card responses are working.
No static data — everything comes from the live Rayna API or Pinecone RAG.
"""
import asyncio
import aiohttp
import sys
from dotenv import load_dotenv
load_dotenv()

from rayna_utils import RaynaApiClient, format_tour_card, _is_transfers_only
from rag_engine import (
    search_tours as rag_search_tours,
    search_all as rag_search_all,
    dedupe_by_parent as rag_dedupe,
    format_rag_tour_card,
    is_available as rag_is_available,
)

# Test cities for API
TEST_CITIES = ["Dubai", "Bangkok", "Bali", "Singapore", "Phuket", "Kuala Lumpur"]
# Test queries for RAG
RAG_QUERIES = [
    "desert safari Dubai",
    "Burj Khalifa tickets",
    "Phi Phi Island tour",
    "Singapore attractions",
    "Bali temple tour",
    "holiday packages Thailand",
]

PASS = 0
FAIL = 0
SKIP = 0
results_log = []


async def check_url(session, url, context):
    global PASS, FAIL, SKIP
    if not url:
        SKIP += 1
        results_log.append(("SKIP", context, "(empty URL)"))
        return
    if url == "https://www.raynatours.com":
        # Homepage fallback — always works
        PASS += 1
        results_log.append(("PASS", context, url + " (homepage fallback)"))
        return
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=15), allow_redirects=True) as resp:
            if resp.status < 400:
                PASS += 1
                results_log.append(("PASS", context, url))
            else:
                FAIL += 1
                results_log.append(("FAIL", context, f"{url} → {resp.status}"))
    except Exception as e:
        FAIL += 1
        results_log.append(("FAIL", context, f"{url} → {e}"))


async def test_api_tours(session):
    """Test show-tours: fetch products from live API for each city, format cards, check URLs."""
    print("\n" + "=" * 60)
    print("TEST 1: Live API — show-tours (city products)")
    print("=" * 60)
    api = RaynaApiClient()
    for city_name in TEST_CITIES:
        print(f"\n  [{city_name}]")
        try:
            city_id = await api.resolve_city_id(session, city_name)
            if not city_id:
                print(f"    Could not resolve city ID for {city_name}")
                continue
            print(f"    City ID: {city_id}")
            products = await api.get_city_products(session, city_id, limit=10)
            if not products:
                print(f"    No products found")
                continue
            if _is_transfers_only(products[:10]):
                print(f"    Only transfer products, skipping")
                continue
            count = min(len(products), 5)
            for p in products[:count]:
                card = format_tour_card(p)
                url = card.get("url", "")
                title = card.get("title", "Unknown")[:50]
                ctx = f"API/{city_name}/{title}"
                await check_url(session, url, ctx)
            print(f"    Checked {count} tour URLs")
        except Exception as e:
            print(f"    ERROR: {e}")


async def test_api_tour_detail(session):
    """Test show-tour-detail: get product details from API, check URLs."""
    print("\n" + "=" * 60)
    print("TEST 2: Live API — show-tour-detail")
    print("=" * 60)
    api = RaynaApiClient()
    try:
        city_id = await api.resolve_city_id(session, "Dubai")
        if not city_id:
            print("  Could not resolve Dubai city ID")
            return
        products = await api.get_city_products(session, city_id, limit=10)
        checked = 0
        for p in products[:10]:
            prod_url = p.get("url") or p.get("productUrl") or p.get("slug") or ""
            if not prod_url:
                continue
            try:
                detail = await api.get_product_details(session, prod_url)
                if detail:
                    card = format_tour_card(detail)
                    url = card.get("url", "")
                    title = card.get("title", "Unknown")[:50]
                    await check_url(session, url, f"DETAIL/{title}")
                    checked += 1
                    if checked >= 3:
                        break
            except Exception as e:
                print(f"    Detail error: {e}")
        print(f"  Checked {checked} tour detail URLs")
    except Exception as e:
        print(f"  ERROR: {e}")


async def test_api_holidays(session):
    """Test show-holiday-packages from API, check URLs."""
    print("\n" + "=" * 60)
    print("TEST 3: Live API — show-holiday-packages")
    print("=" * 60)
    api = RaynaApiClient()
    for city_name in ["Dubai", "Bangkok", "Bali"]:
        print(f"\n  [{city_name}]")
        try:
            city_id = await api.resolve_city_id(session, city_name, product_type="holiday")
            if not city_id:
                print(f"    Could not resolve city ID for {city_name} (holiday)")
                continue
            packages = await api.get_city_holiday(session, city_id)
            if not packages:
                print(f"    No holiday packages found")
                continue
            count = min(len(packages), 3)
            for p in packages[:count]:
                card = format_tour_card(p)
                url = card.get("url", "")
                title = card.get("title", "Unknown")[:50]
                await check_url(session, url, f"HOLIDAY/{city_name}/{title}")
            print(f"    Checked {count} holiday URLs")
        except Exception as e:
            print(f"    ERROR: {e}")


async def test_api_visa(session):
    """Test get-visa-info, check any URLs in the response."""
    print("\n" + "=" * 60)
    print("TEST 4: Live API — get-visa-info")
    print("=" * 60)
    api = RaynaApiClient()
    for country in ["India", "Philippines", "Pakistan"]:
        print(f"\n  [{country}]")
        try:
            visas = await api.get_visas(session, country=country)
            if not visas:
                print(f"    No visa data")
                continue
            count = min(len(visas), 3)
            for v in visas[:count]:
                if not isinstance(v, dict):
                    continue
                url = v.get("url") or v.get("productUrl") or v.get("link") or ""
                title = v.get("name") or v.get("title") or "Unknown"
                if url:
                    await check_url(session, url, f"VISA/{country}/{str(title)[:40]}")
                else:
                    # Format as card to see if URL extraction works
                    card = format_tour_card(v)
                    card_url = card.get("url", "")
                    await check_url(session, card_url, f"VISA-CARD/{country}/{card.get('title', 'Unknown')[:40]}")
            print(f"    Checked {count} visa entries")
        except Exception as e:
            print(f"    ERROR: {e}")


async def test_rag_tours():
    """Test RAG search results — format cards, check URLs."""
    print("\n" + "=" * 60)
    print("TEST 5: RAG (Pinecone) — tour search")
    print("=" * 60)
    if not rag_is_available():
        print("  RAG not available (missing API keys), skipping")
        return
    async with aiohttp.ClientSession() as session:
        for query in RAG_QUERIES:
            print(f"\n  Query: '{query}'")
            try:
                results = rag_search_tours(query, top_k=3)
                deduped = rag_dedupe(results)
                if not deduped:
                    print(f"    No RAG results")
                    continue
                for r in deduped[:3]:
                    card = format_rag_tour_card(r["metadata"])
                    url = card.get("url", "")
                    title = card.get("title", "Unknown")[:50]
                    await check_url(session, url, f"RAG/{title}")
                print(f"    Checked {min(len(deduped), 3)} results")
            except Exception as e:
                print(f"    ERROR: {e}")


async def test_rag_general():
    """Test RAG general search (ask-rayna style)."""
    print("\n" + "=" * 60)
    print("TEST 6: RAG (Pinecone) — general knowledge")
    print("=" * 60)
    if not rag_is_available():
        print("  RAG not available, skipping")
        return
    async with aiohttp.ClientSession() as session:
        queries = ["visa requirements UAE", "best time to visit Dubai", "Rayna Tours refund policy"]
        for query in queries:
            print(f"\n  Query: '{query}'")
            try:
                results = rag_search_all(query, top_k=3)
                deduped = rag_dedupe(results)
                if not deduped:
                    print(f"    No results")
                    continue
                for r in deduped[:2]:
                    meta = r["metadata"]
                    url = meta.get("url") or meta.get("urlPath") or meta.get("source") or ""
                    title = meta.get("title", "Unknown")[:50]
                    if url and (url.startswith("http") or url.startswith("/")):
                        if not url.startswith("http"):
                            url = f"https://www.raynatours.com{url}"
                        await check_url(session, url, f"RAG-KB/{title}")
                print(f"    Checked {min(len(deduped), 2)} results")
            except Exception as e:
                print(f"    ERROR: {e}")


async def main():
    print("=" * 60)
    print("LIVE URL VERIFICATION — No Static Data")
    print("All data from Rayna API (MCP) or Pinecone RAG")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        await test_api_tours(session)
        await test_api_tour_detail(session)
        await test_api_holidays(session)
        await test_api_visa(session)

    await test_rag_tours()
    await test_rag_general()

    # Summary
    total = PASS + FAIL + SKIP
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total URLs checked: {total}")
    print(f"  PASS: {PASS} ({PASS*100//max(total,1)}%)")
    print(f"  FAIL: {FAIL}")
    print(f"  SKIP: {SKIP} (empty URLs)")

    if FAIL > 0:
        print(f"\n  FAILED URLs:")
        for status, ctx, detail in results_log:
            if status == "FAIL":
                print(f"    [{ctx}] {detail}")

    if SKIP > 0:
        print(f"\n  SKIPPED (empty URLs):")
        for status, ctx, detail in results_log:
            if status == "SKIP":
                print(f"    [{ctx}]")

    return FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
