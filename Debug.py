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

print("Testing Kalshi API access...")
print(f"API Key present: {bool(API_KEY)}")
print()

# Test 1: Get any markets to verify authentication
print("Test 1: Fetching any markets (no filters)...")
response = requests.get(f"{BASE_URL}/markets", headers=headers, params={"limit": 5})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    markets = data.get("markets", [])
    print(f"Found {len(markets)} markets")
    if len(markets) > 0:
        print(f"Sample ticker: {markets[0].get('ticker')}")
        print(f"Sample series: {markets[0].get('series_ticker')}")
        print(f"Sample status: {markets[0].get('status')}")
else:
    print(f"Error: {response.text}")
print()

# Test 2: Try to find Bitcoin markets
print("Test 2: Searching for Bitcoin-related markets...")
response = requests.get(f"{BASE_URL}/markets", headers=headers, params={"limit": 50})
if response.status_code == 200:
    data = response.json()
    markets = data.get("markets", [])
    
    # Look for any Bitcoin-related tickers
    btc_markets = [m for m in markets if "BTC" in m.get("ticker", "").upper()]
    print(f"Found {len(btc_markets)} markets with 'BTC' in ticker")
    
    if btc_markets:
        print("Sample Bitcoin tickers:")
        for m in btc_markets[:5]:
            print(f"  - {m.get('ticker')} | Series: {m.get('series_ticker')} | Status: {m.get('status')}")
print()

# Test 3: Try KXBTCD series specifically
print("Test 3: Fetching KXBTCD series markets...")
response = requests.get(
    f"{BASE_URL}/markets", 
    headers=headers, 
    params={"series_ticker": "KXBTCD", "limit": 10}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    markets = data.get("markets", [])
    print(f"Found {len(markets)} KXBTCD markets")
    if markets:
        print("Sample tickers:")
        for m in markets[:5]:
            print(f"  - {m.get('ticker')} | Status: {m.get('status')} | Volume: {m.get('volume', 0)}")
else:
    print(f"Error: {response.text}")
print()

# Test 4: Check for settled markets
print("Test 4: Fetching settled KXBTCD markets...")
response = requests.get(
    f"{BASE_URL}/markets", 
    headers=headers, 
    params={"series_ticker": "KXBTCD", "status": "settled", "limit": 10}
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    markets = data.get("markets", [])
    print(f"Found {len(markets)} settled KXBTCD markets")
    if markets:
        print("Sample settled tickers:")
        for m in markets[:5]:
            print(f"  - {m.get('ticker')} | Closed: {m.get('close_time')} | Result: {m.get('result')}")
else:
    print(f"Error: {response.text}")