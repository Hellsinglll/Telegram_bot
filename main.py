import os
import yt_dlp
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, 
    filters, CallbackContext
)
from telegram.constants import ChatMemberStatus

# 🔹 Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# 🔹 Telegram Bot Token
TOKEN = os.getenv("TOKEN")

# 🔹 Group & Channel Details
CHANNEL_ID = -1002682987275  
GROUP_ID = -1002375756524  
CHANNEL_LINK = "https://t.me/latest_animes_world"
GROUP_LINK = "https://t.me/All_anime_chat"

# 🔹 Flask Web Server (For UptimeRobot)
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "I'm alive!"

def run_web():
    """Runs the web server in a separate thread."""
    app_web.run(host="0.0.0.0", port=8080)

# 🔹 Check User Membership
async def is_user_member(bot, user_id):
    try:
        statuses = [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        chat_member_channel = await bot.get_chat_member(CHANNEL_ID, user_id)
        chat_member_group = await bot.get_chat_member(GROUP_ID, user_id)

        return (chat_member_channel.status in statuses) and (chat_member_group.status in statuses)
    except Exception as e:
        logger.error(f"Error checking membership: {e}")  
        return False

# 🔹 Start Command
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    bot = context.bot

    is_member = await is_user_member(bot, user.id)

    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("💬 Join Group", url=GROUP_LINK)],
            [InlineKeyboardButton("✅ I've Joined", callback_data=f"verify_join_{user.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔒 To use this bot, you must join our official channel and group.\n\n"
            f"📢 *Join the Channel:* [Click Here]({CHANNEL_LINK})\n"
            f"💬 *Join the Group:* [Click Here]({GROUP_LINK})\n\n"
            "After joining, tap *'I've Joined'* below.",
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📌 *Welcome\\!* \n\n"
            "🎥 Send me a video link \Facebook, Instagram, Twitter, TikTok, YouTube\ to download\\. \n\n"
            "💡 Type /help for more info\\.",
            parse_mode="MarkdownV2",
        )

# 🔹 Verify Membership
async def verify_join(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = int(query.data.split("_")[-1])
    bot = context.bot

    is_member = await is_user_member(bot, user_id)

    if is_member:
        await query.message.edit_text("✅ You are now verified! Send a video link to download.")
    else:
        await query.message.edit_text("❌ You haven't joined both the channel and group yet!")

# 🔹 Start the Bot
def main():
    bot = ApplicationBuilder().token(TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CallbackQueryHandler(verify_join, pattern="verify_join_.*"))

    Thread(target=run_web).start()
    bot.run_polling()

if __name__ == "__main__":
    main()
