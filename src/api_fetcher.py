from nhlpy import NHLClient
from datetime import datetime, timedelta
import time

class NHLAPIFetcher:
    def __init__(self):
        self.client = NHLClient()

    def get_games_for_date(self, date_str=None):
        """
        Fetches games for a specific date (YYYY-MM-DD).
        If no date provided, uses today.
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        print(f"Fetching games for {date_str}...")
        try:
            schedule = self.client.schedule.daily_schedule(date=date_str)
            games = []
            
            # Flexible parsing based on API response structure
            if 'games' in schedule:
                games = schedule['games']
            elif 'gameWeek' in schedule:
                # Sometimes it returns a week structure even for daily call
                week_data = schedule.get('gameWeek', [{}])
                if week_data:
                    games = week_data[0].get('games', [])
            
            # Simple validation
            valid_games = []
            for g in games:
                # Ensure it has basic info
                if 'id' in g or 'gameId' in g:
                    valid_games.append(g)
            
            return valid_games
            
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return []

    def get_game_details(self, game_id):
        """
        Fetches detailed boxscore/stats for a game. 
        For future games, boxscore is empty, so we need 'match_up' and 'standings'.
        """
        data = {}
        try:
            # 1. Boxscore (good for live/finished)
            boxscore = self.client.game_center.boxscore(game_id=game_id)
            data['boxscore'] = boxscore
            
            # 2. Matchup (Pre-game H2H and season context)
            try:
                # Based on inspection: match_up(game_id=str)
                matchup = self.client.game_center.match_up(game_id=str(game_id))
                data['matchup'] = matchup
            except Exception as e:
                print(f"Matchup fetch error: {e}")

        except Exception as e:
            print(f"Error fetching game details for {game_id}: {e}")
            return None
        return data

    def get_standings(self):
        """Fetches current standings to get team form/stats."""
        try:
            return self.client.standings.league_standings()
        except:
            return None

if __name__ == "__main__":
    # Test
    fetcher = NHLAPIFetcher()
    # Test with yesterday's date to ensure we get some completed games
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    games = fetcher.get_games_for_date(yesterday)
    print(f"Found {len(games)} games for {yesterday}")
    if games:
        g_id = games[0].get('id') or games[0].get('gameId')
        print(f"Details for game {g_id}:")
        details = fetcher.get_game_details(g_id)
        if details:
            print("  - details fetched successfully")
