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
            "🎥 Send me a video link (Facebook, Instagram, Twitter, TikTok, YouTube) to download.\n"
            "🎵 Choose 'MP3' to get audio only.\n\n"
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

# 🔹 Extract Video Info
def get_video_info(url):
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", "Unknown Title"), info.get("thumbnail", None)
    except yt_dlp.utils.DownloadError:
        return "⚠️ Unable to fetch video info (private/restricted?)", None

async def ask_quality(update: Update, context: CallbackContext):
    user = update.message.from_user
    bot = context.bot

    # Ignore messages in groups (Bot will not react in groups)
    if update.message.chat.type in ["group", "supergroup"]:
        return

    is_member = await is_user_member(bot, user.id)
    if not is_member:
        await start(update, context)
        return

    url = update.message.text
    context.user_data["video_url"] = url  

    title, thumbnail_url = get_video_info(url)

    keyboard = [
        [InlineKeyboardButton("🔵 High Quality", callback_data="high")],
        [InlineKeyboardButton("🟢 Low Quality", callback_data="low")],
        [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="audio")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if thumbnail_url:
        await update.message.reply_photo(photo=thumbnail_url, caption=f"🎬 {title}\n\nChoose video quality:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"🎬 {title}\n\nChoose video quality:", reply_markup=reply_markup)

# 🔹 Download Video or Audio
async def download_video(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    quality = query.data  
    url = context.user_data.get("video_url", "")

    try:
        await query.edit_message_caption(f"📥 Downloading video in {quality.upper()} quality...")
    except:
        await query.message.reply_text(f"📥 Downloading video in {quality.upper()} quality...")

    format_choice = {
        "high": "best",
        "low": "worst",
        "audio": "bestaudio",
    }[quality]

    file_extension = "mp3" if quality == "audio" else "mp4"
    
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, f"downloaded_video.{file_extension}")

    ydl_opts = {
        "outtmpl": temp_file,
        "format": format_choice,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }] if quality == "audio" else [],
        "keepvideo": True,  
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        video_title = info.get("title", "Downloaded_Video").replace(" ", "_")
        output_file = os.path.join(temp_dir, f"{video_title}.{file_extension}")
        os.rename(temp_file, output_file)

        with open(output_file, "rb") as f:
            if quality == "audio":
                await query.message.reply_audio(audio=f, caption="✅ Here is your MP3 file!")
            else:
                await query.message.reply_video(video=f, caption="✅ Download complete!")

        os.remove(output_file)  

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download Error: {e}")
        await query.message.reply_text("❌ Download failed. This video might be private or restricted.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await query.message.reply_text(f"⚠️ Unexpected error: {str(e)}")

# 🔹 Handle Errors
async def error_handler(update: object, context: CallbackContext):
    logger.error(f"Exception: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ An error occurred. Please try again later.")

# 🔹 Start the Bot
def main():
    bot = ApplicationBuilder().token(TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality))
    bot.add_handler(CallbackQueryHandler(download_video))
    bot.add_handler(CallbackQueryHandler(verify_join, pattern="verify_join"))

    bot.add_error_handler(error_handler)

    Thread(target=run_web).start()
    bot.run_polling()

if __name__ == "__main__":
    main()
