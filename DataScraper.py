import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional
import json
import os
from dotenv import load_dotenv
import signal
import sys

# Load environment variables from .env file
load_dotenv()

# Global variable to store results for interrupt handling
_global_results = []
_global_output_file = "bitcoin_hourly_analysis.csv"

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully by saving collected data"""
    print("\n\n⚠️  Interrupt received! Saving collected data...")
    if _global_results:
        df = pd.DataFrame(_global_results)
        df.to_csv(_global_output_file, index=False)
        print(f"✅ Saved {len(_global_results)} records to {_global_output_file}")
    else:
        print("No data collected yet.")
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

class KalshiHistoricalAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_settled_bitcoin_hourly_markets(self, min_close_date: Optional[str] = None, max_close_date: Optional[str] = None) -> List[Dict]:
        """
        Fetch all settled Bitcoin hourly markets from Kalshi
        Markets have format: KXBTCD-25NOV1417-T100249.99
        
        Args:
            min_close_date: Optional ISO format date string (e.g., "2025-10-01T00:00:00Z") for earliest close time
            max_close_date: Optional ISO format date string (e.g., "2025-11-11T23:59:59Z") for latest close time
        """
        url = f"{self.base_url}/markets"
        params = {
            "limit": 200,
            "status": "settled",  # Use 'settled' status to get closed markets with results
            "series_ticker": "KXBTCD"  # Bitcoin hourly markets
        }
        
        # Add close time filters if provided - convert to Unix timestamps
        if min_close_date:
            min_dt = datetime.fromisoformat(min_close_date.replace('Z', '+00:00'))
            params["min_close_ts"] = int(min_dt.timestamp())
        if max_close_date:
            max_dt = datetime.fromisoformat(max_close_date.replace('Z', '+00:00'))
            params["max_close_ts"] = int(max_dt.timestamp())
        
        all_markets = []
        cursor = None
        
        while True:
            if cursor:
                params["cursor"] = cursor
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching markets: {response.status_code}")
                print(response.text)
                break
            
            data = response.json()
            markets = data.get("markets", [])
            
            print(f"DEBUG: Raw markets returned: {len(markets)}")
            if len(markets) > 0:
                print(f"DEBUG: First market ticker: {markets[0].get('ticker')}")
                print(f"DEBUG: First market status: {markets[0].get('status')}")
                print(f"DEBUG: First market result: {markets[0].get('result')}")
            
            # Filter to only KXBTCD markets (Bitcoin hourly)
            bitcoin_markets = [m for m in markets if m.get("ticker", "").startswith("KXBTCD-")]
            all_markets.extend(bitcoin_markets)
            
            print(f"Fetched {len(bitcoin_markets)} Bitcoin markets... Total: {len(all_markets)}")
            
            cursor = data.get("cursor")
            if not cursor:
                break
            
            time.sleep(0.5)  # Rate limiting
        
        print(f"\nDEBUG: Final total markets: {len(all_markets)}")
        if len(all_markets) > 0:
            print(f"DEBUG: Sample tickers: {[m.get('ticker') for m in all_markets[:3]]}")
        
        return all_markets
    
    def parse_event_ticker(self, market_ticker: str) -> str:
        """
        Extract event ticker from full market ticker
        Example: KXBTCD-25NOV1417-T100249.99 -> KXBTCD-25NOV1417
        """
        parts = market_ticker.split("-T")
        return parts[0] if len(parts) > 0 else market_ticker
    
    def get_market_trades_in_window(self, market_ticker: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Get trades for a market within a specific time window
        """
        url = f"{self.base_url}/markets/trades"
        
        params = {
            "ticker": market_ticker,
            "min_ts": int(start_time.timestamp()),
            "max_ts": int(end_time.timestamp()),
            "limit": 1000
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        return data.get("trades", [])
    
    def extract_final_15min_data(self, market_ticker: str, close_time: str) -> Optional[Dict]:
        """
        Extract trading data from the final 15 minutes before settlement
        Returns: dict with final prices at various intervals and resolution outcome
        """
        # Parse close time
        close_dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
        cutoff_15min = close_dt - timedelta(minutes=15)
        cutoff_10min = close_dt - timedelta(minutes=10)
        cutoff_5min = close_dt - timedelta(minutes=5)
        cutoff_1min = close_dt - timedelta(minutes=1)
        
        # Get trades in final 15 minutes
        trades = self.get_market_trades_in_window(market_ticker, cutoff_15min, close_dt)
        
        if not trades:
            return None
        
        # Convert trades to price snapshots
        snapshots = []
        for trade in trades:
            trade_time_str = trade.get("created_time")
            if not trade_time_str:
                continue
            
            trade_time = datetime.fromisoformat(trade_time_str.replace('Z', '+00:00'))
            yes_price = trade.get("yes_price")
            
            if yes_price is not None:
                snapshots.append({
                    "time": trade_time,
                    "price": yes_price / 100.0  # Convert cents to probability
                })
        
        if not snapshots:
            return None
        
        # Find prices at specific time points (closest trade to each target time)
        def find_closest_price(target_time):
            closest = min(snapshots, key=lambda x: abs((x["time"] - target_time).total_seconds()))
            return closest["price"]
        
        return {
            "price_15min": find_closest_price(cutoff_15min),
            "price_10min": find_closest_price(cutoff_10min),
            "price_5min": find_closest_price(cutoff_5min),
            "price_1min": find_closest_price(cutoff_1min),
            "final_snapshots_count": len(snapshots)
        }
    
    def get_market_result(self, market_ticker: str) -> Optional[Dict]:
        """
        Get the full market details including result and any price data
        Returns dict with result and available price info
        """
        url = f"{self.base_url}/markets/{market_ticker}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        market = data.get("market", {})
        
        # Return relevant fields
        return {
            "result": market.get("result"),
            "last_price": market.get("last_price"),  # Might have final price
            "yes_bid": market.get("yes_bid"),
            "yes_ask": market.get("yes_ask"),
            "settlement_value": market.get("settlement_value")
        }
    
    def analyze_all_markets(self, output_file: str = "bitcoin_hourly_analysis.csv", 
                           min_close_date: Optional[str] = None, 
                           max_close_date: Optional[str] = None):
        """
        Main analysis pipeline:
        1. Get all settled Bitcoin hourly markets
        2. For each event, get top 5 volume strikes
        3. Extract final 15min data and outcome
        4. Save to CSV
        
        Args:
            output_file: CSV filename for results
            min_close_date: Optional ISO format date (e.g., "2025-10-01T00:00:00Z") for earliest close time
            max_close_date: Optional ISO format date (e.g., "2025-11-11T23:59:59Z") for latest close time
        """
        global _global_results, _global_output_file
        _global_output_file = output_file
        
        print("Fetching settled Bitcoin hourly markets...")
        print("💡 Press Ctrl+C at any time to stop and save collected data")
        if min_close_date or max_close_date:
            print(f"Date range: {min_close_date or 'beginning'} to {max_close_date or 'now'}")
        
        markets = self.get_settled_bitcoin_hourly_markets(min_close_date, max_close_date)
        
        print(f"\nFound {len(markets)} settled markets")
        
        # Group markets by event ticker (parsed from full ticker)
        # Example: KXBTCD-25NOV1417-T100249.99 -> KXBTCD-25NOV1417
        events = {}
        for market in markets:
            ticker = market.get("ticker")
            event_ticker = self.parse_event_ticker(ticker)
            
            if event_ticker not in events:
                events[event_ticker] = []
            events[event_ticker].append(market)
        
        print(f"Found {len(events)} unique events")
        
        results = []
        _global_results = results  # Make accessible to interrupt handler
        
        for event_ticker, event_markets in events.items():
            print(f"\n{'='*60}")
            print(f"Processing event: {event_ticker}")
            
            # Sort strikes by volume and take top 5
            markets_with_volume = [m for m in event_markets if m.get("volume", 0) > 0]
            markets_with_volume.sort(key=lambda x: x.get("volume", 0), reverse=True)
            top_markets = markets_with_volume[:5]
            
            print(f"  Top 5 strikes by volume: {[m['ticker'] for m in top_markets]}")
            
            for market in top_markets:
                ticker = market["ticker"]
                close_time = market.get("close_time") or market.get("expiration_time")
                
                if not close_time:
                    print(f"  Skipping {ticker}: no close time")
                    continue
                
                print(f"  Analyzing {ticker}...")
                
                # Get result and any available price data
                market_details = self.get_market_result(ticker)
                
                if not market_details or not market_details.get("result"):
                    print(f"    No result found")
                    continue
                
                result = market_details["result"]
                result_binary = 1 if result.lower() == "yes" else 0
                
                # Try to get historical price data
                final_data = self.extract_final_15min_data(ticker, close_time)
                
                # Save data with whatever price info we have
                result_row = {
                    "ticker": ticker,
                    "event_ticker": event_ticker,
                    "close_time": close_time,
                    "result": result,
                    "result_binary": result_binary,
                    "volume": market.get("volume", 0),
                    "last_price": market_details.get("last_price"),  # Final price if available
                }
                
                # Add historical price data if available
                if final_data:
                    result_row.update({
                        "price_15min": final_data["price_15min"],
                        "price_10min": final_data["price_10min"],
                        "price_5min": final_data["price_5min"],
                        "price_1min": final_data["price_1min"],
                        "snapshots_in_window": final_data["final_snapshots_count"]
                    })
                    print(f"    ✓ Price history available - 15min: {final_data['price_15min']:.2%}, Result: {result}")
                else:
                    result_row.update({
                        "price_15min": None,
                        "price_10min": None,
                        "price_5min": None,
                        "price_1min": None,
                        "snapshots_in_window": 0
                    })
                    last_price_str = f", Last price: {market_details.get('last_price')}" if market_details.get('last_price') else ""
                    print(f"    ✓ No price history{last_price_str}, Result: {result}")
                
                results.append(result_row)
                
                time.sleep(0.2)  # Rate limiting
        
        # Save to CSV
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
        
        print(f"\n{'='*60}")
        print(f"Analysis complete! Saved {len(results)} market records to {output_file}")
        
        return df


if __name__ == "__main__":
    # Load API key from .env file
    API_KEY = os.getenv("KALSHI_API_KEY_ID")
    
    if not API_KEY:
        raise ValueError("KALSHI_API_KEY_ID not found in .env file")
    
    analyzer = KalshiHistoricalAnalyzer(API_KEY)
    
    # Analyze last 30 days of markets (adjust as needed)
    # For all time, remove the date parameters
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)
    
    df = analyzer.analyze_all_markets(
        min_close_date=start_date.strftime("%Y-%m-%dT00:00:00Z"),
        max_close_date=end_date.strftime("%Y-%m-%dT23:59:59Z")
    )
    
    print("\nPreview of results:")
    print(df.head())