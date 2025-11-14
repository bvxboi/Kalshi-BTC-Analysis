# CLAUDE.md - Kalshi Bitcoin Analysis Codebase Guide

## Project Overview

**Purpose**: Analyze historical Bitcoin price prediction markets on Kalshi to identify trading patterns and potential edge opportunities.

**Key Functionality**: Fetches settled Bitcoin hourly markets (KXBTCD series) from Kalshi API, extracts trading data from the final 15 minutes before settlement, and correlates with actual outcomes to analyze market efficiency.

**Tech Stack**: Python 3, pandas, requests, dotenv

---

## Codebase Structure

```
Kalshi-BTC-Analysis/
├── DataScraper.py          # Main production scraper (primary module)
├── Debug.py                # API connection testing and debugging
├── diagnose_markets.py     # Market data exploration and diagnostics
├── README.md               # Project description
├── LICENSE                 # MIT License
└── .gitignore             # Excludes: .env, *.csv, test files
```

### File Purposes

**DataScraper.py** (Main Module - 354 lines)
- Production-ready historical data scraper
- Class: `KalshiHistoricalAnalyzer`
- Fetches settled Bitcoin hourly markets from Kalshi API
- Extracts final 15-minute trading data before settlement
- Outputs structured CSV with market outcomes and price history
- Includes graceful interrupt handling (Ctrl+C saves partial data)

**Debug.py** (89 lines)
- API authentication testing
- Market availability verification
- Series ticker validation (KXBTCD)
- Quick diagnostics for API issues

**diagnose_markets.py** (59 lines)
- Market status distribution analysis
- Volume analysis for KXBTCD markets
- Quick market exploration utility

---

## Key Components

### KalshiHistoricalAnalyzer Class
Located in: `DataScraper.py:33`

**Constructor**: `__init__(self, api_key: str)` - DataScraper.py:34
- Initializes API client with Bearer token authentication
- Base URL: `https://api.elections.kalshi.com/trade-api/v2`

**Core Methods**:

1. `get_settled_bitcoin_hourly_markets(min_close_date, max_close_date)` - DataScraper.py:42
   - Fetches all settled markets with series ticker "KXBTCD"
   - Supports pagination via cursor
   - Returns list of market dictionaries
   - Includes rate limiting (0.5s delay)

2. `parse_event_ticker(market_ticker)` - DataScraper.py:107
   - Extracts event ticker from full market ticker
   - Format: `KXBTCD-25NOV1417-T100249.99` → `KXBTCD-25NOV1417`

3. `get_market_trades_in_window(market_ticker, start_time, end_time)` - DataScraper.py:115
   - Retrieves trades within specific time window
   - Used for final 15-minute analysis
   - Max 1000 trades per request

4. `extract_final_15min_data(market_ticker, close_time)` - DataScraper.py:136
   - Key analysis function
   - Extracts YES prices at: 15min, 10min, 5min, 1min before close
   - Finds closest trade to each target time
   - Returns price snapshots and trade count

5. `get_market_result(market_ticker)` - DataScraper.py:186
   - Fetches final market result (YES/NO)
   - Returns settlement value and final prices

6. `analyze_all_markets(output_file, min_close_date, max_close_date)` - DataScraper.py:210
   - **Main pipeline orchestrator**
   - Groups markets by event
   - Selects top 5 strikes by volume per event
   - Extracts data and saves to CSV
   - Includes progress logging

### Signal Handling
- Function: `signal_handler(sig, frame)` - DataScraper.py:19
- Gracefully handles Ctrl+C interrupts
- Saves partial results to CSV before exit
- Uses global variables: `_global_results`, `_global_output_file`

---

## Data Model

### Output CSV Schema
The scraper produces CSV files with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | string | Full market ticker (e.g., KXBTCD-25NOV1417-T100249.99) |
| `event_ticker` | string | Event identifier (e.g., KXBTCD-25NOV1417) |
| `close_time` | ISO datetime | Market settlement timestamp |
| `result` | string | Outcome: "yes" or "no" |
| `result_binary` | int | Binary outcome: 1 (yes) or 0 (no) |
| `volume` | int | Total trading volume |
| `last_price` | float | Final market price if available |
| `price_15min` | float | YES price 15 minutes before close (0-1 probability) |
| `price_10min` | float | YES price 10 minutes before close |
| `price_5min` | float | YES price 5 minutes before close |
| `price_1min` | float | YES price 1 minute before close |
| `snapshots_in_window` | int | Number of trades in final 15 minutes |

### Market Ticker Format
- **Series**: KXBTCD (Bitcoin hourly markets)
- **Format**: `KXBTCD-{DATE}{HOUR}-T{STRIKE}`
- **Example**: `KXBTCD-25NOV1417-T100249.99`
  - Date: November 25, 2025
  - Hour: 17:00 (5 PM)
  - Strike: $100,249.99

---

## Environment Setup

### Required Environment Variables
File: `.env` (gitignored)

```bash
KALSHI_API_KEY_ID=your_api_key_here
```

### Dependencies
Based on imports, install with:
```bash
pip install requests pandas python-dotenv
```

**Note**: No `requirements.txt` currently exists in the repository.

---

## API Integration

### Kalshi API Details
- **Base URL**: `https://api.elections.kalshi.com/trade-api/v2`
- **Authentication**: Bearer token in Authorization header
- **Rate Limiting**: Implemented with sleep delays (0.2-0.5s between requests)

### Key Endpoints Used

1. **List Markets**: `GET /markets`
   - Params: `series_ticker`, `status`, `limit`, `cursor`, `min_close_ts`, `max_close_ts`
   - Used in: DataScraper.py:51

2. **Get Market Details**: `GET /markets/{ticker}`
   - Returns: result, prices, settlement value
   - Used in: DataScraper.py:191

3. **List Trades**: `GET /markets/trades`
   - Params: `ticker`, `min_ts`, `max_ts`, `limit`
   - Used in: DataScraper.py:119

### Price Conversion
- API returns prices in cents (0-100)
- Converted to probability (0-1) by dividing by 100
- See: DataScraper.py:167

---

## Development Workflows

### Running the Main Scraper

```bash
python DataScraper.py
```

**Current Configuration** (DataScraper.py:342-351):
- Fetches last 5 days of settled markets
- Outputs to: `bitcoin_hourly_analysis.csv`
- Supports Ctrl+C for early termination with partial save

**Customization**:
```python
analyzer = KalshiHistoricalAnalyzer(API_KEY)
df = analyzer.analyze_all_markets(
    output_file="custom_output.csv",
    min_close_date="2025-10-01T00:00:00Z",
    max_close_date="2025-11-11T23:59:59Z"
)
```

### Testing API Access

```bash
python Debug.py
```
Runs 4 diagnostic tests:
1. Basic authentication verification
2. Bitcoin market search
3. KXBTCD series query
4. Settled market check

### Exploring Market Data

```bash
python diagnose_markets.py
```
Shows:
- Status distribution (active/settled/finalized)
- Volume statistics
- Sample market details

---

## Code Conventions

### Style Guidelines
1. **Type Hints**: Used extensively (e.g., `-> List[Dict]`, `-> Optional[Dict]`)
2. **Docstrings**: Present on all major methods with parameter descriptions
3. **Error Handling**:
   - HTTP status code checks
   - None-safe field access with `.get()`
   - Graceful degradation (partial data return)
4. **Logging**: Print statements with emoji indicators (⚠️, ✅, 💡)
5. **Constants**: API_KEY and BASE_URL extracted at module level

### Naming Conventions
- **Classes**: PascalCase (e.g., `KalshiHistoricalAnalyzer`)
- **Methods**: snake_case (e.g., `get_market_trades_in_window`)
- **Variables**: snake_case (e.g., `close_time`, `event_ticker`)
- **Private/Global**: Leading underscore (e.g., `_global_results`)

### Time Handling
- **Input Format**: ISO 8601 with Z suffix (e.g., "2025-10-01T00:00:00Z")
- **Internal**: Python `datetime` objects with timezone awareness
- **API**: Unix timestamps (seconds since epoch)
- Conversion example: DataScraper.py:60-64

---

## Common AI Assistant Tasks

### Adding New Features

1. **New Analysis Metrics**:
   - Extend `extract_final_15min_data()` in DataScraper.py:136
   - Add fields to result dictionary in `analyze_all_markets()` at DataScraper.py:288
   - Update CSV schema documentation in this file

2. **Different Time Windows**:
   - Modify time deltas in DataScraper.py:143-146
   - Adjust `get_market_trades_in_window()` calls
   - Update output schema

3. **Additional Market Series**:
   - Change `series_ticker` parameter in DataScraper.py:55
   - Update `parse_event_ticker()` logic if ticker format differs

### Debugging Issues

**API Authentication Failures**:
- Run `python Debug.py` first
- Verify `.env` file exists with correct key
- Check API key hasn't expired

**No Markets Returned**:
- Check date range (may be no settled markets in window)
- Verify series ticker is correct (KXBTCD for Bitcoin)
- Review status filter (settled vs active)

**Missing Price Data**:
- Some markets may have zero trades in final 15 minutes
- Check `snapshots_in_window` field in output
- Function handles gracefully by returning None (DataScraper.py:151-152)

### Testing Changes

1. **Small Date Range**: Use 1-2 days for quick testing
2. **Single Market**: Modify to process one event/market
3. **Dry Run**: Add return statement before CSV save
4. **Debug Logging**: Existing DEBUG prints available (DataScraper.py:83-104)

### Code Quality Checks

Before committing:
- [ ] All functions have type hints
- [ ] Docstrings updated for modified methods
- [ ] Rate limiting preserved (don't remove sleep calls)
- [ ] Error handling maintains graceful degradation
- [ ] Test with Debug.py for API changes
- [ ] Verify CSV output format unchanged (or update docs)

---

## Git Workflow

### Current Branch
Working branch: `claude/claude-md-mhz553a92eq8zlx0-01XzC5f88BcUBqnqkYFsdKva`

### Commit Guidelines
- Use descriptive messages (see git log for examples)
- Test code before committing
- Don't commit `.env` files or CSV data (gitignored)

### Pushing Changes
```bash
git add .
git commit -m "Description of changes"
git push -u origin claude/claude-md-mhz553a92eq8zlx0-01XzC5f88BcUBqnqkYFsdKva
```

---

## Architecture Patterns

### Data Flow
```
1. API Call (get_settled_bitcoin_hourly_markets)
   ↓
2. Group by Event (parse_event_ticker)
   ↓
3. Filter Top 5 by Volume
   ↓
4. For Each Market:
   a. Get Result (get_market_result)
   b. Get Trade History (get_market_trades_in_window)
   c. Extract Price Snapshots (extract_final_15min_data)
   ↓
5. Save to CSV (pandas DataFrame)
```

### Error Handling Strategy
- **Network Errors**: Return empty list/dict, log error
- **Missing Data**: Use None/0 defaults, include in output
- **Interrupts**: Signal handler saves partial results
- **API Errors**: Print status code and continue to next item

### Rate Limiting Approach
- 0.5s between market list pagination (DataScraper.py:99)
- 0.2s between individual market analysis (DataScraper.py:321)
- Prevents API throttling while maintaining reasonable speed

---

## Security Notes

### Sensitive Data
- **API Keys**: Stored in `.env` (gitignored)
- **Never commit**: .env files, test_closed.py (per .gitignore)
- **CSV Output**: May contain market data but no credentials

### API Key Handling
- Loaded via `python-dotenv` (DataScraper.py:13)
- Environment variable: `KALSHI_API_KEY_ID`
- Used in Authorization header as Bearer token

---

## Future Enhancements (Potential)

Based on codebase analysis, consider:
1. Add `requirements.txt` for dependency management
2. Implement caching to avoid re-fetching settled markets
3. Add statistical analysis module for edge detection
4. Create visualization module for price movement patterns
5. Add configuration file for customizable parameters
6. Implement database storage instead of CSV-only
7. Add unit tests for key functions
8. Create CLI argument parser for flexible execution

---

## Quick Reference

### Main Entry Point
```python
from DataScraper import KalshiHistoricalAnalyzer
analyzer = KalshiHistoricalAnalyzer(api_key)
df = analyzer.analyze_all_markets()
```

### Key Constants
- Series: `KXBTCD`
- API Base: `https://api.elections.kalshi.com/trade-api/v2`
- Default Output: `bitcoin_hourly_analysis.csv`
- Time Window: Final 15 minutes before settlement

### Important Timestamps
Line references for quick navigation:
- Main analyzer class: DataScraper.py:33
- Pipeline orchestrator: DataScraper.py:210
- Price extraction logic: DataScraper.py:136
- Signal handler: DataScraper.py:19
- API endpoints: DataScraper.py:51, 119, 191

---

**Last Updated**: 2025-11-14
**Repository**: https://github.com/bvxboi/Kalshi-BTC-Analysis
**License**: MIT
