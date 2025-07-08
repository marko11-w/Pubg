import os
from flask import Flask, request
import telebot
from telebot import types

# إعدادات البوت
TOKEN = "7863510154:AAHYUQn1pWaNfyA9zrdPIHIjcCb8nB2pz58"
WEBHOOK_URL = "https://pubg-production.up.railway.app/"
ADMIN_ID = 7758666677
CHANNEL_USERNAME = "MARK01i"

# إعداد البوت و Flask
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# الرد على /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "👋 مرحباً بك!\nأرسل صورة مع كلمة 'نسخة' وسأجهزها للنشر.\nأو استخدم /admin للدخول إلى لوحة التحكم.")

# لوحة التحكم للأدمن
@bot.message_handler(commands=["admin"])
def admin(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📝 تعديل النص")
        bot.send_message(message.chat.id, "🎛 لوحة التحكم", reply_markup=markup)
    else:
        bot.reply_to(message, "❌ أنت لا تملك صلاحية الدخول.")

# إعداد التحديثات من Telegram إلى Flask
@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# تشغيل البوت
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=8080)
