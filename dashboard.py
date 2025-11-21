"""
Interactive web dashboard for NBA Prop Predictor
"""

from flask import Flask, render_template, jsonify
import pandas as pd
import json
from datetime import datetime
import os
from config import PREDICTIONS_CSV, CSV_DIR
from results_tracker import ResultsTracker

app = Flask(__name__)

RECORD_FILE = os.path.join(CSV_DIR, 'overall_record.json')


def get_record():
    """Get overall record"""
    try:
        with open(RECORD_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'wins': 0, 'losses': 0, 'win_percentage': 0.0, 'total': 0}


def get_predictions():
    """Get current predictions grouped by game"""
    try:
        df = pd.read_csv(PREDICTIONS_CSV)
        
        # Group by game
        games = []
        for game in df['game'].unique():
            game_picks = df[df['game'] == game]
            
            picks = []
            for _, row in game_picks.iterrows():
                picks.append({
                    'player_name': row['player_name'],
                    'team': row.get('team', 'Unknown'),
                    'dk_line': float(row['dk_line']),
                    'has_dk_line': bool(row.get('has_dk_line', True)),
                    'meets_threshold': bool(row.get('meets_threshold', False)),
                    'recommended_minimum': float(row['recommended_minimum']),
                    'season_avg': float(row['season_avg']),
                    'pts_avg': float(row['pts_avg']),
                    'reb_avg': float(row['reb_avg']),
                    'ast_avg': float(row['ast_avg']),
                    'confidence': float(row['confidence']),
                    'reasoning': row['reasoning'],
                    'cushion': float(row['season_avg'] - row['recommended_minimum']),
                    'below_dk': float(row['dk_line'] - row['recommended_minimum'])
                })
            
            # Parse game time
            game_time = game_picks.iloc[0]['game_time']
            try:
                dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%I:%M %p ET')
                formatted_date = dt.strftime('%b %d, %Y')
            except:
                formatted_time = 'TBD'
                formatted_date = 'TBD'
            
            games.append({
                'game': game,
                'time': formatted_time,
                'date': formatted_date,
                'picks': picks,
                'pick_count': len(picks),
                'avg_confidence': sum(p['confidence'] for p in picks) / len(picks)
            })
        
        return sorted(games, key=lambda x: x['date'])
        
    except FileNotFoundError:
        return []


@app.route('/')
def index():
    """Main dashboard page"""
    record = get_record()
    games = get_predictions()
    
    total_picks = sum(g['pick_count'] for g in games)
    avg_confidence = sum(g['avg_confidence'] * g['pick_count'] for g in games) / total_picks if total_picks > 0 else 0
    
    return render_template('dashboard.html', 
                         record=record,
                         games=games,
                         total_picks=total_picks,
                         avg_confidence=avg_confidence)


@app.route('/api/refresh')
def refresh():
    """API endpoint to refresh data"""
    record = get_record()
    games = get_predictions()
    total_picks = sum(g['pick_count'] for g in games)
    
    return jsonify({
        'record': record,
        'games': games,
        'total_picks': total_picks
    })


if __name__ == '__main__':
    # Check if templates directory exists
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, port=5000)

# Add this at the bottom for Render deployment
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
