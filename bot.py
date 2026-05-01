import os
import zipfile
import uuid
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Track user upload sessions
user_sessions = {}


# 📥 Handle incoming media (no spam messages)
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_folder = os.path.join(DOWNLOAD_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    # Initialize session
    if user_id not in user_sessions:
        user_sessions[user_id] = {"saved": 0, "errors": 0}

    msg = update.message
    file = None
    file_name = None

    try:
        if msg.document:
            file = await msg.document.get_file()
            file_name = msg.document.file_name or "file"

        elif msg.photo:
            file = await msg.photo[-1].get_file()
            file_name = "photo.jpg"

        elif msg.video:
            file = await msg.video.get_file()
            file_name = "video.mp4"

        elif msg.audio:
            file = await msg.audio.get_file()
            file_name = msg.audio.file_name or "audio.mp3"

        elif msg.voice:
            file = await msg.voice.get_file()
            file_name = "voice.ogg"

        elif msg.video_note:
            file = await msg.video_note.get_file()
            file_name = "video_note.mp4"

        else:
            return

        # Prevent overwriting
        file_name = f"{uuid.uuid4()}_{file_name}"
        path = os.path.join(user_folder, file_name)

        await file.download_to_drive(path)

        user_sessions[user_id]["saved"] += 1

    except Exception:
        user_sessions[user_id]["errors"] += 1


# 📦 Zip command
async def zip_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_folder = os.path.join(DOWNLOAD_DIR, str(user_id))

    session = user_sessions.get(user_id, {"saved": 0, "errors": 0})

    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        await update.message.reply_text("No files to zip.")
        return

    zip_path = os.path.join(DOWNLOAD_DIR, f"{user_id}.zip")

    # Summary message
    await update.message.reply_text(
        f"Files received: {session['saved']}\n"
        f"Errors: {session['errors']}\n"
        "Zipping files..."
    )

    # Create zip
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for filename in os.listdir(user_folder):
            filepath = os.path.join(user_folder, filename)
            zipf.write(filepath, arcname=filename)

    # Send zip
    await update.message.reply_document(document=open(zip_path, 'rb'))

    # Cleanup
    for f in os.listdir(user_folder):
        os.remove(os.path.join(user_folder, f))
    os.rmdir(user_folder)
    os.remove(zip_path)

    # Reset session
    user_sessions.pop(user_id, None)


# 🚀 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me files (audio, video, documents, photos).\n"
        "When you're done, send 'zip'."
    )


# 🧠 Main bot setup
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start))

    # ZIP trigger (case-insensitive)
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("(?i)^(zip|/zip)$", re.IGNORECASE),
            zip_files
        )
    )

    # Media handler
    app.add_handler(MessageHandler(filters.ALL, handle_media))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
