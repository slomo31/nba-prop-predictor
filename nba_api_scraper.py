"""
Scrape actual game results from NBA.com API (more reliable than Basketball Reference)
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NBAApiScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com'
        }
    
    def get_games_for_date(self, date_str):
        """Get all games for a specific date from NBA.com"""
        # NBA.com scoreboard API
        url = f"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        
        # For past dates, use the date-specific endpoint
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%Y%m%d')
        
        url = f"https://stats.nba.com/stats/scoreboardv2"
        params = {
            'DayOffset': 0,
            'GameDate': date_obj.strftime('%m/%d/%Y'),
            'LeagueID': '00'
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'resultSets' in data:
                games = data['resultSets'][0]['rowSet']
                game_ids = [game[2] for game in games]  # Game IDs
                logger.info(f"Found {len(game_ids)} games for {date_str}")
                return game_ids
            
        except Exception as e:
            logger.error(f"Error fetching games: {e}")
        
        return []
    
    def get_box_score(self, game_id):
        """Get box score for a specific game"""
        url = "https://stats.nba.com/stats/boxscoretraditionalv2"
        params = {
            'GameID': game_id,
            'StartPeriod': 0,
            'EndPeriod': 10,
            'StartRange': 0,
            'EndRange': 28800,
            'RangeType': 0
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            player_stats = []
            
            # Get player stats from resultSets
            if 'resultSets' in data:
                for result_set in data['resultSets']:
                    if result_set['name'] == 'PlayerStats':
                        headers = result_set['headers']
                        rows = result_set['rowSet']
                        
                        pts_idx = headers.index('PTS')
                        reb_idx = headers.index('REB')
                        ast_idx = headers.index('AST')
                        name_idx = headers.index('PLAYER_NAME')
                        min_idx = headers.index('MIN')
                        
                        for row in rows:
                            if row[min_idx] and row[min_idx] != '0:00':
                                player_stats.append({
                                    'player_name': row[name_idx],
                                    'pts': float(row[pts_idx] or 0),
                                    'reb': float(row[reb_idx] or 0),
                                    'ast': float(row[ast_idx] or 0),
                                    'pra': float(row[pts_idx] or 0) + float(row[reb_idx] or 0) + float(row[ast_idx] or 0),
                                    'mp': row[min_idx]
                                })
            
            return player_stats
            
        except Exception as e:
            logger.error(f"Error fetching box score for {game_id}: {e}")
            return []


def test_scraper():
    """Test the NBA API scraper"""
    scraper = NBAApiScraper()
    
    # Test with Nov 20
    date = '2025-11-20'
    print(f"\nTesting NBA API scraper for {date}...")
    
    game_ids = scraper.get_games_for_date(date)
    
    if game_ids:
        print(f"Found {len(game_ids)} games")
        print("\nGetting box score for first game...")
        
        stats = scraper.get_box_score(game_ids[0])
        if stats:
            df = pd.DataFrame(stats)
            print(f"\nScraped {len(df)} players")
            print("\nSample:")
            print(df.head(10))
        else:
            print("No stats retrieved")
    else:
        print("No games found - API might be down or date format issue")


if __name__ == "__main__":
    test_scraper()
