# scheduler.py

import os
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from config import DATA_FOLDER, CHANNEL_USERNAME
import telebot
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

SCHEDULE_FILE = os.path.join(DATA_FOLDER, "scheduled.json")

def load_scheduled_posts():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_scheduled_posts(data):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def post_scheduled_photos():
    now = datetime.now()
    hour = now.hour
    period = "morning" if 5 <= hour < 12 else "evening" if 17 <= hour < 23 else None
    if not period:
        return

    posts = load_scheduled_posts()
    remaining = []

    for post in posts:
        if post["time"] == period:
            try:
                bot.send_photo(CHANNEL_USERNAME, open(post["path"], "rb"))
            except Exception as e:
                print(f"❌ فشل في النشر: {e}")
        else:
            remaining.append(post)

    save_scheduled_posts(remaining)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(post_scheduled_photos, 'interval', minutes=15)
    scheduler.start()
