"""
Configuration file for NBA Prop Predictor System
"""

import os

# API Configuration
ODDS_API_KEY = "a03349ac7178eb60a825d19bd27014ce"
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# Data Storage Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_DIR = os.path.join(DATA_DIR, "csv")
MODELS_DIR = os.path.join(DATA_DIR, "models")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
BACKTEST_DIR = os.path.join(DATA_DIR, "backtest")

# CSV File Paths
PLAYER_STATS_CSV = os.path.join(CSV_DIR, "player_stats.csv")
ODDS_DATA_CSV = os.path.join(CSV_DIR, "odds_data.csv")
PREDICTIONS_CSV = os.path.join(CSV_DIR, "predictions.csv")
BACKTEST_RESULTS_CSV = os.path.join(CSV_DIR, "backtest_results.csv")
GAME_RESULTS_CSV = os.path.join(CSV_DIR, "game_results.csv")

# Scraping Configuration
NBA_STATS_URL = "https://www.basketball-reference.com"
CURRENT_SEASON = "2026"
UPDATE_CHECKPOINT_FILE = os.path.join(DATA_DIR, "last_update.json")

# ML Configuration
CONFIDENCE_THRESHOLD = 0.90  # 90% confidence for high-probability picks
MIN_SAMPLES_FOR_TRAINING = 50
TEST_SIZE = 0.2
RANDOM_STATE = 42

# Features for ML Model
FEATURE_COLUMNS = [
    'games_played', 'minutes_avg', 'points_avg', 'rebounds_avg', 'assists_avg',
    'points_last_5', 'rebounds_last_5', 'assists_last_5',
    'home_away', 'days_rest', 'opponent_def_rating',
    'usage_rate', 'true_shooting_pct', 'pts_reb_ast_avg'
]

TARGET_COLUMN = 'hit_line'

# Backtesting Configuration
BACKTEST_START_DATE = "2024-10-01"
BACKTEST_DAYS = 30

# Create necessary directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(BACKTEST_DIR, exist_ok=True)
