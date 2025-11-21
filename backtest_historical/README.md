# Historical Backtesting System

This module allows you to backtest the prediction system using REAL historical data.

## How It Works

1. **Scrape historical game results** from Basketball Reference
2. **Calculate what our system would have recommended** for each player
3. **Compare to actual performance** to calculate win rate

## Usage

### Step 1: Scrape Historical Data
```bash
cd backtest_historical

# Scrape games from a date range
python historical_scraper.py 2025-11-01 2025-11-15

# This creates: ../data/backtest/historical_results_2025-11-01_to_2025-11-15.csv
```

### Step 2: Run Backtest
```bash
# Run backtest on scraped data
python real_backtest.py ../data/backtest/historical_results_2025-11-01_to_2025-11-15.csv
```

### Output

The backtest will show:
- Total predictions made
- Overall win rate
- Win rate for 90%+ confidence picks
- Sample predictions with actual vs recommended

## Example
```bash
# Scrape last 2 weeks
python historical_scraper.py 2025-11-05 2025-11-19

# Run backtest
python real_backtest.py ../data/backtest/historical_results_2025-11-05_to_2025-11-19.csv
```

## Notes

- Be respectful of Basketball Reference (3-5 second delays between requests)
- Scraping 2 weeks of data takes ~15-30 minutes
- The backtest uses current season averages (simplified)
- For true accuracy, you'd need historical averages as of each date
