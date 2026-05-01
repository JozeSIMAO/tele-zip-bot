import os
import zipfile
import uuid
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_folder = os.path.join(DOWNLOAD_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    file = None
    file_name = None
    msg = update.message

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

    file_name = f"{uuid.uuid4()}_{file_name}"
    path = os.path.join(user_folder, file_name)

    await file.download_to_drive(path)
    await update.message.reply_text(f"Saved: {file_name}")


async def zip_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_folder = os.path.join(DOWNLOAD_DIR, str(user_id))

    if not os.path.exists(user_folder) or not os.listdir(user_folder):
        await update.message.reply_text("No files to zip.")
        return

    zip_path = os.path.join(DOWNLOAD_DIR, f"{user_id}.zip")

    await update.message.reply_text("Zipping files...")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for filename in os.listdir(user_folder):
            filepath = os.path.join(user_folder, filename)
            zipf.write(filepath, arcname=filename)

    await update.message.reply_document(document=open(zip_path, 'rb'))

    # Cleanup
    for f in os.listdir(user_folder):
        os.remove(os.path.join(user_folder, f))
    os.rmdir(user_folder)
    os.remove(zip_path)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send files (audio, video, documents, photos).\n"
        "When you're done, send 'zip'."
    )


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("(?i)^(zip|/zip)$"), zip_files))
    app.add_handler(MessageHandler(filters.ALL, handle_media))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
