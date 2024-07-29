import subprocess
import logging
import os
import time
from dotenv import dotenv_values
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to run setup commands with automated input handling
def run_setup_commands():
    try:
        logger.info("Cloning repository...")
        subprocess.run(["git", "clone", "https://github.com/foxytouxxx/freeroot.git"], check=True)
        
        logger.info("Changing directory to freeroot...")
        os.chdir("freeroot")
        
        logger.info("Running root.sh with automated input...")
        process = subprocess.Popen(
            ["bash", "root.sh"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=b"yes\n")
        if process.returncode != 0:
            logger.error(f"Error running root.sh: {stderr.decode()}")
            exit(1)
        
        logger.info("Executing CFwarp script with automated input...")
        process = subprocess.Popen(
            ["bash", "-c", "wget -qO- https://gitlab.com/rwkgyg/CFwarp/raw/main/CFwarp.sh 2> /dev/null | bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=b"3\n1\n3\n")
        if process.returncode != 0:
            logger.error(f"Error running CFwarp script: {stderr.decode()}")
            exit(1)
        
        logger.info("Installing spotdl and ffmpeg...")
        subprocess.run(["pip", "install", "spotdl"], check=True)
        subprocess.run(["spotdl", "--download-ffmpeg"], check=True)
        
        logger.info("Setup completed successfully.")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"An error occurred during setup: {e}")
        exit(1)

# Configuration class
class Config:
    def __init__(self):
        self.load_config()

    def load_config(self):
        try:
            token = dotenv_values(".env")["TELEGRAM_TOKEN"]
            print(f"Token from .env file: {token}")
        except KeyError:
            logger.error("TELEGRAM_TOKEN not found in .env file")
            token = os.environ.get('TELEGRAM_TOKEN')
            if token is None:
                logger.error("Telegram token not found. Make sure to set TELEGRAM_TOKEN environment variable.")
                raise ValueError("Telegram token not found.")
        self.token = token
        self.auth_enabled = False
        self.auth_password = "your_password"
        self.auth_users = []

config = Config()

# Authentication decorator
def authenticate(func):
    def wrapper(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        if config.auth_enabled:
            if chat_id not in config.auth_users:
                context.bot.send_message(chat_id=chat_id, text="⚠️ The password was incorrect")
                return
        return func(update, context)
    return wrapper

# Command handler for /start
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text="🎵 Welcome to the Song Downloader Bot! 🎵")

# Message handler for song downloads
def get_single_song(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id
    username = update.effective_chat.username
    logger.info(f'Starting song download. Chat ID: {chat_id}, Message ID: {message_id}, Username: {username}')

    url = update.effective_message.text.strip()

    download_dir = f".temp{message_id}{chat_id}"
    os.makedirs(download_dir, exist_ok=True)
    os.chdir(download_dir)

    logger.info('Downloading song...')
    context.bot.send_message(chat_id=chat_id, text="🔍 Downloading")

    if url.startswith(("http://", "https://")):
        subprocess.run(f'spotdl download "{url}" --threads 12 --format mp3 --bitrate 320k --lyrics genius', shell=True, check=True)

        logger.info('Sending song to user...')
        sent = 0
        files = [file for file in os.listdir(".") if file.endswith(".mp3")]
        if files:
            for file in files:
                try:
                    with open(file, 'rb') as audio_file:
                        context.bot.send_audio(chat_id=chat_id, audio=audio_file, timeout=18000)
                    sent += 1
                    time.sleep(0.3)  # Add a delay of 0.3 seconds between sending each audio file
                except Exception as e:
                    logger.error(f"Error sending audio: {e}")
            logger.info(f'Sent {sent} audio file(s) to user.')
        else:
            context.bot.send_message(chat_id=chat_id, text="❌ Unable to find the requested song.")
            logger.warning('No audio file found after download.')
    else:
        context.bot.send_message(chat_id=chat_id, text="❌ Invalid URL. Please provide a valid song URL.")
        logger.warning('Invalid URL provided.')

    os.chdir('..')
    subprocess.run(f'rm -rf {download_dir}', shell=True, check=True)

# Main function to start the bot
def main():
    run_setup_commands()

    updater = Updater(token=config.token, use_context=True)
    dispatcher = updater.dispatcher

    # Handlers
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    song_handler = MessageHandler(Filters.text & (~Filters.command), get_single_song)
    dispatcher.add_handler(song_handler)

    # Start the bot
    updater.start_polling(poll_interval=0.3)
    logger.info('Bot started')
    updater.idle()

if __name__ == "__main__":
    main()
