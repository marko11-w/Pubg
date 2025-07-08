# main.py

import os
import telebot
from telebot import types
from flask import Flask, request
from config import TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_USERNAME, DEFAULT_TEXT, DATA_FOLDER
from image_utils import are_images_similar, write_text_on_image
from scheduler import start_scheduler, save_scheduled_posts, load_scheduled_posts
import datetime
import json

# إعداد البوت وFlask
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ✅ صفحة الفحص
@app.route("/", methods=["GET"])
def home():
    return "✅ Bot is running", 200

# ✅ استقبال Webhook من تيليجرام
@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# 🔧 إعداد المجلدات بأمان
PHOTOS_PATH = os.path.join(DATA_FOLDER, "photos")
TEXT_FILE = os.path.join(DATA_FOLDER, "text.txt")

try:
    if os.path.isfile(DATA_FOLDER):
        os.remove(DATA_FOLDER)
    os.makedirs(DATA_FOLDER, exist_ok=True)
except Exception as e:
    print(f"❌ فشل في إنشاء مجلد البيانات: {e}")

try:
    if os.path.isfile(PHOTOS_PATH):
        os.remove(PHOTOS_PATH)
    os.makedirs(PHOTOS_PATH, exist_ok=True)
except Exception as e:
    print(f"❌ فشل في إنشاء مجلد الصور: {e}")

# تحميل النص الحالي
def load_text():
    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE, "r", encoding='utf-8') as f:
            return f.read()
    return DEFAULT_TEXT

# أمر /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "👋 مرحبًا بك!\nأرسل صورة مع كلمة 'نسخة' وسأجهزها للنشر.\nأو استخدم /admin للدخول إلى لوحة التحكم.")

# تحميل الصور السابقة
def get_existing_photos():
    return [os.path.join(PHOTOS_PATH, f) for f in os.listdir(PHOTOS_PATH) if f.endswith(".jpg")]

# حفظ صورة جديدة
def save_new_photo(file_id):
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = os.path.join(PHOTOS_PATH, f"{file_id}.jpg")
    with open(file_path, 'wb') as f:
        f.write(downloaded_file)
    return file_path

# معالجة الصور
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    caption = message.caption or ""
    file_id = message.photo[-1].file_id
    new_photo_path = save_new_photo(file_id)

    if "نسخة" not in caption:
        for existing_path in get_existing_photos():
            if are_images_similar(existing_path, new_photo_path):
                os.remove(new_photo_path)
                return
        return

    final_path = new_photo_path.replace(".jpg", "_edited.jpg")
    write_text_on_image(new_photo_path, load_text(), final_path)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ نشر الآن", callback_data=f"publish_now|{final_path}"),
        types.InlineKeyboardButton("🕒 صباحًا", callback_data=f"schedule_morning|{final_path}"),
        types.InlineKeyboardButton("🌙 مساءً", callback_data=f"schedule_evening|{final_path}")
    )
    bot.reply_to(message, "📸 تم تجهيز الصورة.\nمتى تريد نشرها؟", reply_markup=markup)

# نشر مباشر
@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_now"))
def publish_now(call):
    _, path = call.data.split("|")
    try:
        bot.send_photo(CHANNEL_USERNAME, open(path, "rb"))
        bot.answer_callback_query(call.id, "✅ تم النشر الآن")
    except:
        bot.answer_callback_query(call.id, "❌ فشل في النشر")

# جدولة نشر صباحًا/مساءً
@bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_"))
def schedule_later(call):
    _, time_type, path = call.data.split("|")
    data = load_scheduled_posts()
    data.append({"time": time_type, "path": path})
    save_scheduled_posts(data)
    bot.answer_callback_query(call.id, f"📅 تم جدولة النشر ({'صباحًا' if time_type == 'morning' else 'مساءً'})")

# لوحة تحكم الأدمن
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✏️ تعديل النص")
    bot.send_message(message.chat.id, "🎛️ لوحة التحكم", reply_markup=markup)

# تعديل النص
@bot.message_handler(func=lambda m: m.text == "✏️
