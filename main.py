from flask import Flask, request
import telebot
import os

API_TOKEN = "7837218696:AAGSozPdf3hLT0bBjrgB3uExeuir-90Rvok"
CHANNEL_USERNAME = "@MARK01i"
ADMIN_ID = 7758666677

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)
user_data = {}

# تحقق من الاشتراك في القناة
def is_user_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# بدء البوت
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not is_user_subscribed(user_id):
        bot.send_message(user_id, f"🚫 يجب الاشتراك في القناة أولًا: {CHANNEL_USERNAME}")
        return
    user_data[user_id] = {}
    bot.send_message(user_id, "📸 أرسل صورة الحساب الذي تريد عرضه للبيع:")

# استقبال الصورة
@bot.message_handler(content_types=['photo'])
def get_photo(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return
    file_id = message.photo[-1].file_id
    user_data[user_id]['photo'] = file_id
    bot.send_message(user_id, "✍️ اكتب وصف الحساب:")

# استقبال النصوص (الوصف، النوع، السعر)
@bot.message_handler(func=lambda m: True)
def get_text(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    if 'desc' not in user_data[user_id]:
        user_data[user_id]['desc'] = message.text
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("🎮 ببجي", "🔥 فري فاير", "⚽ بيس", "🎯 أخرى")
        bot.send_message(user_id, "🎮 اختر نوع اللعبة:", reply_markup=markup)

    elif 'game' not in user_data[user_id]:
        user_data[user_id]['game'] = message.text
        bot.send_message(user_id, "💰 اكتب السعر المطلوب بالدولار:")

    elif 'price' not in user_data[user_id]:
        user_data[user_id]['price'] = message.text
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ إرسال الطلب", callback_data="send_request"))
        bot.send_message(user_id, "📦 اضغط لتأكيد إرسال الطلب للأدمن.", reply_markup=markup)

# عند الضغط على "إرسال الطلب"
@bot.callback_query_handler(func=lambda call: call.data == "send_request")
def send_to_admin(call):
    user_id = call.from_user.id
    data = user_data.get(user_id, {})
    if not data:
        return bot.send_message(user_id, "❌ حدث خطأ، حاول من جديد.")

    caption = f"""
🆕 طلب بيع حساب جديد

🎮 اللعبة: {data['game']}
📝 الوصف: {data['desc']}
💰 السعر: {data['price']}$

👤 البائع: @{call.from_user.username or 'بدون يوزر'}
🆔 ID: {user_id}
"""

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
        telebot.types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
    )
    bot.send_photo(ADMIN_ID, data['photo'], caption=caption, reply_markup=markup)
    bot.send_message(user_id, "📨 تم إرسال الطلب للإدارة، سيتم الرد عليك قريبًا.")
    del user_data[user_id]

# الموافقة والرفض
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def handle_admin_action(call):
    parts = call.data.split("_")
    action, user_id = parts[0], int(parts[1])
    message = call.message

    if action == "accept":
        caption = message.caption + "\n\n📌 لشراء الحساب تواصل مع البائع 👆"
        bot.send_photo(CHANNEL_USERNAME, message.photo[-1].file_id, caption=caption)
        bot.send_message(user_id, "✅ تم قبول عرض حسابك ونُشر في القناة!")
    else:
        bot.send_message(user_id, "❌ تم رفض عرض الحساب من قبل الإدارة.")

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# إعداد Webhook
@app.route('/', methods=['POST'])
def webhook():
    json_data = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "ok", 200

@app.route('/')
def home():
    return "Bot is running.", 200

if __name__ == "__main__":
    app.run(debug=True)
