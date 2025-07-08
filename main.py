# main.py

import os
import telebot
from telebot import types
from flask import Flask, request
from config import TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_USERNAME, DEFAULT_TEXT, DATA_FOLDER
from image_utils import are_images_similar, write_text_on_image
import datetime
import json

# إعداد البوت
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تأكد من وجود مجلد البيانات
os.makedirs(DATA_FOLDER, exist_ok=True)
PHOTOS_PATH = os.path.join(DATA_FOLDER, "photos")
os.makedirs(PHOTOS_PATH, exist_ok=True)

# تحميل الصور السابقة (للمقارنة)
def get_existing_photos():
    return [os.path.join(PHOTOS_PATH, f) for f in os.listdir(PHOTOS_PATH) if f.endswith(".jpg")]

# تخزين صورة جديدة
def save_new_photo(file_id):
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = os.path.join(PHOTOS_PATH, f"{file_id}.jpg")
    with open(file_path, 'wb') as f:
        f.write(downloaded_file)
    return file_path

# استقبال التحديثات من تيليجرام عبر Webhook
@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# عند استقبال صورة
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not message.caption or "نسخة" not in message.caption:
        # مقارنة الصور المتشابهة
        file_id = message.photo[-1].file_id
        new_photo_path = save_new_photo(file_id)

        for existing_path in get_existing_photos():
            if are_images_similar(existing_path, new_photo_path):
                try:
                    os.remove(new_photo_path)
                    return  # لا تنشرها لأنها مكررة
                except:
                    pass
        return  # انتهى من التحقق من التكرار فقط

    # صورة مع "نسخة" — اكتب النص عليها
    file_id = message.photo[-1].file_id
    original_path = save_new_photo(file_id)
    output_path = original_path.replace(".jpg", "_edited.jpg")
    write_text_on_image(original_path, DEFAULT_TEXT, output_path)

    # إرسال أزرار النشر
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ نشر الآن", callback_data=f"publish_now|{output_path}"),
        types.InlineKeyboardButton("🕒 صباحًا", callback_data=f"schedule_morning|{output_path}"),
        types.InlineKeyboardButton("🌙 مساءً", callback_data=f"schedule_evening|{output_path}")
    )
    bot.reply_to(message, "📸 تم تجهيز الصورة.\nمتى تريد نشرها؟", reply_markup=markup)

# نشر الصورة الآن
@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_now"))
def publish_now(call):
    _, path = call.data.split("|")
    bot.send_photo(CHANNEL_USERNAME, open(path, "rb"))
    bot.answer_callback_query(call.id, "✅ تم النشر الآن")

# جدولة صباحية / مسائية (مؤقتًا فقط كعرض)
@bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_"))
def schedule_later(call):
    _, time_type, path = call.data.split("|")
    # ملاحظة: هنا فقط عرض كتنبيه، لاحقًا سيتم تنفيذ الجدولة بملف مستقل
    bot.answer_callback_query(call.id, f"📅 تم جدولة النشر ({'صباحًا' if time_type=='morning' else 'مساءً'})")
    # لاحقًا: نسجلها في ملف JSON للجدولة الحقيقية

# لوحة تحكم الأدمن
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✏️ تعديل النص")
    bot.send_message(message.chat.id, "🎛️ لوحة التحكم", reply_markup=markup)

# تعديل النص
@bot.message_handler(func=lambda m: m.text == "✏️ تعديل النص")
def ask_new_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📝 أرسل النص الجديد الذي تريد وضعه على الصور:")
    bot.register_next_step_handler(msg, save_new_text)

def save_new_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    with open(os.path.join(DATA_FOLDER, "text.txt"), "w", encoding='utf-8') as f:
        f.write(message.text.strip())
    bot.send_message(message.chat.id, "✅ تم حفظ النص الجديد بنجاح.")

# تحميل النص من الملف
def load_text():
    path = os.path.join(DATA_FOLDER, "text.txt")
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as f:
            return f.read()
    return DEFAULT_TEXT

# عند بدء التشغيل
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)
