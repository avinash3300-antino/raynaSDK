"""Simulate: show me dubai tours"""
import asyncio, aiohttp
from dotenv import load_dotenv
load_dotenv()
from rayna_utils import RaynaApiClient, format_tour_card, _is_transfers_only

async def main():
    api = RaynaApiClient()
    async with aiohttp.ClientSession() as session:
        city_id = await api.resolve_city_id(session, "Dubai")
        print(f"City: Dubai -> city_id={city_id}")
        products = await api.get_city_products(session, city_id, limit=20)
        print(f"Products fetched: {len(products)}")
        print(f"Transfers only: {_is_transfers_only(products[:10])}")
        cards = [format_tour_card(p) for p in products[:6]]
        print(f"\n{'='*60}")
        print(f"RESPONSE: show-tours (Dubai) — {len(cards)} cards")
        print(f"{'='*60}\n")
        for i, card in enumerate(cards, 1):
            print(f"Card {i}:")
            print(f"  Title:    {card.get('title','N/A')}")
            print(f"  Price:    {card.get('price','N/A')}")
            print(f"  Currency: {card.get('currency','N/A')}")
            img = card.get('image','')
            print(f"  Image:    {img[:80]}{'...' if len(img)>80 else ''}")
            print(f"  URL:      {card.get('url','N/A')}")
            print(f"  Rating:   {card.get('rating','N/A')}")
            print(f"  Duration: {card.get('duration','N/A')}")
            print()
        print("URL Verification:")
        for i, card in enumerate(cards, 1):
            url = card.get("url", "")
            if url:
                try:
                    async with session.head(url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True) as resp:
                        s = "PASS" if resp.status < 400 else f"FAIL({resp.status})"
                except Exception as e:
                    s = f"FAIL({e})"
                print(f"  Card {i}: {s} — {url}")
        print("\nAll done.")

asyncio.run(main())
