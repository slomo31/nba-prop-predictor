"""
Track prediction results and calculate win/loss record
"""

import pandas as pd
import json
from datetime import datetime
from config import PREDICTIONS_CSV, CSV_DIR
import os

RESULTS_FILE = os.path.join(CSV_DIR, 'pick_results.csv')
RECORD_FILE = os.path.join(CSV_DIR, 'overall_record.json')


class ResultsTracker:
    def __init__(self):
        self.results_file = RESULTS_FILE
        self.record_file = RECORD_FILE
        
    def mark_result(self, player_name, date, result, actual_pra=None):
        """
        Mark a pick as win or loss
        
        Args:
            player_name: Player name
            date: Date of game (YYYY-MM-DD)
            result: 'W' for win, 'L' for loss
            actual_pra: Actual PRA scored (optional)
        """
        try:
            df = pd.read_csv(self.results_file)
        except FileNotFoundError:
            df = pd.DataFrame(columns=[
                'date', 'player_name', 'recommended_minimum', 
                'actual_pra', 'result', 'marked_at'
            ])
        
        # Get the prediction - use fuzzy matching
        pred_df = pd.read_csv(PREDICTIONS_CSV)
        
        # Try exact match first (normalized)
        pred_name_norm = player_name.replace('.', '').strip()
        pred = pred_df[pred_df['player_name'].str.replace('.', '').str.strip().str.lower() == pred_name_norm.lower()]
        
        # If no match, try last name
        if pred.empty:
            last_name = player_name.split()[-1].replace('.', '').replace('Jr', '').replace('III', '').replace('II', '').strip()
            if last_name and len(last_name) > 2:
                pred = pred_df[pred_df['player_name'].str.contains(last_name, case=False, na=False)]
                if len(pred) > 1:
                    first_name = player_name.split()[0]
                    temp_pred = pred[pred['player_name'].str.contains(first_name, case=False, na=False)]
                    if not temp_pred.empty:
                        pred = temp_pred
        
        if pred.empty:
            print(f"No prediction found for {player_name}")
            return
        
        # Check if already marked (prevent duplicates)
        if not df.empty:
            already_marked = df[(df['player_name'] == player_name) & (df['date'] == date)]
            if not already_marked.empty:
                return  # Already marked, skip
        
        pred = pred.iloc[0]
        
        # Add result
        new_result = {
            'date': date,
            'player_name': player_name,
            'recommended_minimum': pred['recommended_minimum'],
            'actual_pra': actual_pra,
            'result': result.upper(),
            'marked_at': datetime.now().isoformat()
        }
        
        df = pd.concat([df, pd.DataFrame([new_result])], ignore_index=True)
        df.to_csv(self.results_file, index=False)
        
        print(f"✓ Marked {player_name} as {result.upper()}")
        
        # Update overall record
        self.update_record()
        
    def mark_multiple(self, results_dict, date):
        """
        Mark multiple results at once
        
        Args:
            results_dict: {'Player Name': ('W', actual_pra), ...}
            date: Date of games
        """
        for player, (result, actual) in results_dict.items():
            self.mark_result(player, date, result, actual)
    
    def update_record(self):
        """Calculate and save overall record"""
        try:
            df = pd.read_csv(self.results_file)
            
            wins = len(df[df['result'] == 'W'])
            losses = len(df[df['result'] == 'L'])
            total = wins + losses
            win_pct = (wins / total * 100) if total > 0 else 0
            
            record = {
                'wins': int(wins),
                'losses': int(losses),
                'total': int(total),
                'win_percentage': round(win_pct, 1),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.record_file, 'w') as f:
                json.dump(record, f, indent=2)
            
            return record
        except FileNotFoundError:
            return {'wins': 0, 'losses': 0, 'total': 0, 'win_percentage': 0.0}
    
    def show_record(self):
        """Display current record"""
        try:
            with open(self.record_file, 'r') as f:
                record = json.load(f)
        except FileNotFoundError:
            record = {'wins': 0, 'losses': 0, 'win_percentage': 0.0}
        
        print("\n" + "=" * 60)
        print("OVERALL RECORD")
        print("=" * 60)
        print(f"Record: {record['wins']}-{record['losses']}")
        win_pct = record.get('win_percentage', 100*record['wins']/(record['wins']+record['losses']) if record['wins']+record['losses'] > 0 else 0)
        print(f"Win Rate: {win_pct:.1f}%")
        print("=" * 60)
        
        return record
    
    def show_recent_results(self, n=10):
        """Show recent results"""
        try:
            df = pd.read_csv(self.results_file)
            df = df.sort_values('marked_at', ascending=False)
            
            print(f"\nLast {min(n, len(df))} Results:")
            print("-" * 80)
            
            for _, row in df.head(n).iterrows():
                status = "✓ WIN" if row['result'] == 'W' else "✗ LOSS"
                actual = f" ({row['actual_pra']:.1f} PRA)" if pd.notna(row['actual_pra']) else ""
                print(f"{row['date']} | {row['player_name']:25} | {status}{actual}")
            
        except FileNotFoundError:
            print("No results tracked yet")
    
    def export_report(self):
        """Export detailed report"""
        try:
            df = pd.read_csv(self.results_file)
            
            report_file = f"{CSV_DIR}/results_report_{datetime.now().strftime('%Y%m%d')}.txt"
            
            with open(report_file, 'w') as f:
                f.write("=" * 60 + "\n")
                f.write("PREDICTION RESULTS REPORT\n")
                f.write("=" * 60 + "\n\n")
                
                record = self.update_record()
                f.write(f"Overall Record: {record['wins']}-{record['losses']}\n")
                f.write(f"Win Percentage: {record['win_percentage']:.1f}%\n")
                f.write(f"Total Picks: {record['total']}\n\n")
                
                # By date
                f.write("Results by Date:\n")
                f.write("-" * 60 + "\n")
                
                for date, group in df.groupby('date'):
                    wins = len(group[group['result'] == 'W'])
                    losses = len(group[group['result'] == 'L'])
                    f.write(f"\n{date}: {wins}-{losses}\n")
                    
                    for _, row in group.iterrows():
                        status = "W" if row['result'] == 'W' else "L"
                        f.write(f"  [{status}] {row['player_name']} - {row['recommended_minimum']:.1f}\n")
            
            print(f"\n✓ Report exported to {report_file}")
            return report_file
            
        except FileNotFoundError:
            print("No results to export")


def main():
    import sys
    tracker = ResultsTracker()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python results_tracker.py record                    - Show current record")
        print("  python results_tracker.py recent                    - Show recent results")
        print("  python results_tracker.py mark <player> <W/L> <date> [actual_pra]")
        print("  python results_tracker.py report                    - Export detailed report")
        print("\nExamples:")
        print("  python results_tracker.py mark 'Stephen Curry' W 2025-11-19 38.5")
        print("  python results_tracker.py mark 'LeBron James' L 2025-11-19")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'record':
        tracker.show_record()
    
    elif command == 'recent':
        tracker.show_recent_results()
    
    elif command == 'mark':
        if len(sys.argv) < 5:
            print("Usage: python results_tracker.py mark <player> <W/L> <date> [actual_pra]")
            return
        
        player = sys.argv[2]
        result = sys.argv[3]
        date = sys.argv[4]
        actual_pra = float(sys.argv[5]) if len(sys.argv) > 5 else None
        
        tracker.mark_result(player, date, result, actual_pra)
        tracker.show_record()
    
    elif command == 'report':
        tracker.export_report()
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
