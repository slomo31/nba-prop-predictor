"""
Utility functions for NBA Prop Predictor System
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import logging
from config import (
    PLAYER_STATS_CSV, ODDS_DATA_CSV, PREDICTIONS_CSV,
    BACKTEST_RESULTS_CSV, CSV_DIR
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_old_data(days_to_keep=30):
    """Remove old data from CSV files to keep them manageable"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    print(f"Cleaning data older than {cutoff_date.date()}...")
    
    # Clean odds data
    try:
        df = pd.read_csv(ODDS_DATA_CSV)
        df['fetched_at'] = pd.to_datetime(df['fetched_at'])
        
        original_len = len(df)
        df = df[df['fetched_at'] >= cutoff_date]
        
        df.to_csv(ODDS_DATA_CSV, index=False)
        print(f"  Odds data: Removed {original_len - len(df)} old records")
    except Exception as e:
        print(f"  Could not clean odds data: {e}")
    
    # Clean predictions
    try:
        df = pd.read_csv(PREDICTIONS_CSV)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        original_len = len(df)
        df = df[df['timestamp'] >= cutoff_date]
        
        df.to_csv(PREDICTIONS_CSV, index=False)
        print(f"  Predictions: Removed {original_len - len(df)} old records")
    except Exception as e:
        print(f"  Could not clean predictions: {e}")
    
    print("✓ Data cleanup complete")


def export_predictions_to_format(format='txt'):
    """Export predictions to human-readable format"""
    try:
        df = pd.read_csv(PREDICTIONS_CSV)
        
        if df.empty:
            print("No predictions to export")
            return
        
        # Get most recent predictions
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        latest_timestamp = df['timestamp'].max()
        df_latest = df[df['timestamp'] == latest_timestamp]
        
        output_file = f"{CSV_DIR}/predictions_export_{datetime.now().strftime('%Y%m%d')}.{format}"
        
        if format == 'txt':
            with open(output_file, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write("NBA PROP PREDICTIONS\n")
                f.write(f"Generated: {latest_timestamp}\n")
                f.write("=" * 80 + "\n\n")
                
                for _, row in df_latest.iterrows():
                    f.write(f"Player: {row['player_name']}\n")
                    f.write(f"Line: {row['line']:.1f} Pts+Reb+Ast\n")
                    f.write(f"Prediction: {'OVER' if row['predicted_hit'] else 'UNDER'}\n")
                    f.write(f"Confidence: {row['confidence']:.1%}\n")
                    f.write(f"Season Avg: {row['pts_reb_ast_avg']:.1f}\n")
                    f.write("-" * 80 + "\n\n")
        
        print(f"✓ Exported {len(df_latest)} predictions to {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Export failed: {e}")
        return None


def get_prediction_summary():
    """Get summary statistics of recent predictions"""
    try:
        df = pd.read_csv(PREDICTIONS_CSV)
        
        if df.empty:
            return "No predictions available"
        
        summary = []
        summary.append("PREDICTION SUMMARY")
        summary.append("=" * 50)
        summary.append(f"Total predictions: {len(df)}")
        summary.append(f"Average confidence: {df['confidence'].mean():.1%}")
        summary.append(f"Min confidence: {df['confidence'].min():.1%}")
        summary.append(f"Max confidence: {df['confidence'].max():.1%}")
        
        # By predicted outcome
        if 'predicted_hit' in df.columns:
            over_count = df['predicted_hit'].sum()
            under_count = len(df) - over_count
            summary.append(f"\nOVER predictions: {over_count}")
            summary.append(f"UNDER predictions: {under_count}")
        
        return "\n".join(summary)
        
    except Exception as e:
        return f"Error generating summary: {e}"


def check_data_freshness():
    """Check how recent the data is"""
    print("\nDATA FRESHNESS CHECK")
    print("=" * 50)
    
    # Check player stats
    try:
        df = pd.read_csv(PLAYER_STATS_CSV)
        if 'scraped_at' in df.columns:
            last_update = pd.to_datetime(df['scraped_at']).max()
            hours_old = (datetime.now() - last_update).total_seconds() / 3600
            print(f"Player stats: {last_update.strftime('%Y-%m-%d %H:%M')} ({hours_old:.1f} hours ago)")
        else:
            print("Player stats: No timestamp available")
    except FileNotFoundError:
        print("Player stats: Not found")
    
    # Check odds data
    try:
        df = pd.read_csv(ODDS_DATA_CSV)
        if 'fetched_at' in df.columns:
            last_update = pd.to_datetime(df['fetched_at']).max()
            hours_old = (datetime.now() - last_update).total_seconds() / 3600
            print(f"Odds data: {last_update.strftime('%Y-%m-%d %H:%M')} ({hours_old:.1f} hours ago)")
        else:
            print("Odds data: No timestamp available")
    except FileNotFoundError:
        print("Odds data: Not found")
    
    # Check predictions
    try:
        df = pd.read_csv(PREDICTIONS_CSV)
        if 'timestamp' in df.columns:
            last_update = pd.to_datetime(df['timestamp']).max()
            hours_old = (datetime.now() - last_update).total_seconds() / 3600
            print(f"Predictions: {last_update.strftime('%Y-%m-%d %H:%M')} ({hours_old:.1f} hours ago)")
        else:
            print("Predictions: No timestamp available")
    except FileNotFoundError:
        print("Predictions: Not found")


def get_csv_stats():
    """Get statistics about all CSV files"""
    print("\nCSV FILE STATISTICS")
    print("=" * 50)
    
    csv_files = {
        'Player Stats': PLAYER_STATS_CSV,
        'Odds Data': ODDS_DATA_CSV,
        'Predictions': PREDICTIONS_CSV,
        'Backtest Results': BACKTEST_RESULTS_CSV
    }
    
    total_size = 0
    
    for name, filepath in csv_files.items():
        try:
            df = pd.read_csv(filepath)
            file_size = os.path.getsize(filepath) / 1024  # KB
            total_size += file_size
            
            print(f"\n{name}:")
            print(f"  Records: {len(df):,}")
            print(f"  Columns: {len(df.columns)}")
            print(f"  File size: {file_size:.1f} KB")
            
        except FileNotFoundError:
            print(f"\n{name}: Not found")
    
    print(f"\nTotal CSV size: {total_size:.1f} KB")


def merge_duplicate_player_records():
    """Merge duplicate player records in stats file"""
    try:
        df = pd.read_csv(PLAYER_STATS_CSV)
        
        original_len = len(df)
        
        # Keep most recent record for each player-team combination
        df = df.sort_values('scraped_at', ascending=False)
        df = df.drop_duplicates(subset=['Player', 'Tm'], keep='first')
        
        df.to_csv(PLAYER_STATS_CSV, index=False)
        
        removed = original_len - len(df)
        print(f"✓ Merged {removed} duplicate player records")
        
    except Exception as e:
        print(f"Could not merge duplicates: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("\nUtility Functions:")
        print("  python utils.py clean              - Clean old data")
        print("  python utils.py export             - Export predictions")
        print("  python utils.py summary            - Show prediction summary")
        print("  python utils.py freshness          - Check data freshness")
        print("  python utils.py stats              - Show CSV statistics")
        print("  python utils.py merge              - Merge duplicate records")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == 'clean':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        clean_old_data(days)
    
    elif command == 'export':
        export_predictions_to_format()
    
    elif command == 'summary':
        print(get_prediction_summary())
    
    elif command == 'freshness':
        check_data_freshness()
    
    elif command == 'stats':
        get_csv_stats()
    
    elif command == 'merge':
        merge_duplicate_player_records()
    
    else:
        print(f"Unknown command: {command}")
