from nhlpy import NHLClient
import json

def test_depth():
    client = NHLClient()
    
    # 1. Inspect top-level client to find 'standings' or similar
    print("Client attributes:", [a for a in dir(client) if not a.startswith('_')])
    
    # 2. Test 'match_up' endpoint
    print("\n--- Testing Match Up ---")
    try:
        # Inspect arguments
        import inspect
        print(f"Match Up Args: {inspect.signature(client.game_center.match_up)}")
        
        # Try calling with positional if names unclear, or help introspection
    except Exception as e:
        print(f"Introspection failed: {e}")

    # 3. Test standings
    print("\n--- Testing Standings ---")
    try:
        # Trying league_standings
        std = client.standings.league_standings()
        print("Standings fetched.")
        print(f"Standings keys: {std.keys() if std else 'None'}")
        
        if std and 'standings' in std:
             print(f"Number of teams: {len(std['standings'])}")
             print(f"First team sample: {std['standings'][0]}")
    except Exception as e:
        print(f"Standings error: {e}")

if __name__ == "__main__":
    test_depth()
