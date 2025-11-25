#!/usr/bin/env python3
"""
Incremental Player Consistency Backtest
- Only fetches NEW games since last run
- Saves progress after each game
- REMOVES DUPLICATES (same player, same game)
- Much faster for weekly updates
"""

import pandas as pd
from datetime import datetime
import time
import os
import warnings
warnings.filterwarnings('ignore')

from nba_api.stats.endpoints import leaguegamefinder, boxscoretraditionalv3

# Config
SEASON = '2025-26'
BUFFER = 5.0
CSV_DIR = 'data/csv'
CACHE_FILE = os.path.join(CSV_DIR, 'season_game_results.csv')
GAMES_PROCESSED_FILE = os.path.join(CSV_DIR, 'games_processed.txt')
CONSISTENCY_FILE = os.path.join(CSV_DIR, 'player_consistency.csv')


def get_processed_games():
    """Load list of already processed game IDs"""
    try:
        with open(GAMES_PROCESSED_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()


def save_processed_game(game_id):
    """Append a game ID to the processed list"""
    with open(GAMES_PROCESSED_FILE, 'a') as f:
        f.write(f"{game_id}\n")


def get_all_season_games():
    """Get all game IDs from current season"""
    print("Fetching game list from NBA API...")
    game_finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=SEASON,
        season_type_nullable='Regular Season'
    )
    games_df = game_finder.get_data_frames()[0]
    game_ids = games_df['GAME_ID'].unique()
    print(f"Found {len(game_ids)} total games this season")
    return set(game_ids)


def get_box_score(game_id):
    """Get box score for a specific game - V3 format"""
    try:
        time.sleep(0.6)
        box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
        dfs = box.get_data_frames()
        
        if len(dfs) == 0:
            return None
        
        return dfs[0]  # DataFrame 0 is player stats
        
    except Exception as e:
        print(f"  Error fetching {game_id}: {e}")
        return None


def load_existing_results():
    """Load existing player performance data"""
    try:
        df = pd.read_csv(CACHE_FILE)
        print(f"Loaded {len(df)} existing player performances (may include duplicates)")
        return df
    except FileNotFoundError:
        return pd.DataFrame()


def save_results(results_df):
    """Save player performance data"""
    results_df.to_csv(CACHE_FILE, index=False)


def load_player_averages():
    """Load player season averages"""
    try:
        df = pd.read_csv(os.path.join(CSV_DIR, 'player_stats.csv'))
        df['avg_pra'] = df['PTS'] + df['TRB'] + df['AST']
        return df.set_index('Player')['avg_pra'].to_dict()
    except Exception as e:
        print(f"Error loading averages: {e}")
        return {}


def fetch_new_games(new_game_ids):
    """Fetch box scores for new games only"""
    new_results = []
    
    print(f"\nFetching {len(new_game_ids)} NEW games...")
    print("(Previously processed games are skipped)\n")
    
    for i, game_id in enumerate(new_game_ids):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(new_game_ids)} new games... ({len(new_results)} players)")
        
        player_df = get_box_score(game_id)
        
        if player_df is None or player_df.empty:
            save_processed_game(game_id)
            continue
        
        for _, row in player_df.iterrows():
            try:
                first_name = row.get('firstName', '')
                last_name = row.get('familyName', '')
                player_name = f"{first_name} {last_name}".strip()
                
                pts = row.get('points', 0) or 0
                reb = row.get('reboundsTotal', row.get('rebounds', 0)) or 0
                ast = row.get('assists', 0) or 0
                pra = pts + reb + ast
                
                if pra > 0 and player_name:
                    new_results.append({
                        'game_id': game_id,
                        'player_name': player_name,
                        'pts': pts,
                        'reb': reb,
                        'ast': ast,
                        'pra': pra
                    })
            except Exception:
                continue
        
        save_processed_game(game_id)
    
    print(f"\n✓ Fetched {len(new_results)} player performances from {len(new_game_ids)} new games")
    return new_results


def calculate_player_records(results_df, averages):
    """Calculate win/loss record for each player"""
    
    # CRITICAL FIX: Remove duplicates (same player + same game)
    print("\nRemoving duplicate game entries...")
    original_count = len(results_df)
    results_df = results_df.drop_duplicates(subset=['game_id', 'player_name'], keep='first')
    deduped_count = len(results_df)
    print(f"  Removed {original_count - deduped_count} duplicates")
    print(f"  Clean records: {deduped_count}")
    
    player_records = {}
    
    for player_name, avg_pra in averages.items():
        recommended_min = avg_pra - BUFFER
        
        # Try exact match first
        matches = results_df[results_df['player_name'] == player_name]
        
        # If no exact match, try fuzzy
        if len(matches) == 0:
            name_parts = player_name.replace('.', '').split()
            if len(name_parts) >= 2:
                first = name_parts[0].lower()
                last = name_parts[-1].lower()
                if last in ['jr', 'iii', 'ii', 'iv'] and len(name_parts) > 2:
                    last = name_parts[-2].lower()
                
                matches = results_df[
                    results_df['player_name'].str.lower().str.contains(first, na=False) &
                    results_df['player_name'].str.lower().str.contains(last, na=False)
                ]
        
        if len(matches) == 0:
            continue
        
        wins = sum(matches['pra'] >= recommended_min)
        losses = sum(matches['pra'] < recommended_min)
        
        if wins + losses >= 3:  # Minimum 3 games
            win_pct = 100 * wins / (wins + losses)
            player_records[player_name] = {
                'wins': wins,
                'losses': losses,
                'win_pct': win_pct,
                'games': wins + losses,
                'avg_pra': avg_pra,
                'recommended_min': recommended_min
            }
    
    return player_records


def run_incremental_backtest():
    """Run incremental backtest - only fetches new games"""
    
    print("=" * 70)
    print("INCREMENTAL PLAYER CONSISTENCY UPDATE")
    print(f"Using {BUFFER}-point buffer strategy")
    print("=" * 70)
    
    # Get all games this season
    all_games = get_all_season_games()
    
    # Get already processed games
    processed_games = get_processed_games()
    print(f"Already processed: {len(processed_games)} games")
    
    # Find new games
    new_games = all_games - processed_games
    print(f"New games to fetch: {len(new_games)}")
    
    # Load existing data
    existing_df = load_existing_results()
    
    if len(new_games) == 0:
        print("\n✓ No new games to process!")
        print("Using existing data to recalculate consistency...")
        results_df = existing_df
    else:
        # Fetch new games
        new_results = fetch_new_games(list(new_games))
        
        # Combine with existing
        if len(new_results) > 0:
            new_df = pd.DataFrame(new_results)
            if not existing_df.empty:
                results_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                results_df = new_df
            
            # Save combined results (still may have duplicates from previous runs)
            save_results(results_df)
            print(f"✓ Total: {len(results_df)} player performances saved (may include duplicates)")
        else:
            results_df = existing_df
    
    if results_df.empty:
        print("No game data available!")
        return
    
    # Load averages and calculate records (deduplication happens here)
    averages = load_player_averages()
    print(f"\nCalculating consistency for {len(averages)} players...")
    
    player_records = calculate_player_records(results_df, averages)
    
    # Sort by win %
    sorted_players = sorted(
        player_records.items(), 
        key=lambda x: (-x[1]['win_pct'], -x[1]['games'])
    )
    
    # Display summary
    reliable = len([p for p, r in sorted_players if r['win_pct'] >= 80])
    moderate = len([p for p, r in sorted_players if 60 <= r['win_pct'] < 80])
    avoid = len([p for p, r in sorted_players if r['win_pct'] < 60])
    
    print(f"\n" + "=" * 70)
    print(f"RESULTS: {reliable} reliable (80%+), {moderate} moderate (60-79%), {avoid} avoid (<60%)")
    print("=" * 70)
    
    # Show top 10 reliable
    print("\n🏆 TOP 10 MOST RELIABLE:")
    for i, (player, record) in enumerate(sorted_players[:10]):
        print(f"  {i+1}. {player}: {record['wins']}-{record['losses']} ({record['win_pct']:.1f}%)")
    
    # Show avoid list
    print("\n❌ PLAYERS TO AVOID:")
    for player, record in sorted_players:
        if record['win_pct'] < 60:
            print(f"  {player}: {record['wins']}-{record['losses']} ({record['win_pct']:.1f}%)")
    
    # Save to CSV
    records_list = [{
        'player_name': p,
        'wins': r['wins'],
        'losses': r['losses'],
        'win_pct': round(r['win_pct'], 1),
        'games': r['games'],
        'avg_pra': round(r['avg_pra'], 1),
        'recommended_min': round(r['recommended_min'], 1),
        'tier': '🏆 RELIABLE' if r['win_pct'] >= 80 else ('⚠️ MODERATE' if r['win_pct'] >= 60 else '❌ AVOID')
    } for p, r in sorted_players]
    
    pd.DataFrame(records_list).to_csv(CONSISTENCY_FILE, index=False)
    print(f"\n✓ Saved {len(records_list)} players to {CONSISTENCY_FILE}")
    
    total_games = len(get_processed_games())
    print(f"✓ Total games in database: {total_games}")


def run_full_reset():
    """Clear cache and re-fetch everything (use sparingly)"""
    print("⚠️  FULL RESET - This will re-fetch ALL games")
    
    # Clear processed games list
    if os.path.exists(GAMES_PROCESSED_FILE):
        os.remove(GAMES_PROCESSED_FILE)
    
    # Clear cached results
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    
    print("✓ Cache cleared. Running full backtest...")
    run_incremental_backtest()


if __name__ == "__main__":
    import sys
    
    if '--reset' in sys.argv:
        run_full_reset()
    else:
        run_incremental_backtest()
