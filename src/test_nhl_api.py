try:
    import nhlpy
    from nhlpy import NHLClient
    print(f"Library file: {nhlpy.__file__}")
except ImportError as e:
    print(f"ImportError details: {e}")
    exit(1)

import json
from datetime import datetime, timedelta

def test_api():
    client = NHLClient()
    
    # INSPECT LIBRARY METHODS
    print("\n[INSPECTION]")
    try:
        print(f"Methods in client.schedule: {[m for m in dir(client.schedule) if not m.startswith('_')]}")
        print(f"Methods in client.game_center: {[m for m in dir(client.game_center) if not m.startswith('_')]}")
    except Exception as e:
        print(f"Inspection failed: {e}")

    # 1. Get Schedule
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"\n--- Fetching Schedule for {yesterday} ---")
    
    schedule = None
    
    # Attempt 1: daily_schedule (found in inspection)
    try:
         print("Using client.schedule.daily_schedule...")
         schedule = client.schedule.daily_schedule(date=yesterday)
    except Exception as e:
         print(f"daily_schedule failed: {e}")
    
    if not schedule:
        print("Failed to get schedule.")
        return

    # If we got here, we have schedule
    try:
        print(f"Schedule keys: {schedule.keys()}")
        games = []
        # Structure often has 'games' directly for daily
        if 'games' in schedule:
            games = schedule['games']
        elif 'gameWeek' in schedule:
            games = schedule.get('gameWeek', [{}])[0].get('games', [])
        
        print(f"Found {len(games)} games.")
        
        if games:
            game = games[0]
            game_id = game.get('id')
            if not game_id:
                # Some APIs use 'gameId'
                game_id = game.get('gameId')
            
            print(f"Testing Game ID: {game_id} ({game.get('homeTeam', {}).get('abbrev', '?')} vs {game.get('awayTeam', {}).get('abbrev', '?')})")
            
            # 3. Get Boxscore (Stats)
            if game_id:
                print("\n--- Fetching Boxscore ---")
                try:
                    boxscore = client.game_center.boxscore(game_id=game_id)
                    print("Boxscore fetched successfully.")
                    print(f"Boxscore keys: {boxscore.keys()}")
                    # Check for player stats
                    if 'playerByGameStats' in boxscore or 'boxscore' in boxscore:
                         print("Detailed stats found!")
                except Exception as e:
                    print(f"Boxscore fetch failed: {e}")

    except Exception as e:
        print(f"Error parsing schedule: {e}")
        print(f"Raw schedule keys: {schedule.keys() if isinstance(schedule, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"Error parsing schedule: {e}")
        print(f"Raw schedule keys: {schedule.keys() if isinstance(schedule, dict) else 'Not a dict'}")

if __name__ == "__main__":
    test_api()
