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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Bot Token
TOKEN = os.getenv("TOKEN")

# Channel & Group Details
CHANNEL_ID = -1002682987275  
GROUP_ID = -1002375756524  
CHANNEL_LINK = "https://t.me/latest_animes_world"
GROUP_LINK = "https://t.me/All_anime_chat"

# Flask Web Server (For UptimeRobot)
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "I'm alive!"

def run_web():
    """Runs the web server in a separate thread."""
    app_web.run(host="0.0.0.0", port=8080)

# Check if User is a Member
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

# Start Command
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

# Verify Join Button
async def verify_join(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    bot = context.bot

    is_member = await is_user_member(bot, user.id)

    if is_member:
        await query.message.reply_text("✅ You are now verified! Send a video link to download.")
    else:
        await query.message.reply_text("❌ You haven't joined both the channel and group yet!")

# Ask for Video Quality
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

    keyboard = [
        [InlineKeyboardButton("🔵 High Quality", callback_data="high")],
        [InlineKeyboardButton("🟢 Low Quality", callback_data="low")],
        [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="audio")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🎬 Choose video quality:", reply_markup=reply_markup)

# Download Video or Audio
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
    temp_file = os.path.join(temp_dir, f"downloaded.{file_extension}")

    # Save cookies from environment variable
    cookies_path = os.path.join(temp_dir, "cookies.txt")
    with open(cookies_path, "w") as f:
        f.write(os.getenv("YT_COOKIES", ""))

    ydl_opts = {
        "outtmpl": temp_file,
        "format": format_choice,
        "cookies": cookies_path,  
        "keepvideo": True,  # Prevents yt-dlp from deleting the original file
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }] if quality == "audio" else [],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        video_title = info.get("title", "Downloaded").replace(" ", "_")
        output_file = os.path.join(temp_dir, f"{video_title}.{file_extension}")

        # Ensure the file exists before renaming
        if os.path.exists(temp_file):
            os.rename(temp_file, output_file)
        else:
            logger.error(f"Error: File {temp_file} not found after download.")
            await query.message.reply_text("⚠️ Error: Downloaded file not found.")
            return

        with open(output_file, "rb") as f:
            if quality == "audio":
                await query.message.reply_audio(audio=f, caption="✅ Here is your MP3 file!")
            else:
                await query.message.reply_video(video=f, caption="✅ Download complete!")

        os.remove(output_file)
        os.remove(cookies_path)  

    except Exception as e:
        logger.error(f"Error: {e}")
        await query.message.reply_text(f"⚠️ Unexpected error: {str(e)}")

# Start the Bot
def main():
    bot = ApplicationBuilder().token(TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality))
    bot.add_handler(CallbackQueryHandler(verify_join, pattern="verify_join"))
    bot.add_handler(CallbackQueryHandler(download_video, pattern="^(high|low|audio)$"))

    Thread(target=run_web).start()
    bot.run_polling()

if __name__ == "__main__":
    main()
