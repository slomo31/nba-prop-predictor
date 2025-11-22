"""
Scrape actual game results - FIXED VERSION using table IDs
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import logging
from config import CSV_DIR, PREDICTIONS_CSV
from results_tracker import ResultsTracker
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GAME_RESULTS_CSV = os.path.join(CSV_DIR, 'game_results.csv')


class GameResultsScraper:
    def __init__(self):
        self.base_url = "https://www.basketball-reference.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.tracker = ResultsTracker()
    
    def scrape_games_for_date(self, date):
        """Scrape box scores for all games on a specific date"""
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        url = f"{self.base_url}/boxscores/?month={date.month}&day={date.day}&year={date.year}"
        
        logger.info(f"Scraping games for {date.strftime('%Y-%m-%d')}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            time.sleep(3)
            
            soup = BeautifulSoup(response.content, 'lxml')
            game_summaries = soup.find_all('div', {'class': 'game_summary'})
            
            if not game_summaries:
                logger.warning(f"No games found for {date.strftime('%Y-%m-%d')}")
                return []
            
            all_player_stats = []
            
            for game in game_summaries:
                box_score_link = game.find('a', string='Box Score')
                if not box_score_link:
                    continue
                
                box_score_url = self.base_url + box_score_link['href']
                player_stats = self.scrape_box_score(box_score_url, date)
                if player_stats:
                    all_player_stats.extend(player_stats)
                
                time.sleep(3)
            
            logger.info(f"Scraped {len(all_player_stats)} player performances")
            self.save_game_results(all_player_stats)
            
            return all_player_stats
            
        except Exception as e:
            logger.error(f"Error scraping games: {e}")
            return []
    
    def scrape_box_score(self, url, date):
        """Scrape box score using specific table IDs"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            player_stats = []
            
            # Basketball Reference uses specific IDs for basic box scores
            # box-TEAMABBR-game-basic for each team
            # Find all tables with IDs ending in '-game-basic'
            basic_tables = soup.find_all('table', id=lambda x: x and x.endswith('-game-basic'))
            
            for table in basic_tables:
                df = pd.read_html(str(table))[0]
                
                # Handle multi-level columns
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(0)
                
                # Get player column (first column)
                player_col = df.columns[0]
                
                for _, row in df.iterrows():
                    try:
                        player_name = str(row[player_col])
                        
                        # Skip headers, totals, reserves
                        skip_terms = ['Player', 'Reserves', 'Team Totals', 'Starters']
                        if any(term in player_name for term in skip_terms):
                            continue
                        
                        if pd.isna(player_name) or player_name == '':
                            continue
                        
                        # Get stats
                        pts = float(row.get('PTS', 0) or 0)
                        reb = float(row.get('TRB', 0) or 0)
                        ast = float(row.get('AST', 0) or 0)
                        pra = pts + reb + ast
                        mp = str(row.get('MP', '0:00'))
                        
                        # Skip DNP
                        if 'Did Not' in mp or 'Not With Team' in mp:
                            continue
                        
                        # Skip 0 minutes
                        if mp in ['0:00', '0', 'NaN'] or pd.isna(mp):
                            continue
                        
                        player_stats.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'player_name': player_name,
                            'pts': pts,
                            'reb': reb,
                            'ast': ast,
                            'pra': pra,
                            'mp': mp
                        })
                    except (ValueError, TypeError, KeyError):
                        continue
            
            return player_stats
            
        except Exception as e:
            logger.error(f"Error scraping box score {url}: {e}")
            return []
    
    def save_game_results(self, results):
        """Save game results to CSV"""
        try:
            existing_df = pd.read_csv(GAME_RESULTS_CSV)
        except FileNotFoundError:
            existing_df = pd.DataFrame()
        
        new_df = pd.DataFrame(results)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['date', 'player_name'], keep='last')
        combined_df.to_csv(GAME_RESULTS_CSV, index=False)
        logger.info(f"Saved {len(results)} game results to {GAME_RESULTS_CSV}")
    
    def auto_mark_predictions(self, date):
        """Automatically compare predictions with actual results"""
        logger.info(f"Auto-marking predictions for {date}")
        
        try:
            pred_df = pd.read_csv(PREDICTIONS_CSV)
        except FileNotFoundError:
            logger.error("No predictions file found")
            return
        
        # Try dated file first
        dated_file = PREDICTIONS_CSV.replace('.csv', f'_{date}.csv')
        if os.path.exists(dated_file):
            pred_df = pd.read_csv(dated_file)
            logger.info(f"Using dated predictions: {dated_file}")
        
        try:
            results_df = pd.read_csv(GAME_RESULTS_CSV)
            results_df = results_df[results_df['date'] == date]
        except FileNotFoundError:
            logger.error("No game results found")
            return
        
        if results_df.empty:
            logger.warning(f"No results found for {date}")
            return
        
        marked_count = 0
        
        for _, pred in pred_df.iterrows():
            player_name = pred['player_name']
            recommended_min = pred['recommended_minimum']
            
            # Match player - IMPROVED MATCHING LOGIC
            # Normalize names (remove periods, extra spaces)
            pred_name_norm = player_name.replace('.', '').strip()
            
            # Try exact match first
            result = results_df[results_df['player_name'].str.replace('.', '').str.strip().str.lower() == pred_name_norm.lower()]
            
            # If no exact match, try last name match (more specific than first name)
            if result.empty:
                last_name = player_name.split()[-1].replace('.', '').replace('Jr', '').replace('III', '').replace('II', '').strip()
                if last_name and len(last_name) > 2:  # Avoid matching on "Jr"
                    result = results_df[results_df['player_name'].str.contains(last_name, case=False, na=False)]
                    
                    # If multiple matches, try to match first name too
                    if len(result) > 1:
                        first_name = player_name.split()[0]
                        temp_result = result[result['player_name'].str.contains(first_name, case=False, na=False)]
                        if not temp_result.empty:
                            result = temp_result
            
            if result.empty:
                logger.info(f"No prediction found for {player_name} - skipping")
                continue
            
            if len(result) > 1:
                logger.warning(f"Multiple matches for {player_name}: {result['player_name'].tolist()} - using first")
            
            result = result.iloc[0]
            actual_pra = result['pra']
            
            # Skip DNP (voided by DK)
            if actual_pra == 0.0 or pd.isna(actual_pra):
                logger.info(f"Skipping {player_name} - DNP/Injury (0.0 PRA - voided)")
                continue
            
            # Win or loss
            outcome = 'W' if actual_pra >= recommended_min else 'L'
            self.tracker.mark_result(player_name, date, outcome, actual_pra)
            marked_count += 1
            
            logger.info(f"{player_name}: {outcome} ({actual_pra:.1f} vs {recommended_min:.1f})")
        
        logger.info(f"\n✓ Auto-marked {marked_count} predictions")
        self.tracker.show_record()
    def process_yesterday(self):
        """Process yesterday's games"""
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')
        
        logger.info("=" * 60)
        logger.info(f"PROCESSING YESTERDAY'S GAMES ({date_str})")
        logger.info("=" * 60)
        
        results = self.scrape_games_for_date(yesterday)
        
        if not results:
            logger.warning("No game results found")
            return
        
        self.auto_mark_predictions(date_str)


def main():
    import sys
    scraper = GameResultsScraper()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python game_results_scraper.py yesterday")
        print("  python game_results_scraper.py date YYYY-MM-DD")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'yesterday':
        scraper.process_yesterday()
    elif command == 'date':
        if len(sys.argv) < 3:
            print("Usage: python game_results_scraper.py date YYYY-MM-DD")
            return
        
        date_str = sys.argv[2]
        date = datetime.strptime(date_str, '%Y-%m-%d')
        scraper.scrape_games_for_date(date)
        scraper.auto_mark_predictions(date_str)


if __name__ == "__main__":
    main()
