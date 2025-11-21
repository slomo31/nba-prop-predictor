"""
Scrape historical game results and prop lines for real backtesting
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalDataScraper:
    def __init__(self):
        self.base_url = "https://www.basketball-reference.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_games_on_date(self, date):
        """
        Scrape all games that happened on a specific date
        
        Args:
            date: datetime object or string 'YYYY-MM-DD'
        
        Returns:
            List of game_ids
        """
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        url = f"{self.base_url}/boxscores/"
        params = {
            'month': date.month,
            'day': date.day,
            'year': date.year
        }
        
        logger.info(f"Fetching games for {date.strftime('%Y-%m-%d')}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            time.sleep(3)
            
            soup = BeautifulSoup(response.content, 'lxml')
            game_summaries = soup.find_all('div', {'class': 'game_summary'})
            
            games = []
            for game in game_summaries:
                # Get teams
                teams = game.find_all('a', href=lambda x: x and '/teams/' in x)
                if len(teams) >= 2:
                    away_team = teams[0].text
                    home_team = teams[1].text
                    
                    # Get box score link
                    box_link = game.find('a', text='Box Score')
                    if box_link:
                        game_id = box_link['href'].split('/')[-1].replace('.html', '')
                        
                        games.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'game_id': game_id,
                            'away_team': away_team,
                            'home_team': home_team
                        })
            
            logger.info(f"Found {len(games)} games")
            return games
            
        except Exception as e:
            logger.error(f"Error fetching games: {e}")
            return []
    
    def scrape_box_score(self, game_id, date):
        """
        Scrape detailed box score for a game
        
        Returns:
            DataFrame with player stats
        """
        url = f"{self.base_url}/boxscores/{game_id}.html"
        
        logger.info(f"Scraping box score: {game_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            time.sleep(3)
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find both team tables
            tables = soup.find_all('table', {'class': 'stats_table'})
            
            all_players = []
            
            for table in tables:
                # Skip if not a box score table
                if 'game-basic' not in str(table):
                    continue
                
                tbody = table.find('tbody')
                if not tbody:
                    continue
                
                rows = tbody.find_all('tr')
                
                for row in rows:
                    # Skip header rows and team totals
                    if row.find('th', {'class': 'over_header'}):
                        continue
                    if 'Team Totals' in row.text or 'Reserves' in row.text:
                        continue
                    
                    player_cell = row.find('th', {'data-stat': 'player'})
                    if not player_cell:
                        continue
                    
                    player_name = player_cell.text.strip()
                    
                    # Extract stats
                    stats = {}
                    for td in row.find_all('td'):
                        stat_name = td.get('data-stat')
                        stat_value = td.text.strip()
                        stats[stat_name] = stat_value
                    
                    # Get PTS, REB, AST
                    try:
                        pts = float(stats.get('pts', 0) or 0)
                        reb = float(stats.get('trb', 0) or 0)
                        ast = float(stats.get('ast', 0) or 0)
                        pra = pts + reb + ast
                        
                        all_players.append({
                            'date': date,
                            'game_id': game_id,
                            'player_name': player_name,
                            'pts': pts,
                            'reb': reb,
                            'ast': ast,
                            'pra': pra,
                            'mp': stats.get('mp', '0:00')
                        })
                    except (ValueError, TypeError):
                        continue
            
            return pd.DataFrame(all_players)
            
        except Exception as e:
            logger.error(f"Error scraping box score: {e}")
            return pd.DataFrame()
    
    def scrape_date_range(self, start_date, end_date):
        """
        Scrape all games in a date range
        
        Args:
            start_date: 'YYYY-MM-DD'
            end_date: 'YYYY-MM-DD'
        
        Returns:
            DataFrame with all player performances
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_results = []
        
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            
            # Get games for this date
            games = self.scrape_games_on_date(current)
            
            # Scrape each game
            for game in games:
                box_score = self.scrape_box_score(game['game_id'], date_str)
                if not box_score.empty:
                    all_results.append(box_score)
            
            current += timedelta(days=1)
            time.sleep(5)  # Be nice to the server
        
        if all_results:
            return pd.concat(all_results, ignore_index=True)
        else:
            return pd.DataFrame()


def main():
    import sys
    
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python historical_scraper.py START_DATE END_DATE")
        print("\nExample:")
        print("  python historical_scraper.py 2025-11-01 2025-11-15")
        return
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    
    scraper = HistoricalDataScraper()
    
    print(f"\n{'='*60}")
    print(f"SCRAPING HISTORICAL DATA: {start_date} to {end_date}")
    print(f"{'='*60}\n")
    
    results = scraper.scrape_date_range(start_date, end_date)
    
    if not results.empty:
        output_file = f"../data/backtest/historical_results_{start_date}_to_{end_date}.csv"
        results.to_csv(output_file, index=False)
        
        print(f"\n✓ Scraped {len(results)} player performances")
        print(f"✓ Saved to {output_file}")
        print(f"\nSample data:")
        print(results.head(10))
    else:
        print("\n✗ No data scraped")


if __name__ == "__main__":
    main()
