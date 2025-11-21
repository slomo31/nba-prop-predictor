"""
Backtest using REAL historical data
"""

import pandas as pd
import sys
sys.path.append('..')

from minimum_line_calculator import MinimumLineCalculator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealBacktester:
    def __init__(self):
        self.calc = MinimumLineCalculator()
    
    def load_historical_results(self, filepath):
        """Load historical game results"""
        return pd.read_csv(filepath)
    
    def load_historical_averages(self, date):
        """
        Load what the season averages were at a specific date
        For simplicity, we'll use current season averages
        (In production, you'd need averages as of that date)
        """
        from config import PLAYER_STATS_CSV
        return pd.read_csv(PLAYER_STATS_CSV)
    
    def backtest(self, historical_results_file):
        """
        Run backtest on historical data
        
        For each game:
        1. Get what the player's average was
        2. Calculate our recommended minimum
        3. Check if player hit that minimum
        4. Calculate win rate
        """
        logger.info("="*60)
        logger.info("REAL HISTORICAL BACKTEST")
        logger.info("="*60)
        
        # Load historical results
        results = self.load_historical_results(historical_results_file)
        logger.info(f"\nLoaded {len(results)} historical performances")
        
        # Load current season averages (simplified)
        stats = self.load_historical_averages(None)
        
        predictions = []
        
        for _, result in results.iterrows():
            player_name = result['player_name']
            actual_pra = result['pra']
            date = result['date']
            
            # Find player in stats
            player_parts = player_name.split()
            if len(player_parts) < 2:
                continue
            
            first_name = player_parts[0]
            last_name = player_parts[-1]
            
            player_stats = stats[
                (stats['Player'].str.contains(first_name, case=False, na=False)) &
                (stats['Player'].str.contains(last_name, case=False, na=False))
            ]
            
            if player_stats.empty:
                continue
            
            player = player_stats.iloc[0]
            
            # Calculate season average
            pts_avg = player.get('PTS', 0)
            reb_avg = player.get('TRB', 0)
            ast_avg = player.get('AST', 0)
            pra_avg = pts_avg + reb_avg + ast_avg
            
            if pra_avg < 5.0:
                continue
            
            # Calculate our recommended minimum
            player_stats_dict = {
                'pts_reb_ast_avg': pra_avg,
                'last_5_avg': pra_avg,
                'consistency': 0.85
            }
            
            # Use player's average as the "line"
            min_line, confidence, reasoning = self.calc.calculate_realistic_minimum(
                player_stats_dict, pra_avg
            )
            
            if min_line is None:
                continue
            
            # Check if they hit it
            hit = actual_pra >= min_line
            
            predictions.append({
                'date': date,
                'player_name': player_name,
                'season_avg': pra_avg,
                'recommended_minimum': min_line,
                'actual_pra': actual_pra,
                'hit': hit,
                'confidence': confidence,
                'meets_90_threshold': confidence >= 0.90
            })
        
        # Create results DataFrame
        results_df = pd.DataFrame(predictions)
        
        if results_df.empty:
            logger.info("\nNo predictions to analyze")
            return
        
        # Calculate overall win rate
        total = len(results_df)
        wins = len(results_df[results_df['hit']])
        win_rate = (wins / total) * 100 if total > 0 else 0
        
        # Calculate win rate for 90%+ confidence picks
        high_conf = results_df[results_df['meets_90_threshold']]
        if not high_conf.empty:
            high_conf_wins = len(high_conf[high_conf['hit']])
            high_conf_total = len(high_conf)
            high_conf_rate = (high_conf_wins / high_conf_total) * 100
        else:
            high_conf_wins = 0
            high_conf_total = 0
            high_conf_rate = 0
        
        # Display results
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"\nTotal Predictions: {total}")
        print(f"Wins: {wins}")
        print(f"Losses: {total - wins}")
        print(f"Overall Win Rate: {win_rate:.1f}%")
        print()
        print(f"High Confidence (90%+) Predictions: {high_conf_total}")
        print(f"High Confidence Wins: {high_conf_wins}")
        print(f"High Confidence Win Rate: {high_conf_rate:.1f}%")
        print("="*60)
        
        # Show some examples
        print("\nSample Predictions:")
        print(results_df[['player_name', 'season_avg', 'recommended_minimum', 
                         'actual_pra', 'hit', 'confidence']].head(20))
        
        # Save results
        output_file = historical_results_file.replace('.csv', '_backtest_results.csv')
        results_df.to_csv(output_file, index=False)
        print(f"\n✓ Full results saved to {output_file}")
        
        return results_df


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python real_backtest.py HISTORICAL_RESULTS_FILE")
        print("\nExample:")
        print("  python real_backtest.py ../data/backtest/historical_results_2025-11-01_to_2025-11-15.csv")
        return
    
    results_file = sys.argv[1]
    
    backtester = RealBacktester()
    backtester.backtest(results_file)


if __name__ == "__main__":
    main()
