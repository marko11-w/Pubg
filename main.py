import os
import telebot
from telebot import types
from flask import Flask, request
import hashlib
import requests

# إعدادات البوت
TOKEN = "7863510154:AAHYUQn1pWaNfyA9zrdPIHIjcCb8nB2pz58"
WEBHOOK_URL = "https://pubg-production.up.railway.app/"
ADMIN_ID = 7758666677
CHANNEL_USERNAME = "@MARK01i"
DATA_FOLDER = "data"
HASHES_FILE = f"{DATA_FOLDER}/hashes.txt"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تأكد من وجود مجلد data
os.makedirs(DATA_FOLDER, exist_ok=True)

# تحميل بصمات الصور المخزنة
def load_hashes():
    if not os.path.exists(HASHES_FILE):
        return set()
    with open(HASHES_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_hash(image_hash):
    with open(HASHES_FILE, "a") as f:
        f.write(image_hash + "\n")

def calculate_image_hash(file_path):
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# نقطة استقبال Webhook
@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# أمر /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "👋 مرحباً بك!\nأرسل صورة مع كلمة 'نسخة' وسأجهزها للنشر.\nأو استخدم /admin للدخول إلى لوحة التحكم.")

# أمر /admin
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "🎛️ لوحة التحكم")
    else:
        bot.reply_to(message, "🚫 ليس لديك صلاحية الوصول.")

# التعامل مع الصور
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path
    downloaded_file = bot.download_file(file_path)

    # حفظ الصورة مؤقتًا
    temp_image_path = f"{DATA_FOLDER}/temp.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(downloaded_file)

    # احسب بصمة الصورة
    image_hash = calculate_image_hash(temp_image_path)
    stored_hashes = load_hashes()

    if image_hash in stored_hashes:
        bot.reply_to(message, "🚫 هذه الصورة مكررة وتم تجاهلها.")
        return

    # احفظ البصمة
    save_hash(image_hash)

    if message.caption and "نسخة" in message.caption:
        bot.reply_to(message, "✅ تم استلام الصورة وسأجهزها للنشر.")
    else:
        bot.reply_to(message, "📸 صورة جديدة تم حفظها.")

# تفعيل Webhook
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)
