"""
Module for fetching NBA player prop odds from The Odds API
"""

import requests
import pandas as pd
import json
from datetime import datetime
import time
from config import ODDS_API_KEY, ODDS_API_BASE_URL, ODDS_DATA_CSV
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OddsAPIFetcher:
    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.base_url = ODDS_API_BASE_URL
        self.sport = "basketball_nba"
        
    def get_upcoming_games(self):
        """Fetch upcoming NBA games"""
        url = f"{self.base_url}/sports/{self.sport}/events"
        params = {
            'apiKey': self.api_key,
            'dateFormat': 'iso'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            games = response.json()
            logger.info(f"Fetched {len(games)} upcoming games")
            return games
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching games: {e}")
            return []
    
    def get_player_props(self, event_id, markets='player_points_rebounds_assists'):
        """
        Fetch player prop odds for specific event
        Markets: player_points_rebounds_assists (combined PRA)
        """
        url = f"{self.base_url}/sports/{self.sport}/events/{event_id}/odds"
        
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': markets,
            'oddsFormat': 'american',
            'dateFormat': 'iso'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched player props for event {event_id}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching player props: {e}")
            return None
    
    def parse_player_props_to_dataframe(self, props_data):
        """Parse player props API response into structured dataframe"""
        records = []
        
        for event in props_data:
            event_id = event.get('id')
            home_team = event.get('home_team')
            away_team = event.get('away_team')
            commence_time = event.get('commence_time')
            
            bookmakers = event.get('bookmakers', [])
            
            for bookmaker in bookmakers:
                bookmaker_name = bookmaker.get('key')
                markets = bookmaker.get('markets', [])
                
                for market in markets:
                    market_key = market.get('key')
                    
                    for outcome in market.get('outcomes', []):
                        player_name = outcome.get('description', outcome.get('name', ''))
                        point_line = outcome.get('point')
                        price = outcome.get('price')
                        
                        if point_line is not None:
                            records.append({
                                'event_id': event_id,
                                'home_team': home_team,
                                'away_team': away_team,
                                'commence_time': commence_time,
                                'bookmaker': bookmaker_name,
                                'market': market_key,
                                'player_name': player_name,
                                'line': point_line,
                                'odds': price,
                                'fetched_at': datetime.now().isoformat()
                            })
        
        df = pd.DataFrame(records)
        return df
    
    def fetch_and_save_current_props(self):
        """Fetch current player props and save to CSV"""
        logger.info("Fetching current player props...")
        
        # First get all upcoming games
        games = self.get_upcoming_games()
        
        if not games:
            logger.warning("No upcoming games found")
            return None
        
        # Fetch props for each game
        all_props = []
        for game in games:  # Get ALL games
            event_id = game.get('id')
            props_data = self.get_player_props(event_id)
            
            if props_data:
                all_props.append(props_data)
        
        if not all_props:
            logger.warning("No props data available")
            return None
        
        # Parse all props data
        all_dfs = []
        for props_data in all_props:
            df = self.parse_player_props_to_dataframe([props_data])
            if not df.empty:
                all_dfs.append(df)
        
        if not all_dfs:
            logger.warning("No player props found")
            return None
        
        df = pd.concat(all_dfs, ignore_index=True)
        
        if df.empty:
            logger.warning("No player props found")
            return None
        
        # Filter for player_points_rebounds_assists market
        df = df[df['market'] == 'player_points_rebounds_assists']
        
        # Save to CSV (append mode to keep history)
        try:
            existing_df = pd.read_csv(ODDS_DATA_CSV)
            df = pd.concat([existing_df, df], ignore_index=True)
            df = df.drop_duplicates(subset=['event_id', 'player_name', 'line', 'fetched_at'], keep='last')
        except FileNotFoundError:
            pass
        
        df.to_csv(ODDS_DATA_CSV, index=False)
        logger.info(f"Saved {len(df)} prop lines to {ODDS_DATA_CSV}")
        
        return df
    
    def get_latest_props_for_prediction(self):
        """Get the most recent props data for making predictions"""
        try:
            df = pd.read_csv(ODDS_DATA_CSV)
            df['fetched_at'] = pd.to_datetime(df['fetched_at'])
            
            # Get most recent fetch (within last 5 minutes to handle microsecond differences)
            latest_fetch = df['fetched_at'].max()
            time_threshold = latest_fetch - pd.Timedelta(minutes=5)
            df_latest = df[df['fetched_at'] >= time_threshold]
            
            # Filter for player_points_rebounds_assists market only
            if 'market' in df_latest.columns:
                df_latest = df_latest[df_latest['market'] == 'player_points_rebounds_assists']
            
            # Group by player and game, take the MINIMUM line available (easiest to hit)
            df_grouped = df_latest.groupby(['player_name', 'home_team', 'away_team']).agg({
                'line': 'min',  # Use minimum line (most favorable)
                'odds': 'first',
                'commence_time': 'first'
            }).reset_index()
            
            logger.info(f"Processed {len(df_grouped)} unique player props for prediction")
            
            return df_grouped
            
        except FileNotFoundError:
            logger.error("No odds data file found. Run fetch first.")
            return None


if __name__ == "__main__":
    fetcher = OddsAPIFetcher()
    
    # Test API connection
    print("Testing API connection...")
    games = fetcher.get_upcoming_games()
    print(f"Found {len(games)} upcoming games")
    
    # Fetch current props
    print("\nFetching player props...")
    props_df = fetcher.fetch_and_save_current_props()
    
    if props_df is not None:
        print(f"\nSample of fetched props:")
        print(props_df.head(10))
