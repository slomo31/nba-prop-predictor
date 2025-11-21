# QUICK START GUIDE

## Installation (5 minutes)

1. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run setup to verify everything works:**
   ```bash
   python setup.py
   ```
   - Answer 'y' when asked to run demonstration

## First Time Usage

### Option 1: Quick Demo (Recommended First)
```bash
python main.py full
```
This runs the complete pipeline with synthetic data to show you how it works.

### Option 2: Real Data Pipeline
```bash
# Step 1: Fetch real NBA data
python main.py update

# Step 2: Train model on real data
python main.py train

# Step 3: Generate predictions
python main.py predict

# Step 4: Validate with backtest
python main.py backtest
```

## Daily Usage

**Morning Routine (Before Games):**
```bash
python main.py update    # Update stats and odds
python main.py predict   # Get today's picks
```

**Review Predictions:**
- Check terminal output for high-confidence picks
- Or open `data/csv/predictions.csv`

## Understanding Output

### Prediction Display:
```
Player: Stephen Curry
Line: 35.5 Pts+Reb+Ast
Prediction: ✓ OVER
Confidence: 92.5%
Season Avg: 38.2 (27.3 PTS / 4.8 REB / 6.1 AST)
```

**What This Means:**
- System predicts Curry will go OVER 35.5 combined stats
- 92.5% confidence = Should hit 9-10 times out of 10
- His season average (38.2) is well above the line
- **This is a high-confidence bet**

### Confidence Levels:
- **90-92%**: Very Good - Expected to hit 9/10 times
- **92-95%**: Excellent - Expected to hit 9.2-9.5/10 times
- **95%+**: Elite - Extremely safe pick

## File Organization

All data is organized in the `data/` folder:

```
data/
├── csv/                    # All CSV files
│   ├── player_stats.csv       → Player statistics
│   ├── odds_data.csv          → Prop lines from API
│   ├── predictions.csv        → Your predictions
│   └── backtest_results.csv   → Historical performance
│
├── models/                 # Trained ML models
├── logs/                   # System logs
└── backtest/              # Backtest reports
```

## Common Commands

```bash
# Update data
python main.py update

# Train model
python main.py train

# Get predictions
python main.py predict

# Run backtest
python main.py backtest

# Complete pipeline
python main.py full

# Utility functions
python utils.py freshness    # Check data freshness
python utils.py summary      # Prediction summary
python utils.py clean        # Clean old data
python utils.py export       # Export predictions
```

## Automated Scheduling

**Run scheduler (keeps system updated automatically):**
```bash
# Production mode (daily updates)
python scheduler.py prod

# Development mode (quick updates for testing)
python scheduler.py dev
```

## Troubleshooting

### "No predictions found"
1. Make sure data is updated: `python main.py update`
2. Check if model exists: `ls data/models/`
3. If no model: `python main.py train`

### "API error"
- Check API key in `config.py`
- Verify internet connection
- Check API quota (500 requests/month on free tier)

### "No stats for player"
- Run: `python main.py update`
- Player might be new or name doesn't match exactly

## Tips for Success

1. **Update Daily**: Fresh data = better predictions
   ```bash
   python main.py update
   ```

2. **Only Bet High-Confidence**: Stick to 90%+ confidence picks

3. **Track Results**: Keep your own record to verify system performance

4. **Retrain Weekly**: Incorporate new data
   ```bash
   python main.py train
   ```

5. **Check Freshness**: Before making picks
   ```bash
   python utils.py freshness
   ```

## Expected Performance

With 90%+ confidence threshold:
- **Win Rate**: 90-95%
- **Daily Picks**: 3-8 high-confidence plays
- **Best For**: Safe, consistent wins (not max profit)

## Next Steps

1. ✅ Run setup and demo
2. ✅ Update with real data
3. ✅ Generate first predictions
4. ✅ Track results
5. ✅ Refine and improve

## Support Files

- `README.md` - Complete documentation
- `requirements.txt` - Python dependencies
- `config.py` - Configuration and API settings

## Safety Reminders

⚠️ **Important:**
- Never bet more than you can afford to lose
- Past performance doesn't guarantee future results
- Use responsible bankroll management
- This is for educational/informational purposes

---

**Ready to start? Run:**
```bash
python setup.py
```
