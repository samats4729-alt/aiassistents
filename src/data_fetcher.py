import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class FlashscoreParser:
    def __init__(self, headless=True):
        self.base_url = "https://www.flashscorekz.com/hockey/usa/nhl/"
        self.options = Options()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        self.driver = None

    def start_driver(self):
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.options)

    def close_driver(self):
        if self.driver:
            self.driver.quit()

    def get_upcoming_matches(self):
        """
        Fetches upcoming matches from the main hockey page.
        """
        if not self.driver:
            self.start_driver()
        
        print(f"Navigating to {self.base_url}...")
        self.driver.get(self.base_url)
        
        try:
            # Wait for the main container to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sportName"))
            )
            time.sleep(3) # Extra wait for dynamic content
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # This logic will need adjustment based on actual DOM structure
            # Flashscore usually uses 'sportName hockey' class for the container
            # and then 'event__match' for individual games.
            
            matches = []
            event_rows = soup.find_all('div', class_='event__match')
            
            print(f"Found {len(event_rows)} match rows.")
            
            for row in event_rows:
                # Extract basic info
                home_team = row.find('div', class_='event__participant--home')
                away_team = row.find('div', class_='event__participant--away')
                time_div = row.find('div', class_='event__time')
                
                if home_team and away_team:
                    match_info = {
                        'home': home_team.get_text(strip=True),
                        'away': away_team.get_text(strip=True),
                        'time': time_div.get_text(strip=True) if time_div else "N/A",
                        'id': row.get('id', '') # Flashscore IDs usually start with 'g_1_'
                    }
                    matches.append(match_info)
            
            return matches

        except Exception as e:
            print(f"Error fetching matches: {e}")
            return []

    def get_finished_matches(self):
        """
        Fetches finished (past) matches with scores.
        """
        # Restart driver to avoid session issues
        self.close_driver()
        self.start_driver()
        
        # Flashscore results page for hockey
        results_url = self.base_url + "results/"
        print(f"Navigating to {results_url}...")
        self.driver.get(results_url)
        
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sportName"))
            )
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            matches = []
            import re
            
            # Find all match links (eventRowLink contains full URL)
            match_links = soup.find_all('a', class_=re.compile(r'eventRowLink'))
            
            print(f"Found {len(match_links)} finished match rows.")
            
            for link in match_links:
                # Get the parent row for team/score data
                row = link.find_parent('div', class_=re.compile(r'event__match'))
                if not row:
                    row = link  # fallback
                
                home_team = row.find('div', class_=re.compile(r'event__participant--home'))
                away_team = row.find('div', class_=re.compile(r'event__participant--away'))
                home_score = row.find('span', class_=re.compile(r'event__score--home'))
                away_score = row.find('span', class_=re.compile(r'event__score--away'))
                
                # Fallback to div if span not found
                if not home_score:
                    home_score = row.find('div', class_=re.compile(r'event__score--home'))
                if not away_score:
                    away_score = row.find('div', class_=re.compile(r'event__score--away'))
                
                if home_team and away_team:
                    match_info = {
                        'home': home_team.get_text(strip=True),
                        'away': away_team.get_text(strip=True),
                        'home_score': home_score.get_text(strip=True) if home_score else "?",
                        'away_score': away_score.get_text(strip=True) if away_score else "?",
                        'id': row.get('id', ''),
                        'url': link.get('href', '')  # Full match URL
                    }
                    matches.append(match_info)
            
            return matches

        except Exception as e:
            print(f"Error fetching finished matches: {e}")
            return []

    def get_match_details(self, match_url):
        """
        Fetches detailed match data including H2H, statistics, and player stats.
        match_url should be the full URL from the results page (e.g., /match/hockey/team1/team2/?mid=XXX)
        """
        if not self.driver:
            self.start_driver()
        
        # Ensure full URL
        if match_url.startswith('/'):
            match_url = "https://www.flashscorekz.com" + match_url
        
        # Remove query params and trailing slash for base URL
        base_match_url = match_url.split('?')[0].rstrip('/')
        
        match_data = {
            'url': match_url,
            'start_time': 'N/A', # Will be updated
            'h2h': None,
            'stats': None,
            'player_stats': None
        }
        
        # 1. Get Match Date & H2H
        try:
            h2h_url = base_match_url + "#/h2h"
            self.driver.get(h2h_url)
            time.sleep(4)
            
            # Extract date/time from the page header
            try:
                date_el = self.driver.find_element(By.CLASS_NAME, "duelParticipant__startTime")
                if date_el:
                    match_data['start_time'] = date_el.text.strip()
            except Exception:
                pass # Keep default if not found
            
            # Click on H2H tab to ensure it's loaded
            click_tab_js = """
            var tabs = Array.from(document.querySelectorAll('a, button'));
            var h2hTab = tabs.find(t => t.innerText.includes('H2H') || t.innerText.includes('Очные'));
            if (h2hTab) { h2hTab.click(); return 'clicked'; }
            return 'not found';
            """
            self.driver.execute_script(click_tab_js)
            time.sleep(3)
            
            # Use JavaScript to extract H2H data using .h2h__row
            js_script = """
            var result = {
                matches: [],
                homeForm: [],
                awayForm: [],
                headToHead: []
            };
            
            // Find all H2H rows
            var rows = document.querySelectorAll('.h2h__row');
            var currentSection = '';
            
            rows.forEach(function(row) {
                var text = row.innerText.replace(/\\n/g, ' ').trim();
                if (text && text.length > 10) {
                    result.matches.push(text.substring(0, 100));
                }
            });
            
            // Try to separate by sections
            var sections = document.querySelectorAll('.h2h__section');
            sections.forEach(function(section, index) {
                var sectionRows = section.querySelectorAll('.h2h__row');
                sectionRows.forEach(function(row) {
                    var text = row.innerText.replace(/\\n/g, ' ').trim();
                    if (text && text.length > 10) {
                        if (index === 0) result.homeForm.push(text.substring(0, 100));
                        else if (index === 1) result.awayForm.push(text.substring(0, 100));
                        else result.headToHead.push(text.substring(0, 100));
                    }
                });
            });
            
            return result;
            """
            
            h2h_result = self.driver.execute_script(js_script)
            
            h2h_data = {
                'home_last5': h2h_result.get('homeForm', [])[:5] if h2h_result else [],
                'away_last5': h2h_result.get('awayForm', [])[:5] if h2h_result else [],
                'head_to_head': h2h_result.get('headToHead', [])[:10] if h2h_result else [],
                'all_matches': h2h_result.get('matches', [])[:15] if h2h_result else []
            }
            
            match_data['h2h'] = h2h_data
        except Exception as e:
            print(f"Error fetching H2H: {e}")
        
        # Get match statistics using JavaScript execution
        try:
            stats_url = base_match_url + "#/match-summary/match-statistics"
            self.driver.get(stats_url)
            time.sleep(4)
            
            # Click on "Статистика" tab to ensure it's active
            click_tab_js = """
            var tabs = Array.from(document.querySelectorAll('a, button, div[role="tab"], [class*="tab"]'));
            var statsTab = tabs.find(t => {
                var txt = t.innerText || t.textContent || "";
                return txt.toUpperCase().includes('СТАТИСТИКА') && !txt.toUpperCase().includes('ИГРОК');
            });
            
            if (statsTab) { 
                statsTab.click(); 
                return 'clicked'; 
            }
            
            // Fallback: try finding by href
            var linkTab = document.querySelector('a[href*="match-statistics"]');
            if (linkTab) {
                linkTab.click();
                return 'clicked_link';
            }
            
            return 'not found';
            """
            self.driver.execute_script(click_tab_js)
            time.sleep(3)
            
            # Use JavaScript to extract stats using specific stat__ classes
            js_script = """
            var stats = {};
            
            // Method 1: Use stat__row with stat__homeValue/category/awayValue
            var rows = document.querySelectorAll('[class*="stat__row"], [class*="statRow"]');
            rows.forEach(function(row) {
                var label = row.querySelector('[class*="category"], [class*="Category"]');
                var home = row.querySelector('[class*="homeValue"], [class*="Homev"]');
                var away = row.querySelector('[class*="awayValue"], [class*="Awayv"]');
                
                if (label && (home || away)) {
                    stats[label.innerText.trim()] = {
                        home: home ? home.innerText.trim() : '0',
                        away: away ? away.innerText.trim() : '0'
                    };
                }
            });
            
            // Method 2: Parse from text if method 1 didn't find enough stats
            if (Object.keys(stats).length < 5) {
                var allRows = document.querySelectorAll('[class*="row"], [class*="stat"]');
                allRows.forEach(function(row) {
                    if (row && row.innerText) {
                        var text = row.innerText.trim();
                        var parts = text.split(/[\\n\\t]+/).filter(p => p && p.trim());
                        
                        // Check if it looks like a stat row: Number String Number
                        if (parts.length >= 3) {
                             // E.g. "23", "Shots", "10"
                             var p1 = parts[0].trim();
                             var pLast = parts[parts.length-1].trim();
                             
                             if (p1.match(/^\\d+$/) && pLast.match(/^\\d+$/)) {
                                 var name = parts.slice(1, parts.length-1).join(' ').trim();
                                 if (name.length > 2 && !stats[name]) {
                                     stats[name] = {home: p1, away: pLast};
                                 }
                             }
                        }
                    }
                });
            }
            
            return stats;
            """
            
            extracted_stats = self.driver.execute_script(js_script)
            
            
            stats = {
                'shots_on_goal': {'home': '?', 'away': '?'},
                'shots_missed': {'home': '?', 'away': '?'},
                'saves': {'home': '?', 'away': '?'},
                'penalty_minutes': {'home': '?', 'away': '?'},
                'powerplay_goals': {'home': '?', 'away': '?'},
                'blocked_shots': {'home': '?', 'away': '?'},
                'faceoffs_won': {'home': '?', 'away': '?'},
                'raw': extracted_stats  # Store all extracted stats
            }
            
            # Map extracted stats to our keys
            if extracted_stats:
                for key, val in extracted_stats.items():
                    key_lower = key.lower()
                    # Flashscore uses "ударов в створ" or "броски в створ"
                    if ('удар' in key_lower or 'брос' in key_lower) and 'створ' in key_lower:
                        stats['shots_on_goal'] = val
                    elif 'отраж' in key_lower or 'сейв' in key_lower:
                        stats['saves'] = val
                    elif 'штраф' in key_lower:
                        stats['penalty_minutes'] = val
                    elif 'большинств' in key_lower:
                        stats['powerplay_goals'] = val
                    elif 'блок' in key_lower:
                        stats['blocked_shots'] = val
                    elif 'вбрас' in key_lower:
                        stats['faceoffs_won'] = val
                    elif 'мимо' in key_lower:
                        stats['shots_missed'] = val

            
            match_data['stats'] = stats
        except Exception as e:
            print(f"Error fetching stats: {e}")
        
        # Get player statistics using JavaScript execution
        try:
            player_stats_url = base_match_url + "#/match-summary/player-statistics"
            self.driver.get(player_stats_url)
            time.sleep(4)
            
            # Click on "Статистика игроков" tab
            click_tab_js = """
            var tabs = Array.from(document.querySelectorAll('button'));
            var playerTab = tabs.find(t => t.innerText.includes('игроков'));
            if (playerTab) { playerTab.click(); return 'clicked'; }
            return 'not found';
            """
            self.driver.execute_script(click_tab_js)
            time.sleep(3)
            
            # Use JavaScript to extract player data using ui-table__row
            js_script = """
            var result = {skaters: [], goalies: []};
            var isGoalieSection = false;
            
            // Find all table rows
            var rows = document.querySelectorAll('.ui-table__row, [class*="playerStatsTable__row"]');
            
            rows.forEach(function(row) {
                if (!row || !row.innerText) return;
                var text = row.innerText.trim().replace(/\\n/g, ' ');
                
                // Check if entering goalie section
                if (text.toLowerCase().includes('вратар') || text.toLowerCase().includes('goalie')) {
                    isGoalieSection = true;
                    return;
                }
                
                // Skip headers
                if (text.includes('ИГРОК') || text.includes('ВРАТАРЬ')) {
                    if (text.includes('ВРАТАРЬ')) isGoalieSection = true;
                    return;
                }
                
                // Look for player data (contains time format like XX:XX)
                if (text.match(/\\d+:\\d+/)) {
                    var parts = text.split(/\\s+/).filter(p => p.trim());
                    if (parts.length >= 5) {
                        // Detect goalie by save percentage pattern (XX.XX% or XX-XX format)
                        var hasGoalieStats = text.match(/\\d+-\\d+/) && text.match(/\\d+\\.\\d+%/);
                        var isShortRow = parts.length < 12;  // Goalies have fewer columns
                        
                        if (hasGoalieStats || (isShortRow && isGoalieSection)) {
                            // This is a goalie - format: name team O PIM TOI saves save%
                            var playerInfo = {
                                name: parts[0] + ' ' + (parts[1] || ''),
                                team: parts[2] || '',
                                toi: parts.find(p => p.match(/^\\d+:\\d+$/)) || '-',
                                saves: parts.find(p => p.match(/^\\d+-\\d+$/)) || '-',
                                savePercent: parts.find(p => p.match(/\\d+\\.\\d+%$/)) || '-'
                            };
                            result.goalies.push(playerInfo);
                        } else {
                            // This is a skater - format: name team G A P +/- PIM SOG ... TOI
                            var playerInfo = {
                                name: parts[0] + ' ' + (parts[1] || ''),
                                team: parts[2] || '',
                                goals: parts[3] || '-',
                                assists: parts[4] || '-',
                                points: parts[5] || '-',
                                plusMinus: parts[6] || '-',
                                pim: parts[7] || '-',
                                shots: parts[8] || '-',
                                toi: parts[parts.length - 1] || '-'
                            };
                            result.skaters.push(playerInfo);
                        }
                    }
                }
            });
            
            return result;
            """
            
            player_data = self.driver.execute_script(js_script)
            
            players = {
                'skaters': player_data.get('skaters', []) if player_data else [],
                'goalies': player_data.get('goalies', []) if player_data else [],
                'raw': player_data
            }
            
            match_data['player_stats'] = players
        except Exception as e:
            print(f"Error fetching player stats: {e}")
        
        return match_data

    def get_team_stats(self, team_url):
        """
        Fetches team statistics from the team page.
        """
        if not self.driver:
            self.start_driver()
        
        try:
            print(f"Fetching team stats: {team_url}")
            self.driver.get(team_url)
            time.sleep(3)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            team_data = {
                'form': [],  # Recent results
                'home_record': None,
                'away_record': None
            }
            
            # Extract form and records
            import re
            form_elements = soup.find_all('span', class_=re.compile(r'form'))
            for el in form_elements[:5]:
                team_data['form'].append(el.get_text(strip=True))
            
            return team_data
        except Exception as e:
            print(f"Error fetching team stats: {e}")
            return None

if __name__ == "__main__":
    parser = FlashscoreParser(headless=True)
    try:
        print("=== UPCOMING MATCHES ===")
        upcoming = parser.get_upcoming_matches()
        for m in upcoming[:5]:
            print(f"  {m['home']} vs {m['away']} @ {m['time']}")
        
        print("\n=== FINISHED MATCHES ===")
        finished = parser.get_finished_matches()
        for m in finished[:5]:
            print(f"  {m['home']} {m['home_score']} - {m['away_score']} {m['away']}")
        
        # Test detailed match data for one match
        if finished:
            print("\n=== MATCH DETAILS (first match) ===")
            match_url = finished[0].get('url', '')
            if match_url:
                details = parser.get_match_details(match_url)
                
                print(f"\n  STATS:")
                if details.get('stats'):
                    stats = details['stats']
                    print(f"    Shots on goal: {stats.get('shots_on_goal', {})}")
                    print(f"    Saves: {stats.get('saves', {})}")
                    print(f"    Penalty min: {stats.get('penalty_minutes', {})}")
                    print(f"    Powerplay: {stats.get('powerplay_goals', {})}")
                
                print(f"\n  PLAYERS:")
                if details.get('player_stats'):
                    ps = details['player_stats']
                    print(f"    Skaters found: {len(ps.get('skaters', []))}")
                    print(f"    Goalies found: {len(ps.get('goalies', []))}")
                    # Show first skater and goalie
                    if ps.get('skaters'):
                        print(f"    Sample skater: {ps['skaters'][0]}")
                    if ps.get('goalies'):
                        print(f"    Sample goalie: {ps['goalies'][0]}")
                
                print(f"\n  H2H:")
                if details.get('h2h'):
                    h2h = details['h2h']
                    print(f"    Head-to-head matches: {len(h2h.get('head_to_head', []))}")
                    if h2h.get('head_to_head'):
                        print(f"    Sample: {h2h['head_to_head'][0][:60]}...")
    finally:
        parser.close_driver()

