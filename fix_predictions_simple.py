with open('main.py', 'r') as f:
    content = f.read()

import re

# Find and replace make_predictions with the SIMPLE correct approach
old_start = content.find('def make_predictions(self')
old_end = content.find('return pred_df', old_start) + len('return pred_df')

new_method = '''def make_predictions(self):
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
        logger.info("\\nFetching players with prop lines from Odds API...")
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
        pred_df.to_csv(PREDICTIONS_CSV, index=False)
        
        high_conf = len(pred_df[pred_df['meets_threshold']])
        games = pred_df['game'].nunique()
        
        logger.info(f"\\n✓ Generated {len(pred_df)} predictions")
        logger.info(f"   - {high_conf} high confidence (90%+)")
        logger.info(f"   - {games} games")
        logger.info(f"Saved to {PREDICTIONS_CSV}")
        
        return pred_df'''

content = content[:old_start] + new_method + content[old_end:]

with open('main.py', 'w') as f:
    f.write(content)

print("✓ Fixed to use ONLY players from Odds API")
