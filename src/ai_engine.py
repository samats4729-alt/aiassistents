import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIEngine:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        if not self.api_key:
            print("Warning: DEEPSEEK_API_KEY not found in .env")

    def analyze_match(self, match_data):
        """
        Sends match data to DeepSeek for analysis.
        match_data: dict containing home_team, away_team, recent_form, etc.
        """
        if not self.api_key:
            return "Error: API Key missing."

        prompt = self._construct_prompt(match_data)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Store history for follow-up questions
        self.conversation_history = [
            {"role": "system", "content": "Ты эксперт по ставкам на НХЛ. Проанализируй предоставленный матч, используя статистику и текущую форму команд. Дай структурированный прогноз на русском языке, включающий: 1. Ключевые факторы, 2. Анализ рисков, 3. Рекомендуемая ставка (Победитель/Тотал), 4. Уровень уверенности (1-10). Будь краток и профессионален."},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": "deepseek-chat",
            "messages": self.conversation_history,
            "temperature": 0.7
        }
        
        try:
            print(f"Отправка запроса в DeepSeek для матча {match_data.get('home_team')} vs {match_data.get('away_team')}...")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            analysis = result['choices'][0]['message']['content']
            
            # Save AI response to history
            self.conversation_history.append({"role": "assistant", "content": analysis})
            
            return analysis
            
        except Exception as e:
            return f"Ошибка анализа ИИ: {e}"

    def ask_followup(self, question):
        """Sends a follow-up question in the same context."""
        if not hasattr(self, 'conversation_history') or not self.conversation_history:
            return "Сначала выполните анализ матча."
            
        self.conversation_history.append({"role": "user", "content": question})
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": self.conversation_history,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            answer = result['choices'][0]['message']['content']
            self.conversation_history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            return f"Ошибка при ответе: {e}"

    def _construct_prompt(self, data):
        """Formats the match data into a readable text prompt."""
        today = datetime.now().strftime("%d.%m.%Y")
        
        prompt = f"""
        Проанализируй этот матч НХЛ. Дата: {today}
        
        Матч: {data.get('home_team')} (Дома) vs {data.get('away_team')} (В гостях)
        
        Статистика Хозяев:
        - Последние 5 игр: {data.get('home_last_5', 'N/A')}
        - Забитые/Игра: {data.get('home_gf_pg', 'N/A')}
        - Пропущенные/Игра: {data.get('home_ga_pg', 'N/A')}
        
        Статистика Гостей:
        - Последние 5 игр: {data.get('away_last_5', 'N/A')}
        - Забитые/Игра: {data.get('away_gf_pg', 'N/A')}
        - Пропущенные/Игра: {data.get('away_ga_pg', 'N/A')}
        
        Личные встречи (Последние 5):
        {data.get('h2h_summary', 'N/A')}
        
        Вратари:
        - Хозяева: {data.get('home_goalie', 'Не подтвержден')}
        - Гости: {data.get('away_goalie', 'Не подтвержден')}
        
        Инфо (травмы/заметки):
        {data.get('notes', 'Нет')}
        
        Кто победит? Какой Тотал? Отвечай на русском.
        """
        return prompt

if __name__ == "__main__":
    # Test stub
    engine = AIEngine()
    test_data = {
        "home_team": "New York Rangers",
        "away_team": "Boston Bruins",
        "home_last_5": "W-W-L-W-O",
        "away_last_5": "L-L-W-L-W",
        "h2h_summary": "Rangers won 3 of last 5",
        "home_gf_pg": "3.4",
        "home_ga_pg": "2.8",
        "away_gf_pg": "3.1",
        "away_ga_pg": "3.0"
    }
    print(engine.analyze_match(test_data))
