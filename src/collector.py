import time
import random
from data_fetcher import FlashscoreParser
from storage_json import StorageJson

def run_collector():
    print("=== NHL Data Collector Started ===")
    
    # Initialize components
    storage = StorageJson(filepath="data/nhl_data.json")
    parser = FlashscoreParser(headless=True)
    
    try:
        # 1. Get list of all finished matches from the results page
        print("\n--- Step 1: Fetching list of finished matches ---")
        finished_matches = parser.get_finished_matches()
        print(f"Found {len(finished_matches)} finished matches on the results page.")
        
        # 2. Filter out matches we already have
        new_matches = []
        for match in finished_matches:
            # Flashscore IDs usually look like 'g_1_E588Co9j' -> key is 'E588Co9j'
            # Or we can just use the full ID if consistent. 
            # Let's ensure we use the ID from the parser.
            match_id = match.get('id')
            
            # Filter out matches without scores (future matches might leak in)
            has_score = match.get('home_score') is not None and match.get('away_score') is not None
            if not has_score:
                continue

            if match_id and not storage.match_exists(match_id):
                new_matches.append(match)
        
        print(f"New matches to process: {len(new_matches)}")
        print(f"Matches already in DB: {len(finished_matches) - len(new_matches)}")
        
        if not new_matches:
            print("No new matches to collect. Exiting.")
            return

        # 3. Process new matches
        print("\n--- Step 2: Fetching details for new matches ---")
        count = 0
        
        # Open driver for detailed fetching (get_finished_matches closes it)
        parser.start_driver()
        
        for match in new_matches:
            count += 1
            match_url = match.get('url')
            match_id = match.get('id')
            
            # Get full details first to populate start_time
            print(f"\nProcessing {count}/{len(new_matches)}: {match['home']} vs {match['away']}...")
            
            if not match_url:
                print(f"Skipping match {match_id}: No URL found")
                continue
                
            try:
                # Retry logic for fetching details
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Get full details
                        details = parser.get_match_details(match_url)
                        break # Success
                    except Exception as details_error:
                        print(f"  [Attempt {attempt+1}/{max_retries}] Error fetching details: {details_error}")
                        # If connection error, restart driver
                        if "Connection" in str(details_error) or "timeout" in str(details_error).lower():
                            print("  ! Connection issue detected. Restarting driver...")
                            parser.close_driver()
                            time.sleep(5)
                            parser.start_driver()
                        else:
                            time.sleep(2)
                        
                        if attempt == max_retries - 1:
                            raise details_error
                
                # Merge basic info with details
                full_data = {**match, **details}
                
                print(f"  > Date: {full_data.get('start_time', 'N/A')}")
                
                # Save to DB
                storage.add_match(full_data)
                
                # Sleep to represent human behavior
                sleep_time = random.uniform(2.5, 5.0)
                print(f"Sleeping for {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                
                # Restart driver periodically to free memory
                if count % 10 == 0:
                    print(f"Restarting browser to clear memory (processed {count})...")
                    parser.close_driver()
                    time.sleep(3)
                    parser.start_driver()
                    
            except Exception as e:
                print(f"Error processing match {match_id}: {e}")
                # Don't exit loop, try next match, but maybe restart driver first
                try:
                    parser.close_driver()
                    time.sleep(2)
                    parser.start_driver()
                except:
                    pass
                
    except Exception as e:
        print(f"Critical Collector Error: {e}")
    finally:
        print("\nClosing parser...")
        parser.close_driver()
        print("Done.")

if __name__ == "__main__":
    run_collector()
