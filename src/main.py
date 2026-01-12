from api_fetcher import NHLAPIFetcher
from ai_engine import AIEngine
from datetime import datetime
import json

def simplify_game_data(game_info, details, fetcher=None):
    """
    Combines Schedule info + Matchup/Boxscore + Standings to query AI.
    """
    # Helper to clean name
    def clean_name(n):
        if isinstance(n, dict):
            return n.get('default', str(n))
        return str(n)

    # Use Abbrev for reliable mapping, Name for display
    home_abbrev = clean_name(game_info.get('homeTeam', {}).get('abbrev'))
    away_abbrev = clean_name(game_info.get('awayTeam', {}).get('abbrev'))
    
    # Try to get full names for better AI context
    home_full = clean_name(game_info.get('homeTeam', {}).get('name', home_abbrev))
    away_full = clean_name(game_info.get('awayTeam', {}).get('name', away_abbrev))
    
    data = {
        "home_team": home_full, # used for prompt
        "away_team": away_full,
        "date": game_info.get('date'),
        "notes": "No major injuries reported." 
    }
    
    # 1. Get Standings if possible (for form)
    standings_map = {}
    if fetcher:
        try:
            std = fetcher.get_standings()
            if std and 'standings' in std:
                for team in std['standings']:
                    # Map by abbrev
                    # Structure found: team['teamAbbrev']['default']
                    raw_abb = team.get('teamAbbrev', {})
                    abb = clean_name(raw_abb)
                    standings_map[abb] = team
        except: pass
        
    # Helper to extract team form
    def get_team_form(t_abbrev):
        if t_abbrev in standings_map:
            t = standings_map[t_abbrev]
            # L10 = Last 10 games form
            l10_wins = t.get('l10Wins', 0)
            l10_loss = t.get('l10Losses', 0)
            l10_ot = t.get('l10OtLosses', 0)
            ga = t.get('goalAgainst', 0)
            pts = t.get('points', 0)
            return f"Points: {pts}, L10: {l10_wins}-{l10_loss}-{l10_ot}, GF: {t.get('goalFor')}, GA: {ga}"
        return "N/A"

    data['home_last_5'] = get_team_form(home_abbrev)
    data['away_last_5'] = get_team_form(away_abbrev)
    
    # 2. Matchup (Head-to-Head)
    if 'matchup' in details:
        # Structure of matchup is complex, we just capture specific keys if we knew them
        # For now, we pass the raw dictionary reduced
        data['h2h_summary'] = str(details['matchup'])[:1000] # Cap length
        
    return data

def main():
    print("\n=== Анализатор НХЛ (на базе DeepSeek) ===")
    
    fetcher = NHLAPIFetcher()
    engine = AIEngine()
    
    while True:
        print("\nМеню:")
        print("1. Показать расписание на сегодня")
        print("2. Проанализировать матч (DeepSeek)")
        print("q. Выход")
        
        choice = input("\nВыберите опцию: ").strip().lower()
        
        if choice == 'q':
            break
            
        if choice == '1':
            games = fetcher.get_games_for_date()
            if not games:
                print("На сегодня игр не найдено.")
            else:
                print(f"\n--- Матчи на {datetime.now().strftime('%d.%m.%Y')} ---")
                for i, g in enumerate(games):
                    home = g.get('homeTeam', {}).get('abbrev', '?')
                    away = g.get('awayTeam', {}).get('abbrev', '?')
                    # Convert UTC to nicer format if possible, or just keep as is
                    time_str = g.get('startTimeUTC', 'TBD')
                    print(f"{i+1}. {home} vs {away} ({time_str})")
                    
        elif choice == '2':
            # Flow: Get list -> pick one -> analyze
            games = fetcher.get_games_for_date()
            if not games:
                print("Нет доступных матчей для анализа.")
                continue
                
            print("\nВыберите матч для анализа:")
            for i, g in enumerate(games):
                home = g.get('homeTeam', {}).get('abbrev', '?')
                away = g.get('awayTeam', {}).get('abbrev', '?')
                print(f"{i+1}. {home} vs {away}")
            
            try:
                idx = int(input("\nВведите номер матча: ")) - 1
                if 0 <= idx < len(games):
                    selected_game = games[idx]
                    game_id = selected_game.get('id') or selected_game.get('gameId')
                    
                    print(f"\nПолучение данных для матча ID {game_id}...")
                    details = fetcher.get_game_details(game_id)
                    
                    if details:
                        # Prepare simplified data for AI
                        ai_payload = simplify_game_data(selected_game, details, fetcher)
                        
                        print("Запрос к искусственному интеллекту...")
                        analysis = engine.analyze_match(ai_payload)
                        print("\n" + "="*40)
                        print("🤖 ПРОГНОЗ ИИ:")
                        print("="*40)
                        print(analysis)
                        
                        # Loop for follow-up chat
                        while True:
                            print("\n[Чат] Введите вопрос (или 'back' для выхода в меню):")
                            q = input("> ").strip()
                            if q.lower() in ['back', 'назад', 'exit', 'q']:
                                break
                            
                            print("Думаю...")
                            answer = engine.ask_followup(q)
                            print(f"\n🤖: {answer}")

                    else:
                        print("Не удалось получить детали матча.")
                else:
                    print("Неверный выбор.")
            except ValueError:
                print("Неверный ввод (введите число).")

if __name__ == "__main__":
    main()
