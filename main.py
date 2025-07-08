# main.py

import os
import json
import telebot
from telebot import types
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
import imagehash
from config import TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_USERNAME, DEFAULT_TEXT, DATA_FOLDER

# إعداد البوت وFlask
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# نقطة الفحص
@app.route("/", methods=["GET"])
def check():
    return "✅ Bot is running", 200

# استقبال Webhook
@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# المسارات
PHOTOS_PATH = os.path.join(DATA_FOLDER, "photos")
TEXT_FILE = os.path.join(DATA_FOLDER, "text.txt")
HASH_FILE = os.path.join(DATA_FOLDER, "hashes.json")

# تأكد من أن المجلدات موجودة
for path in [DATA_FOLDER, PHOTOS_PATH]:
    if os.path.exists(path) and not os.path.isdir(path):
        os.remove(path)
    if not os.path.exists(path):
        os.makedirs(path)

# تحميل النص الحالي
def load_text():
    if os.path.exists(TEXT_FILE):
        with open(TEXT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return DEFAULT_TEXT

# حفظ نص جديد
def save_text(new_text):
    with open(TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(new_text.strip())

# تحميل البصمات
def load_hashes():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return json.load(f)
    return []

# حفظ البصمات
def save_hashes(hashes):
    with open(HASH_FILE, "w") as f:
        json.dump(hashes, f)

# حساب بصمة الصورة
def get_image_hash(image_path):
    img = Image.open(image_path).convert("RGB")
    return str(imagehash.average_hash(img))

# كتابة نص على صورة
def write_text(img_path, text, out_path):
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 36)
    W, H = img.size
    w, h = draw.textsize(text, font=font)
    position = ((W - w) // 2, H - h - 20)
    draw.text(position, text, fill="white", font=font)
    img.save(out_path)

# استقبال الصور
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)

    path = os.path.join(PHOTOS_PATH, f"{file_id}.jpg")
    with open(path, "wb") as f:
        f.write(file)

    # فحص التكرار
    new_hash = get_image_hash(path)
    hashes = load_hashes()
    if new_hash in hashes:
        os.remove(path)
        return  # تم حذفه لأنه مكرر
    hashes.append(new_hash)
    save_hashes(hashes)

    # فحص إن كانت تحتوي على كلمة "نسخة"
    caption = message.caption or ""
    if "نسخة" in caption:
        output_path = path.replace(".jpg", "_edited.jpg")
        write_text(path, load_text(), output_path)

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ نشر الآن", callback_data=f"now|{output_path}")
        )
        bot.reply_to(message, "📸 تم تجهيز الصورة.\nاضغط للنشر:", reply_markup=markup)

# نشر مباشر
@bot.callback_query_handler(func=lambda call: call.data.startswith("now"))
def publish_now(call):
    _, path = call.data.split("|")
    try:
        bot.send_photo(CHANNEL_USERNAME, open(path, "rb"))
        bot.answer_callback_query(call.id, "✅ تم النشر إلى القناة.")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ فشل في النشر: {e}")

# /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "👋 أهلاً! أرسل صورة مع كلمة 'نسخة' وسأجهزها للنشر.\nاستخدم /admin للوصول إلى لوحة التحكم.")

# /admin للأدمن
@bot.message_handler(commands=["admin"])
def admin(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✏️ تعديل النص")
    bot.send_message(message.chat.id, "🎛️ لوحة التحكم", reply_markup=markup)

# تعديل النص
@bot.message_handler(func=lambda m: m.text == "✏️ تعديل النص")
def ask_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📝 أرسل النص الجديد:")
    bot.register_next_step_handler(msg, save_new_text)

def save_new_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    save_text(message.text)
    bot.send_message(message.chat.id, "✅ تم حفظ النص الجديد.")

# بدء التشغيل
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
