import os
import yt_dlp
import tempfile
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

# 🔹 Telegram Bot Token (Replace with your actual token)
TOKEN = os.getenv("TOKEN")

# 🔹 Group & Channel Details (Replace with your actual IDs)
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

# 🔹 Check if User is a Member of the Channel & Group
async def is_user_member(bot, user_id):
    try:
        chat_member_channel = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        chat_member_group = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)

        allowed_statuses = [
            ChatMemberStatus.MEMBER, 
            ChatMemberStatus.ADMINISTRATOR, 
            ChatMemberStatus.OWNER, 
            ChatMemberStatus.RESTRICTED
        ]

        return (
            chat_member_channel.status in allowed_statuses and
            chat_member_group.status in allowed_statuses
        )
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
            [InlineKeyboardButton("✅ I've Joined", callback_data="verify_join")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔒 To use this bot, you must join our official channel and group.\n\n"
            f"📢 *Join the Channel:* [Click Here]({CHANNEL_LINK})\n"
            f"💬 *Join the Group:* [Click Here]({GROUP_LINK})\n\n"
            "After joining, tap *'I've Joined'* below.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📌 *Welcome!*\n\n"
            "🎥 Send me a video link (Facebook, Instagram, Twitter, TikTok, YouTube) to download.\n\n"
            "💡 Type /help for more info.",
            parse_mode="Markdown",
        )

# 🔹 Verify Join Button
async def verify_join(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    bot = context.bot

    is_member = await is_user_member(bot, user.id)

    if is_member:
        await query.message.reply_text("✅ You are now verified! Send a video link to download.")
    else:
        await query.message.reply_text("❌ You haven't joined both the channel and group yet!")

# 🔹 Help Command
async def help_command(update: Update, context: CallbackContext):
    help_text = (
        "🎥 *Video Downloader Bot*\n\n"
        "📌 *How to use?*\n"
        "1️⃣ Send a video link (YouTube, Facebook, Instagram, Twitter, TikTok, etc.).\n"
        "2️⃣ Choose the video quality (High/Low).\n"
        "3️⃣ The bot will download and send the video.\n\n"
        "💡 *Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/similar_bot - View similar bots\n\n"
        "🔗 *Join our Community:*\n"
        f"📢 [Channel]({CHANNEL_LINK})\n"
        f"💬 [Group]({GROUP_LINK})"
    )

    await update.message.reply_text(help_text, parse_mode="Markdown")

# 🔹 Similar Bots Command
async def similar_bots(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🎵 Music Lyrics Finder", url="https://t.me/Lyrics_Mfinderbot")],
        [InlineKeyboardButton("🔗 URL Shortener", url="https://t.me/URL_Shoorter_bot")],
        [InlineKeyboardButton("🖼️ Image to Text", url="https://t.me/Image_Ai_TextBot")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📌 *Similar Bots:*\nChoose from the list below:", parse_mode="Markdown", reply_markup=reply_markup)

# 🔹 Extract Video Info
def get_video_info(url):
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", "Unknown Title"), info.get("thumbnail", None)
    except yt_dlp.utils.DownloadError:
        return "⚠️ Unable to fetch video info (private/restricted?)", None

# 🔹 Ask for Video Quality
async def ask_quality(update: Update, context: CallbackContext):
    user = update.message.from_user
    bot = context.bot

    is_member = await is_user_member(bot, user.id)
    if not is_member:
        await start(update, context)
        return

    url = update.message.text

    # Validate URL
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("⚠️ Please send a valid video link.")
        return

    context.user_data["video_url"] = url  

    title, thumbnail_url = get_video_info(url)

    keyboard = [
        [InlineKeyboardButton("🔵 High Quality", callback_data="high")],
        [InlineKeyboardButton("🟢 Low Quality", callback_data="low")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if thumbnail_url:
        await update.message.reply_photo(photo=thumbnail_url, caption=f"🎬 {title}\n\nChoose video quality:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"🎬 {title}\n\nChoose video quality:", reply_markup=reply_markup)

# 🔹 Start the Bot
def main():
    bot = ApplicationBuilder().token(TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("help", help_command))
    bot.add_handler(CommandHandler("similar_bot", similar_bots))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality))
    bot.add_handler(CallbackQueryHandler(verify_join, pattern="verify_join"))

    Thread(target=run_web).start()
    bot.run_polling()

if __name__ == "__main__":
    main()
