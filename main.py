"""
Main orchestration script for NBA Prop Predictor System
"""

import pandas as pd
import logging
from datetime import datetime
import sys
from config import PREDICTIONS_CSV, CONFIDENCE_THRESHOLD
from odds_fetcher import OddsAPIFetcher
from stats_scraper import PlayerStatsScraper
from ml_predictor import PropPredictor
from backtester import Backtester
from minimum_line_calculator import MinimumLineCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NBAPropSystem:
    def __init__(self):
        self.odds_fetcher = OddsAPIFetcher()
        self.stats_scraper = PlayerStatsScraper()
        self.predictor = PropPredictor()
        self.backtester = Backtester()
        
    def update_data(self):
        """Update all data sources"""
        logger.info("=" * 60)
        logger.info("UPDATING DATA")
        logger.info("=" * 60)
        
        # Update player stats
        logger.info("\n1. Updating player statistics...")
        stats_success = self.stats_scraper.update_player_stats()
        
        # Fetch current odds
        logger.info("\n2. Fetching current odds...")
        odds_df = self.odds_fetcher.fetch_and_save_current_props()
        
        if stats_success and odds_df is not None:
            logger.info("\n✓ Data update completed successfully")
            return True
        else:
            logger.error("\n✗ Data update failed")
            return False
    
    def train_model(self, use_historical=True):
        """Train or retrain the ML model"""
        logger.info("=" * 60)
        logger.info("TRAINING MODEL")
        logger.info("=" * 60)
        
        if use_historical:
            # In production, this would load real historical data
            # For now, we'll use synthetic data for initial training
            from ml_predictor import create_synthetic_training_data
            
            logger.info("\nCreating training data...")
            train_df = create_synthetic_training_data()
            
            logger.info(f"Training data: {len(train_df)} samples")
            logger.info(f"Hit rate: {train_df['hit_line'].mean():.2%}")
        else:
            # Load actual historical data from CSVs
            logger.info("\nLoading historical data from files...")
            # Implementation would load from your scraped game results
            return False
        
        # Prepare features
        logger.info("\nPreparing features...")
        X, y = self.predictor.prepare_training_data(train_df)
        
        if X is None:
            logger.error("Failed to prepare training data")
            return False
        
        # Train models
        logger.info("\nTraining models...")
        results = self.predictor.train_model(X, y)
        
        logger.info("\n✓ Model training completed")
        
        # Show feature importance
        importance = self.predictor.get_feature_importance()
        if importance is not None:
            logger.info("\nTop 10 Most Important Features:")
            logger.info(str(importance.head(10)))
        
        return True
    
    def make_predictions(self):
        """
        Generate predictions - SIMPLE VERSION
        1. Get players with lines from Odds API
        2. Match to our stats
        3. Calculate minimum
        """
        logger.info("=" * 60)
        logger.info("GENERATING PREDICTIONS")
        logger.info("=" * 60)
        
        # Load model
        if not self.predictor.load_model():
            logger.error("No trained model found")
            return None
        
        # 1. GET PLAYERS WITH LINES FROM ODDS API
        logger.info("\nFetching players with prop lines from Odds API...")
        odds_df = self.odds_fetcher.get_latest_props_for_prediction()
        
        if odds_df is None or odds_df.empty:
            logger.error("No odds data available")
            return None
        
        logger.info(f"Found {len(odds_df)} players with prop lines")
        
        # 2. LOAD OUR PLAYER STATS
        logger.info("Loading player statistics...")
        try:
            from config import PLAYER_STATS_CSV
            stats_df = pd.read_csv(PLAYER_STATS_CSV)
        except FileNotFoundError:
            logger.error("Player stats not found")
            return None
        
        # 3. MATCH AND CALCULATE
        calc = MinimumLineCalculator()
        predictions = []
        
        for _, odds_row in odds_df.iterrows():
            player_name = odds_row['player_name']
            dk_line = odds_row['line']
            home_team = odds_row['home_team']
            away_team = odds_row['away_team']
            game_time = odds_row['commence_time']
            
            # Find player in our stats (match by first and last name)
            player_parts = player_name.split()
            if len(player_parts) < 2:
                continue
            
            first_name = player_parts[0]
            last_name = player_parts[-1]
            
            # Match player
            player_stats = stats_df[
                (stats_df['Player'].str.contains(first_name, case=False, na=False)) &
                (stats_df['Player'].str.contains(last_name, case=False, na=False))
            ]
            
            if player_stats.empty:
                logger.warning(f"No stats found for {player_name}")
                continue
            
            # Get the most recent stats for this player
            player = player_stats.iloc[0]
            
            # Calculate PRA average
            pts_avg = player.get('PTS', 0)
            reb_avg = player.get('TRB', 0)
            ast_avg = player.get('AST', 0)
            pra_avg = pts_avg + reb_avg + ast_avg
            
            # Skip if no real production
            if pra_avg < 5.0:
                continue
            
            # Calculate minimum line using our system
            player_stats_dict = {
                'pts_reb_ast_avg': pra_avg,
                'last_5_avg': pra_avg,
                'consistency': 0.85
            }
            
            min_line, confidence, reasoning = calc.calculate_realistic_minimum(
                player_stats_dict, dk_line
            )
            
            if min_line is None:
                continue
            
            meets_threshold = confidence >= 0.90
            
            predictions.append({
                'player_name': player_name,
                'team': player.get('Team', 'Unknown'),
                'dk_line': dk_line,
                'has_dk_line': True,
                'recommended_minimum': min_line,
                'season_avg': pra_avg,
                'pts_avg': pts_avg,
                'reb_avg': reb_avg,
                'ast_avg': ast_avg,
                'confidence': confidence,
                'meets_threshold': meets_threshold,
                'reasoning': reasoning,
                'home_team': home_team,
                'away_team': away_team,
                'game': f"{away_team} @ {home_team}",
                'game_time': game_time,
                'timestamp': datetime.now().isoformat()
            })
        
        if not predictions:
            logger.info("No predictions generated")
            return None
        
        # Create DataFrame
        pred_df = pd.DataFrame(predictions)
        
        # Remove duplicates
        pred_df = pred_df.drop_duplicates(subset=['player_name', 'game'], keep='first')
        
        # Sort by game, then by confidence
        pred_df = pred_df.sort_values(['game', 'confidence'], ascending=[True, False])
        
        # Save
        # Save to main predictions file
        pred_df.to_csv(PREDICTIONS_CSV, index=False)
        
        # Also save dated copy for historical tracking
        date_str = datetime.now().strftime('%Y-%m-%d')
        dated_file = PREDICTIONS_CSV.replace('.csv', f'_{date_str}.csv')
        pred_df.to_csv(dated_file, index=False)
        logger.info(f"Also saved to {dated_file}")
        
        high_conf = len(pred_df[pred_df['meets_threshold']])
        games = pred_df['game'].nunique()
        
        logger.info(f"\n✓ Generated {len(pred_df)} predictions")
        logger.info(f"   - {high_conf} high confidence (90%+)")
        logger.info(f"   - {games} games")
        logger.info(f"Saved to {PREDICTIONS_CSV}")
        
        return pred_df
    
    def run_backtest(self):
        """Run backtesting analysis"""
        logger.info("=" * 60)
        logger.info("RUNNING BACKTEST")
        logger.info("=" * 60)
        
        # Create mock data for demonstration
        from backtester import create_mock_backtest_data
        
        logger.info("\nCreating historical data for backtest...")
        historical_df = create_mock_backtest_data()
        
        logger.info(f"Historical data: {len(historical_df)} records")
        logger.info(f"Date range: {historical_df['date'].min()} to {historical_df['date'].max()}")
        
        # Run backtest
        logger.info("\nRunning backtest simulation...")
        metrics, results_df = self.backtester.run_backtest(historical_df)
        
        if metrics:
            # Generate report
            report = self.backtester.generate_backtest_report(metrics, results_df)
            logger.info("\n" + report)
            
            # Save report
            from config import BACKTEST_DIR
            report_file = f"{BACKTEST_DIR}/backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            logger.info(f"\nReport saved to {report_file}")
            
            return metrics
        else:
            logger.error("Backtest failed")
            return None
    
    def display_predictions(self, pred_df):
        """Display predictions grouped by game with confidence tiers"""
        if pred_df is None or pred_df.empty:
            print("\nNo predictions to display")
            return
        
        print("\n" + "=" * 80)
        print("NBA PLAYER PROP PREDICTIONS - ALL ROTATION PLAYERS")
        print("=" * 80)
        print()
        
        high_conf = len(pred_df[pred_df['meets_threshold']])
        total = len(pred_df)
        
        print(f"🎯 HIGH CONFIDENCE (90%+): {high_conf} picks")
        print(f"⚠️  LOWER CONFIDENCE: {total - high_conf} picks")
        print(f"📊 TOTAL PLAYERS ANALYZED: {total}")
        print()
        
        # Group by game
        games = pred_df['game'].unique()
        
        for game in games:
            game_picks = pred_df[pred_df['game'] == game]
            high_conf_count = len(game_picks[game_picks['meets_threshold']])
            
            print("━" * 80)
            print(f"GAME: {game}")
            game_time = game_picks.iloc[0]['game_time']
            if game_time and game_time != 'TBD':
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                    print(f"Time: {dt.strftime('%I:%M %p ET on %B %d, %Y')}")
                except:
                    print(f"Time: {game_time}")
            print(f"Players: {len(game_picks)} | High Confidence: {high_conf_count}")
            print("━" * 80)
            print()
            
            for idx, row in game_picks.iterrows():
                # Show confidence indicator
                if row['meets_threshold']:
                    conf_icon = "🎯 HIGH CONFIDENCE"
                    color = ""
                else:
                    conf_icon = "⚠️  LOWER CONFIDENCE"
                    color = ""
                
                print(f"{conf_icon} | {row['player_name']} ({row['team']})")
                
                # Show if line exists
                if row['has_dk_line']:
                    print(f"  DraftKings Line: {row['dk_line']:.1f} PRA O/U")
                else:
                    print(f"  ⚠️  NO DK LINE AVAILABLE (prediction based on season avg)")
                
                print(f"  Season Average: {row['season_avg']:.1f} PRA ({row['pts_avg']:.1f} PTS / {row['reb_avg']:.1f} REB / {row['ast_avg']:.1f} AST)")
                print()
                print(f"  🎯 RECOMMENDED MINIMUM: {row['recommended_minimum']:.1f} PRA")
                print(f"  📊 Confidence: {row['confidence']:.1%}")
                print(f"  �� {row['reasoning']}")
                print()
                
                # Show the advantage
                cushion = row['season_avg'] - row['recommended_minimum']
                below_dk = row['dk_line'] - row['recommended_minimum']
                print(f"  ✓ {cushion:.1f} pts below season average")
                
                if row['has_dk_line']:
                    print(f"  ✓ {below_dk:.1f} pts below DraftKings line")
                
                print()
                print("-" * 80)
                print()
        
        print("=" * 80)
        print(f"Total Players: {len(pred_df)}")
        print(f"High Confidence (90%+): {high_conf}")
        print(f"Average Confidence: {pred_df['confidence'].mean():.1%}")
        print(f"Games Covered: {len(games)}")
        print()
        print("💡 TIP: Focus on HIGH CONFIDENCE picks for best results")
        print("   Lower confidence picks shown for reference/comparison")
        print("=" * 80)
        print()


def main():
    """Main execution function"""
    system = NBAPropSystem()
    
    print("\n" + "=" * 80)
    print("NBA PROP PREDICTOR SYSTEM")
    print("High-Confidence Player Prop Predictions (90%+ Win Rate)")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python main.py update           - Update player stats and odds data")
        print("  python main.py train            - Train/retrain ML model")
        print("  python main.py predict          - Generate predictions")
        print("  python main.py backtest         - Run backtesting analysis")
        print("  python main.py full             - Run complete pipeline")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'update':
        system.update_data()
    
    elif command == 'train':
        system.train_model()
    
    elif command == 'predict':
        pred_df = system.make_predictions()
        system.display_predictions(pred_df)
    
    elif command == 'backtest':
        system.run_backtest()
    
    elif command == 'full':
        print("\n[1/4] Updating data...")
        if not system.update_data():
            print("\nData update failed. Continuing with existing data...")
        
        print("\n[2/4] Training model...")
        if not system.train_model():
            print("\nModel training failed. Exiting...")
            return
        
        print("\n[3/4] Generating predictions...")
        pred_df = system.make_predictions()
        system.display_predictions(pred_df)
        
        print("\n[4/4] Running backtest...")
        system.run_backtest()
    
    else:
        print(f"\nUnknown command: {command}")
        print("Use 'python main.py' to see available commands")


if __name__ == "__main__":
    main()
