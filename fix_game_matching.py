with open('main.py', 'r') as f:
    content = f.read()

# Find and replace the make_predictions method with proper game filtering
import re

# Remove the old broken method
old_start = content.find('def make_predictions(self')
old_end = content.find('return pred_df', old_start) + len('return pred_df')
old_method = content[old_start:old_end]

new_method = '''def make_predictions(self, show_all=True):
        """
        Generate predictions for current props with realistic minimum lines
        Only shows players actually in today's games
        """
        logger.info("=" * 60)
        logger.info("GENERATING PREDICTIONS WITH MINIMUM LINES")
        logger.info("=" * 60)
        
        # Load trained model
        if not self.predictor.load_model():
            logger.error("No trained model found. Please train model first.")
            return None
        
        # Get latest odds - THIS TELLS US WHICH GAMES ARE HAPPENING
        logger.info("\\nLoading latest prop lines...")
        odds_df = self.odds_fetcher.get_latest_props_for_prediction()
        
        if odds_df is None or odds_df.empty:
            logger.error("No odds data available - cannot determine today's games")
            return None
        
        logger.info(f"Found {len(odds_df)} prop lines from sportsbooks")
        
        # Get unique games happening today
        games_today = odds_df[['home_team', 'away_team', 'commence_time']].drop_duplicates()
        logger.info(f"Games today: {len(games_today)}")
        
        # Get player stats
        logger.info("\\nLoading player statistics...")
        try:
            from config import PLAYER_STATS_CSV
            stats_df = pd.read_csv(PLAYER_STATS_CSV)
        except FileNotFoundError:
            logger.error("Player stats not found. Please update data first.")
            return None
        
        # Initialize minimum line calculator
        calc = MinimumLineCalculator()
        
        predictions = []
        
        # Process each game
        for _, game_row in games_today.iterrows():
            home_team = game_row['home_team']
            away_team = game_row['away_team']
            game_time = game_row['commence_time']
            
            logger.info(f"\\nProcessing: {away_team} @ {home_team}")
            
            # Get players from BOTH teams in this game
            # Match by team abbreviation
            game_players = stats_df[
                (stats_df['Team'].str.contains(home_team[:3], case=False, na=False)) |
                (stats_df['Team'].str.contains(away_team[:3], case=False, na=False))
            ].copy()
            
            # Filter to rotation players (10+ mins, 5+ games)
            game_players = game_players[
                (game_players['MP'] >= 10.0) & 
                (game_players['G'] >= 5)
            ].copy()
            
            # Sort by PRA average (stars first)
            game_players['PRA'] = game_players['PTS'] + game_players['TRB'] + game_players['AST']
            game_players = game_players.sort_values('PRA', ascending=False)
            
            # Take top 12 players per game (6 starters + 6 bench typically)
            game_players = game_players.head(12)
            
            logger.info(f"  Found {len(game_players)} rotation players for this game")
            
            # Process each player
            for _, player_row in game_players.iterrows():
                player_name = player_row['Player']
                team = player_row['Team']
                
                pts_avg = player_row.get('PTS', 0)
                reb_avg = player_row.get('TRB', 0)
                ast_avg = player_row.get('AST', 0)
                pra_avg = pts_avg + reb_avg + ast_avg
                
                # Skip very low production players
                if pra_avg < 5.0:
                    continue
                
                # Find if this player has an odds line
                player_odds = odds_df[
                    (odds_df['player_name'].str.contains(player_name.split()[0], case=False, na=False)) &
                    (odds_df['home_team'] == home_team) &
                    (odds_df['away_team'] == away_team)
                ]
                
                if not player_odds.empty:
                    main_line = player_odds.iloc[0]['line']
                    has_line = True
                else:
                    main_line = pra_avg
                    has_line = False
                
                # Calculate minimum line
                player_stats_dict = {
                    'pts_reb_ast_avg': pra_avg,
                    'last_5_avg': pra_avg,
                    'consistency': 0.85
                }
                
                min_line, confidence, reasoning = calc.calculate_realistic_minimum(
                    player_stats_dict, main_line
                )
                
                if min_line is None:
                    continue
                
                meets_threshold = confidence >= 0.90
                
                predictions.append({
                    'player_name': player_name,
                    'team': team,
                    'dk_line': main_line,
                    'has_dk_line': has_line,
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
            logger.info("\\nNo predictions generated")
            return None
        
        # Create predictions DataFrame
        pred_df = pd.DataFrame(predictions)
        
        # Remove duplicates (same player might appear twice if odds parser duplicated)
        pred_df = pred_df.drop_duplicates(subset=['player_name', 'game'], keep='first')
        
        # Sort by game, then by season average
        pred_df = pred_df.sort_values(
            ['game', 'season_avg'], 
            ascending=[True, False]
        )
        
        # Save predictions
        pred_df.to_csv(PREDICTIONS_CSV, index=False)
        
        high_conf_count = len(pred_df[pred_df['meets_threshold']])
        
        logger.info(f"\\n✓ Generated {len(pred_df)} total predictions")
        logger.info(f"   - {high_conf_count} meet 90%+ threshold")
        logger.info(f"   - {len(games_today)} games covered")
        logger.info(f"Saved to {PREDICTIONS_CSV}")
        
        return pred_df'''

content = content[:old_start] + new_method + content[old_end:]

with open('main.py', 'w') as f:
    f.write(content)

print("✓ Fixed game matching logic")
