import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from api_fetcher import NHLAPIFetcher
from ai_engine import AIEngine
from main import simplify_game_data

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Global state: {chat_id: {'engine': AIEngine(), 'current_game': dict}}
user_sessions = {}

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {'engine': AIEngine(), 'fetcher': NHLAPIFetcher()}
    return user_sessions[chat_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏒 **Привет! Я AI-аналитик НХЛ.**\n\n"
        "Я могу проанализировать любой сегодняшний матч с помощью DeepSeek.\n\n"
        "Жми /games чтобы увидеть расписание.",
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    fetcher = session['fetcher']
    
    await context.bot.send_message(chat_id=chat_id, text="🔄 Сканирую расписание НХЛ...")
    
    games = fetcher.get_games_for_date()
    
    if not games:
        await context.bot.send_message(chat_id=chat_id, text="📅 На сегодня матчей не запланировано.")
        return

    keyboard = []
    for g in games:
        # Use simple ID or Index. Using Index is risky if list changes, but easier for stateless.
        # Better: Use GameID
        game_id = g.get('id') or g.get('gameId')
        
        home = g.get('homeTeam', {}).get('abbrev', 'H')
        away = g.get('awayTeam', {}).get('abbrev', 'A')
        time = g.get('startTimeUTC', '')[11:16] # Extract HH:MM if ISO format
        
        text = f"{home} vs {away} ({time})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"analyze_{game_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="🏒 **Выберите матч для анализа:**", reply_markup=reply_markup, parse_mode=constants.ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Acknowledge click
    
    data = query.data
    if data.startswith("analyze_"):
        game_id = data.split("_")[1] # Extract ID as string
        chat_id = update.effective_chat.id
        session = get_session(chat_id)
        
        await query.edit_message_text(text=f"⏳ Загружаю статистику и H2H (ID {game_id})...")
        
        # 1. Fetch details
        fetcher = session['fetcher']
        game_list = fetcher.get_games_for_date() # Need this to get basic info again or cache it
        # Find the game object
        selected_game = next((g for g in game_list if str(g.get('id') or g.get('gameId')) == str(game_id)), None)
        
        if not selected_game:
            await query.edit_message_text(text="❌ Ошибка: Матч не найден в кэше.")
            return

        details = fetcher.get_game_details(game_id)
        
        # 2. Prepare AI Prompt
        payload = simplify_game_data(selected_game, details, fetcher)
        
        await context.bot.send_message(chat_id=chat_id, text="🧠 **DeepSeek анализирует матч...**\n_(Это может занять 10-20 секунд)_", parse_mode=constants.ParseMode.MARKDOWN)
        
        # 3. Call AI
        engine = session['engine']
        analysis = engine.analyze_match(payload)
        
        # 4. Send Result
        # Escape markdown specific chars if needed, or rely on AI being good. 
        # DeepSeek usually writes proper MD.
        try:
            await context.bot.send_message(chat_id=chat_id, text=analysis, parse_mode=constants.ParseMode.MARKDOWN)
        except:
            # Fallback if MD parsing fails
            await context.bot.send_message(chat_id=chat_id, text=analysis)
            
        await context.bot.send_message(chat_id=chat_id, text="💬 **Чат открыт!**\nЗадайте вопрос по этому прогнозу или нажмите /games для нового матча.", parse_mode=constants.ParseMode.MARKDOWN)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    session = get_session(chat_id)
    
    # Check if we have an active AI session
    engine = session.get('engine')
    if engine and hasattr(engine, 'conversation_history') and engine.conversation_history:
        # It's a follow-up question
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
        response = engine.ask_followup(text)
        await update.message.reply_text(response, parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Сначала выберите матч через /games 🏒")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found in .env")
        exit(1)
        
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('games', games_menu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("🤖 Bot is running...")
    application.run_polling()
