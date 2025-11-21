"""
Module for scraping NBA player statistics from Basketball Reference
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from datetime import datetime
import logging
from config import (
    NBA_STATS_URL, PLAYER_STATS_CSV, GAME_RESULTS_CSV, 
    UPDATE_CHECKPOINT_FILE, CURRENT_SEASON
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlayerStatsScraper:
    def __init__(self):
        self.base_url = NBA_STATS_URL
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.checkpoint_data = self.load_checkpoint()
        
    def load_checkpoint(self):
        """Load last update checkpoint to avoid re-scraping"""
        try:
            with open(UPDATE_CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'last_update': None, 'last_game_date': None}
    
    def save_checkpoint(self, checkpoint_data):
        """Save checkpoint data"""
        with open(UPDATE_CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint_data, f)
    
    def scrape_player_season_stats(self, season='2026'):
        """Scrape per-game stats for all players in a season"""
        url = f"{self.base_url}/leagues/NBA_{season}_per_game.html"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            time.sleep(3)  # Rate limiting
            
            soup = BeautifulSoup(response.content, 'lxml')
            table = soup.find('table', {'id': 'per_game_stats'})
            
            if not table:
                logger.error("Could not find stats table")
                return None
            
            # Parse table
            df = pd.read_html(str(table))[0]
            
            # Clean up data
            df = df[df['Player'] != 'Player']  # Remove header rows
            df = df[df['Rk'] != 'Rk']
            
            # Convert numeric columns
            numeric_columns = ['Age', 'G', 'GS', 'MP', 'FG', 'FGA', 'FG%', '3P', '3PA', 
                             '3P%', '2P', '2PA', '2P%', 'eFG%', 'FT', 'FTA', 'FT%',
                             'ORB', 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Add season
            df['season'] = season
            df['scraped_at'] = datetime.now().isoformat()
            
            logger.info(f"Scraped stats for {len(df)} player-team combinations")
            return df
            
        except Exception as e:
            logger.error(f"Error scraping season stats: {e}")
            return None
    
    def scrape_player_game_log(self, player_name, season='2026'):
        """Scrape individual game logs for a specific player"""
        # Convert player name to Basketball Reference format
        # This is simplified - would need more robust name matching
        player_slug = player_name.lower().replace(' ', '-')
        
        # This would need the actual player ID from Basketball Reference
        # For now, returning None as this requires more complex implementation
        logger.warning("Game log scraping requires player ID mapping - not implemented yet")
        return None
    
    def scrape_team_schedules(self, season='2026'):
        """Scrape team schedules to get game results"""
        url = f"{self.base_url}/leagues/NBA_{season}_games.html"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            time.sleep(3)
            
            soup = BeautifulSoup(response.content, 'lxml')
            table = soup.find('table', {'id': 'schedule'})
            
            if not table:
                logger.error("Could not find schedule table")
                return None
            
            df = pd.read_html(str(table))[0]
            df = df[df['Date'] != 'Date']  # Remove header rows
            
            df['scraped_at'] = datetime.now().isoformat()
            
            logger.info(f"Scraped {len(df)} games from schedule")
            return df
            
        except Exception as e:
            logger.error(f"Error scraping schedule: {e}")
            return None
    
    def calculate_rolling_averages(self, df, player_col='Player', windows=[5, 10]):
        """Calculate rolling averages for key stats"""
        if df is None or df.empty:
            return df
        
        df = df.sort_values(['Player', 'Date'])
        
        for window in windows:
            for stat in ['PTS', 'TRB', 'AST']:
                if stat in df.columns:
                    col_name = f"{stat.lower()}_last_{window}"
                    df[col_name] = df.groupby(player_col)[stat].transform(
                        lambda x: x.rolling(window, min_periods=1).mean()
                    )
        
        return df
    
    def update_player_stats(self):
        """Update player stats incrementally"""
        logger.info("Updating player statistics...")
        
        # Check if we have existing data
        try:
            existing_df = pd.read_csv(PLAYER_STATS_CSV)
            logger.info(f"Found existing stats with {len(existing_df)} records")
        except FileNotFoundError:
            existing_df = None
            logger.info("No existing stats found, performing full scrape")
        
        # Scrape current season stats
        new_df = self.scrape_player_season_stats(season=CURRENT_SEASON)
        
        if new_df is None:
            logger.error("Failed to scrape new stats")
            return False
        
        # Merge with existing data if available
        if existing_df is not None:
            # Combine and deduplicate
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(
                subset=['Player', 'Team', 'season'], 
                keep='last'
            )
        else:
            combined_df = new_df
        
        # Save updated stats
        combined_df.to_csv(PLAYER_STATS_CSV, index=False)
        logger.info(f"Saved {len(combined_df)} player stat records")
        
        # Update checkpoint
        self.save_checkpoint({
            'last_update': datetime.now().isoformat(),
            'records_count': len(combined_df)
        })
        
        return True
    
    def get_player_stats(self, player_name):
        """Get stats for a specific player"""
        try:
            df = pd.read_csv(PLAYER_STATS_CSV)
            player_data = df[df['Player'].str.contains(player_name, case=False, na=False)]
            
            if player_data.empty:
                logger.warning(f"No stats found for {player_name}")
                return None
            
            # Return most recent stats
            return player_data.iloc[0].to_dict()
            
        except Exception as e:
            logger.error(f"Error getting player stats: {e}")
            return None
    
    def enrich_with_advanced_stats(self, df):
        """Calculate additional advanced statistics"""
        if 'PTS' in df.columns and 'TRB' in df.columns and 'AST' in df.columns:
            df['pts_reb_ast_avg'] = df['PTS'] + df['TRB'] + df['AST']
        
        if 'MP' in df.columns and df['MP'].notna().any():
            # Usage rate approximation (simplified)
            df['usage_rate'] = (df['FGA'] + 0.44 * df['FTA'] + df['TOV']) / df['MP']
            df['usage_rate'] = df['usage_rate'].fillna(0)
        
        if 'FG' in df.columns and 'FGA' in df.columns and '3P' in df.columns:
            # True shooting percentage
            df['true_shooting_pct'] = df['PTS'] / (2 * (df['FGA'] + 0.44 * df['FTA']))
            df['true_shooting_pct'] = df['true_shooting_pct'].fillna(0)
        
        return df


if __name__ == "__main__":
    scraper = PlayerStatsScraper()
    
    print("Starting player stats update...")
    success = scraper.update_player_stats()
    
    if success:
        print("\nStats update completed successfully!")
        
        # Load and show sample
        df = pd.read_csv(PLAYER_STATS_CSV)
        print(f"\nTotal player records: {len(df)}")
        print("\nSample of data:")
        print(df.head(10)[['Player', 'Tm', 'G', 'MP', 'PTS', 'TRB', 'AST']])
