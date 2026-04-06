"""
JARVIS Telegram Bot — BULLETPROOF VERSION
"""
import asyncio, logging, sys
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

import config
from config import JARVIS_NAME, TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_ID
from assistant import JarvisAssistant

logging.basicConfig(level=logging.WARNING)

# Initialize Brain once
config.REMOTE_MODE = True
config.CONFIRM_COMMANDS = False
config.CONFIRM_DELETE = False
brain = JarvisAssistant()

def is_allowed(update: Update) -> bool:
    if not TELEGRAM_ALLOWED_ID: return True
    return str(update.effective_user.id) == str(TELEGRAM_ALLOWED_ID)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await update.message.reply_text(f"👋 *{JARVIS_NAME} is online and stable.*", parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    txt = update.message.text.strip()
    if not txt: return
    
    status_msg = await update.message.reply_text("⏳ Processing...")
    
    # Safe thread execution without UI updates
    loop = asyncio.get_running_loop()
    logs = []
    
    def silent_call(name, inputs):
        logs.append(f"🔧 Used: `{name}`")
        
    try:
        reply = await loop.run_in_executor(None, lambda: brain.chat(txt, on_tool_call=silent_call))
    except Exception as e:
        reply = f"❌ Core Error: {e}"

    try:
        await status_msg.delete()
    except:
        pass

    action_text = "\n".join(logs) + "\n\n" if logs else ""
    final_text = action_text + reply
    
    try:
        await update.message.reply_text(final_text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 JARVIS Telegram Bot running (Bulletproof Mode)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
