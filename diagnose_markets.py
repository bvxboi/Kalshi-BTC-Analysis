import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KALSHI_API_KEY_ID")
BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print("Fetching finalized KXBTCD markets...")
response = requests.get(
    f"{BASE_URL}/markets", 
    headers=headers, 
    params={"series_ticker": "KXBTCD", "limit": 50}
)

if response.status_code == 200:
    data = response.json()
    markets = data.get("markets", [])
    
    print(f"\nFound {len(markets)} markets")
    
    # Check statuses
    statuses = {}
    for m in markets:
        status = m.get('status')
        statuses[status] = statuses.get(status, 0) + 1
    
    print(f"\nStatus distribution:")
    for status, count in statuses.items():
        print(f"  {status}: {count}")
    
    print("\nFirst 10 markets with details:")
    for i, m in enumerate(markets[:10]):
        print(f"\n{i+1}. {m.get('ticker')}")
        print(f"   Volume: {m.get('volume', 0)}")
        print(f"   Status: {m.get('status')}")
        print(f"   Close time: {m.get('close_time')}")
        print(f"   Result: {m.get('result')}")
    
    # Check volume distribution
    with_volume = [m for m in markets if m.get('volume', 0) > 0]
    print(f"\n{'='*60}")
    print(f"Markets with volume > 0: {len(with_volume)} out of {len(markets)}")
    
    if with_volume:
        print("\nTop 5 by volume:")
        with_volume.sort(key=lambda x: x.get('volume', 0), reverse=True)
        for m in with_volume[:5]:
            print(f"  - {m.get('ticker')} | Volume: {m.get('volume')}")
    
else:
    print(f"Error: {response.status_code}")
    print(response.text)