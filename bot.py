import asyncio
import os
import threading
from telebot import TeleBot, types
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    FloodWaitError,
    UnauthorizedError
)
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest


# === إعدادات البوت والحساب ===
BOT_TOKEN = "8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k"
API_ID = 27227913
API_HASH = "ba805b182eca99224403dbcd5d4f50aa"

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# متغيرات الجلسة
user_client = None
login_states = {}
input_states = {}

# === إنشاء loop دائم لتشغيل Telethon بأمان ===
loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()

def run_async(coro):
    """تشغيل coroutine بأمان"""
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

def create_user_client():
    global user_client
    if user_client is None:
        session = StringSession()
        user_client = TelegramClient(session, API_ID, API_HASH)
    return user_client

def ensure_client_connected():
    global user_client
    if user_client is None:
        create_user_client()
    if not run_async(user_client.is_connected()):
        run_async(user_client.connect())

def is_authorized_sync():
    try:
        ensure_client_connected()
        return run_async(user_client.is_user_authorized())
    except Exception:
        return False

# === واجهة الأزرار ===
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔐 تسجيل الدخول", callback_data="login_start"),
        types.InlineKeyboardButton("👤 تغيير الاسم", callback_data="set_name_btn")
    )
    markup.add(
        types.InlineKeyboardButton("📝 تغيير السيرة", callback_data="set_bio_btn"),
        types.InlineKeyboardButton("🖼️ تغيير الصورة", callback_data="set_photo_btn")
    )
    markup.add(
        types.InlineKeyboardButton("📊 حالة الحساب", callback_data="status_btn"),
        types.InlineKeyboardButton("❓ مساعدة", callback_data="help_btn")
    )
    markup.add(types.InlineKeyboardButton("❌ إغلاق", callback_data="close"))
    return markup

# === أوامر البداية ===
@bot.message_handler(commands=["start"])
def start_command(message):
    bot.send_message(
        message.chat.id,
        "👋 <b>مرحباً بك!</b>\n"
        "استخدم الأزرار بالأسفل للتحكم في حسابك.\n"
        "ابدأ بتسجيل الدخول أولاً.",
        reply_markup=main_keyboard(),
    )

# === التعامل مع الأزرار ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global user_client
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    # ======= إغلاق الجلسة =======
    if data in ["close", "cancel"]:
        login_states.pop(user_id, None)
        input_states.pop(user_id, None)
        try:
            if user_client:
                run_async(user_client.disconnect())
        except:
            pass
        user_client = None
        bot.edit_message_text("❌ تم إغلاق الجلسة.", call.message.chat.id, call.message.message_id)
        return

    # ======= تسجيل الدخول =======
    if data == "login_start":
        if is_authorized_sync():
            bot.edit_message_text("✅ أنت متصل بالفعل.", call.message.chat.id, call.message.message_id, reply_markup=main_keyboard())
        else:
            bot.edit_message_text("📱 أرسل رقم هاتفك الآن (مثال: +1234567890)", call.message.chat.id, call.message.message_id)
            input_states[user_id] = "phone"
        return

    # ======= تغيير الاسم =======
    if data == "set_name_btn":
        if not is_authorized_sync():
            bot.edit_message_text("❌ قم بتسجيل الدخول أولاً!", call.message.chat.id, call.message.message_id)
            return
        bot.edit_message_text("👤 أرسل الاسم الجديد:", call.message.chat.id, call.message.message_id)
        input_states[user_id] = "set_name"
        return

    # ======= تغيير السيرة =======
    if data == "set_bio_btn":
        if not is_authorized_sync():
            bot.edit_message_text("❌ قم بتسجيل الدخول أولاً!", call.message.chat.id, call.message.message_id)
            return
        bot.edit_message_text("📝 أرسل السيرة الجديدة (حد 170 حرف):", call.message.chat.id, call.message.message_id)
        input_states[user_id] = "set_bio"
        return

    # ======= تغيير الصورة =======
    if data == "set_photo_btn":
        if not is_authorized_sync():
            bot.edit_message_text("❌ قم بتسجيل الدخول أولاً!", call.message.chat.id, call.message.message_id)
            return
        bot.edit_message_text("📷 أرسل مسار الصورة (مثال: photo.jpg):", call.message.chat.id, call.message.message_id)
        input_states[user_id] = "set_photo"
        return


# === استقبال الرسائل ===
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    global user_client
    user_id = message.from_user.id
    text = message.text.strip()
    state = input_states.get(user_id)

    # ======= تسجيل الدخول برقم الهاتف =======
    if state == "phone":
        if not text.startswith("+"):
            bot.reply_to(message, "❌ الرقم يجب أن يبدأ بـ +.\nأعد الإرسال:")
            return

        try:
            create_user_client()
            ensure_client_connected()
            run_async(user_client.send_code_request(text))
            login_states[user_id] = {"phone": text, "state": "code"}
            input_states[user_id] = "code"
            bot.reply_to(message, "✅ تم إرسال رمز التحقق إلى حسابك.\nأرسل الرمز الآن:")
        except PhoneNumberInvalidError:
            bot.reply_to(message, "❌ رقم غير صالح.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ أثناء إرسال الكود: {e}")
        return

    # ======= إدخال رمز التحقق =======
    if state == "code":
        phone = login_states[user_id]["phone"]
        try:
            ensure_client_connected()
            run_async(user_client.sign_in(phone, text))
            login_states[user_id]["state"] = "authorized"
            input_states.pop(user_id, None)
            bot.reply_to(message, "✅ تم تسجيل الدخول بنجاح!", reply_markup=main_keyboard())
        except SessionPasswordNeededError:
            bot.reply_to(message, "🔒 الحساب يحتوي على كلمة مرور 2FA.\nأرسلها الآن:")
            input_states[user_id] = "password"
        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            bot.reply_to(message, "❌ رمز غير صحيح أو منتهي الصلاحية.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ أثناء التحقق: {e}")
        return

    # ======= كلمة المرور 2FA =======
    if state == "password":
        try:
            ensure_client_connected()
            run_async(user_client.sign_in(password=text))
            login_states[user_id]["state"] = "authorized"
            input_states.pop(user_id, None)
            bot.reply_to(message, "✅ تم تسجيل الدخول باستخدام 2FA!", reply_markup=main_keyboard())
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ في كلمة المرور: {e}")
        return

    # ======= تغيير الاسم =======
    if state == "set_name":
        if not is_authorized_sync():
            bot.reply_to(message, "❌ يجب تسجيل الدخول أولاً.")
            return
        try:
            ensure_client_connected()
            run_async(user_client(UpdateProfileRequest(first_name=text)))
            bot.reply_to(message, f"✅ تم تغيير الاسم إلى: <b>{text}</b>")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ أثناء تغيير الاسم: {e}")
        input_states.pop(user_id, None)
        return

    # ======= تغيير السيرة =======
    if state == "set_bio":
        if not is_authorized_sync():
            bot.reply_to(message, "❌ يجب تسجيل الدخول أولاً.")
            return
        if len(text) > 170:
            bot.reply_to(message, "❌ السيرة طويلة جدًا (الحد 170 حرف).")
            return
        try:
            ensure_client_connected()
            run_async(user_client(UpdateProfileRequest(about=text)))
            bot.reply_to(message, "✅ تم تغيير السيرة بنجاح!")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ أثناء تغيير السيرة: {e}")
        input_states.pop(user_id, None)
        return

    # ======= تغيير الصورة =======
    if state == "set_photo":
        if not is_authorized_sync():
            bot.reply_to(message, "❌ يجب تسجيل الدخول أولاً.")
            return
        if not os.path.exists(text):
            bot.reply_to(message, f"❌ الملف {text} غير موجود.")
            return
        try:
            ensure_client_connected()
            file = run_async(user_client.upload_file(text))
            run_async(user_client(UploadProfilePhotoRequest(file)))
            bot.reply_to(message, f"✅ تم تغيير الصورة بنجاح إلى {text}")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ أثناء تغيير الصورة: {e}")
        input_states.pop(user_id, None)
        return

    bot.reply_to(message, "📍 استخدم /start لبدء التحكم.")

# === بدء التشغيل ===
if __name__ == "__main__":
    print("🚀 البوت يع كس مل الآن بشكل كامل!")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
