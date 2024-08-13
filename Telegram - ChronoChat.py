import os
import telebot
import logging
import time
import schedule
import pyodbc  # For Microsoft SQL Server
from datetime import datetime
from telebot.types import Update

# ---------------------------
# Configuration and Setup
# ---------------------------

# Load bot token from environment variable for better security
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set the BOT_TOKEN environment variable.")

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Admin ID (replace with the actual admin's chat ID)
ADMIN_ID = 123456789

# ---------------------------
# Database Connection & Setup
# ---------------------------

# Connection to SQL Server
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=your_server_name;"  # Replace with your server name or IP
    "DATABASE=your_database_name;"  # Replace with your database name
    "UID=your_username;"  # Replace with your username
    "PWD=your_password;"  # Replace with your password
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Create table for chat information if it doesn't exist
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'chat_info')
    CREATE TABLE chat_info (
        chat_id BIGINT PRIMARY KEY,
        title NVARCHAR(255),
        type NVARCHAR(50),
        added_at DATETIME
    )
''')

# Create table for logging messages if it doesn't exist
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'message_logs')
    CREATE TABLE message_logs (
        chat_id BIGINT,
        message_text NVARCHAR(MAX),
        timestamp DATETIME
    )
''')

conn.commit()

# ---------------------------
# Helper Functions
# ---------------------------

def store_chat_info(chat_id, chat_title, chat_type):
    """
    Store chat information in the database.
    """
    cursor.execute('''
        IF NOT EXISTS (SELECT 1 FROM chat_info WHERE chat_id = ?)
        INSERT INTO chat_info (chat_id, title, type, added_at)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, chat_id, chat_title, chat_type, datetime.now()))
    conn.commit()
    logging.info(f"Stored chat info: {chat_id} - {chat_title} ({chat_type})")

def log_message(chat_id, message_text):
    """
    Log a chat message to the database.
    """
    cursor.execute('''
        INSERT INTO message_logs (chat_id, message_text, timestamp)
        VALUES (?, ?, ?)
    ''', (chat_id, message_text, datetime.now()))
    conn.commit()

def send_message(chat_id, message):
    """
    Send a message to the specified chat ID.
    """
    try:
        bot.send_message(chat_id, message)
        logging.info(f"Message sent successfully to chat ID: {chat_id}")
    except telebot.apihelper.ApiTelegramException as api_ex:
        logging.error(f"Telegram API error occurred while sending message: {api_ex}")
        bot.send_message(ADMIN_ID, f"Failed to send message to {chat_id}. Error: {api_ex}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
        bot.send_message(ADMIN_ID, f"Failed to send message to {chat_id}. Error: {e}")

def get_latest_chat_info():
    """
    Fetch the latest chat information (ID, title, type, and message text) from updates.
    
    Returns:
        tuple: (chat_id, chat_title, chat_type, message_text) or (None, None, None, None).
    """
    try:
        for attempt in range(3):
            try:
                updates = bot.get_updates(timeout=10)
                if updates:
                    # Get the latest update
                    latest_update = updates[-1]
                    chat = latest_update.message.chat
                    message_text = latest_update.message.text

                    chat_id = chat.id
                    chat_title = chat.title or chat.username or "Private Chat"
                    chat_type = chat.type

                    logging.info(f"Chat ID: {chat_id}, Chat Title: {chat_title}, Chat Type: {chat_type}, Message Text: {message_text}")

                    # Store chat info and log message
                    store_chat_info(chat_id, chat_title, chat_type)
                    log_message(chat_id, message_text)

                    # Set offset to avoid processing the same update again
                    bot.get_updates(offset=latest_update.update_id + 1)

                    return chat_id, chat_title, chat_type, message_text
            except telebot.apihelper.ApiTelegramException as api_ex:
                logging.error(f"Attempt {attempt + 1}: Telegram API error while fetching updates: {api_ex}")
                time.sleep(2 ** attempt)  # Exponential backoff
        else:
            logging.error("Failed to fetch updates after multiple attempts.")
            return None, None, None, None

    except telebot.apihelper.ApiTelegramException as api_ex:
        logging.error(f"Telegram API error: {api_ex}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    return None, None, None, None

# ---------------------------
# Bot Commands & Responses
# ---------------------------

@bot.message_handler(commands=['start'])
def start_command(message):
    """
    Handle the /start command.
    """
    chat_id = message.chat.id
    chat_title = message.chat.title or message.chat.username or "Private Chat"
    chat_type = message.chat.type

    store_chat_info(chat_id, chat_title, chat_type)
    welcome_message = "Welcome! I'm here to assist you. Use /info to know more."
    send_message(chat_id, welcome_message)

@bot.message_handler(commands=['info'])
def info_command(message):
    """
    Handle the /info command.
    """
    chat_id = message.chat.id
    info_message = (
        "I'm a bot that can do the following:\n"
        "- Automatically send scheduled messages at 10 AM daily.\n"
        "- Respond to your messages.\n"
        "- Collect and store group and channel information.\n"
        "- Schedule messages to specific chats.\n"
        "- Log messages to a database.\n"
    )
    send_message(chat_id, info_message)

@bot.message_handler(commands=['list_chats'])
def list_chats_command(message):
    """
    Handle the /list_chats command to list all stored chats.
    """
    cursor.execute('SELECT chat_id, title, type, added_at FROM chat_info')
    chats = cursor.fetchall()
    chat_list = "\n".join([f"{chat[1]} (ID: {chat[0]}, Type: {chat[2]}, Added: {chat[3]})" for chat in chats])
    send_message(message.chat.id, f"Stored chats:\n{chat_list}")

@bot.message_handler(commands=['remove_chat'])
def remove_chat_command(message):
    """
    Handle the /remove_chat command to remove a chat from storage.
    """
    command_parts = message.text.split()
    if len(command_parts) != 2:
        send_message(message.chat.id, "Usage: /remove_chat <chat_id>")
        return

    chat_id = int(command_parts[1])
    cursor.execute('DELETE FROM chat_info WHERE chat_id = ?', (chat_id,))
    conn.commit()
    send_message(message.chat.id, f"Chat with ID {chat_id} has been removed from storage.")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """
    Handle the /broadcast command (admin only).
    """
    if message.chat.type == "private":  # Restrict to private messages (assuming admin uses bot in private chat)
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) == 2:
            custom_message = command_parts[1]
            broadcast_message(custom_message)
        else:
            send_message(message.chat.id, "Usage: /broadcast <message>")
    else:
        send_message(message.chat.id, "Broadcast command can only be used in private chat.")

# ---------------------------
# Scheduled Tasks
# ---------------------------

def text():
    """
    Send a scheduled message to the latest chat.
    """
    chat_id, _, chat_type, _ = get_latest_chat_info()
    if chat_id:
        message = "Hello! How are you doing today? How may I assist you?"
        send_message(chat_id, message)
    else:
        logging.warning("No valid chat information retrieved for sending scheduled message.")

def handle_new_message():
    """
    Handles new incoming messages by fetching the latest chat info and responding to it.
    """
    chat_id, chat_title, chat_type, message_text = get_latest_chat_info()
    if chat_id:
        response_message = (
            f"Hello, {'group' if chat_type != 'private' else 'user'}! "
            f"This is a response to your message: '{message_text}'."
        )
        send_message(chat_id, response_message)
    else:
        logging.warning("No valid chat information retrieved. Message not sent.")

def schedule_daily_message():
    """
    Schedules the daily message at 10 AM.
    """
    schedule.every().day.at("10:00").do(text)

def schedule_message_for_chat(chat_id, message, time_str):
    """
    Schedule a message for a specific chat at a specific time.
    """
    schedule.every().day.at(time_str).do(send_message, chat_id=chat_id, message=message)

def broadcast_message(message):
    """
    Broadcast a message to all stored group and channel IDs.
    """
    cursor.execute('SELECT chat_id, title, type FROM chat_info')
    chats = cursor.fetchall()
    for chat in chats:
        chat_id, title, chat_type = chat
        logging.info(f"Broadcasting message to {title} ({chat_type})")
        send_message(chat_id, message)

# ---------------------------
# Main Execution
# ---------------------------

def run_bot():
    """
    Main function to execute the bot's operations in polling mode.
    """
    logging.info("Bot is running...")

    # Schedule the daily message
    schedule_daily_message()

    try:
        # Poll for new messages with error handling and restart logic
        while True:
            try:
                bot.polling(none_stop=True, interval=0)

                # Run the scheduled tasks
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logging.error(f"An error occurred during polling: {e}")
                bot.stop_polling()
                time.sleep(5)  # Wait before attempting to restart polling
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
        bot.stop_polling()

if __name__ == "__main__":
    run_bot()
