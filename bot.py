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

# === بيانات البوت والحساب ===
BOT_TOKEN = '8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k'
API_ID = 27227913
API_HASH = 'ba805b182eca99224403dbcd5d4f50aa'

# إنشاء البوت
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# Telethon client
user_client = None
login_states = {}   # {user_id: {'state': 'phone|code|password|authorized', 'phone': '+number'}}
input_states = {}   # {user_id: 'set_name|set_bio|set_photo'}

# === إعداد event loop دائم ===
loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()

def run_async(coro):
    """تشغيل coroutine بأمان داخل loop دائم"""
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

# === دوال المساعدة ===
def create_user_client():
    """إنشاء عميل Telethon جديد"""
    global user_client
    if user_client is None or not user_client.is_connected():
        session = StringSession()
        user_client = TelegramClient(session, API_ID, API_HASH)
    return user_client

def ensure_client_connected():
    """تأكيد اتصال العميل"""
    global user_client
    if user_client is None:
        create_user_client()
    if not run_async(user_client.is_connected()):
        run_async(user_client.connect())

def is_authorized_sync():
    """التحقق من أن الجلسة مصرح بها"""
    global user_client
    try:
        if user_client is None:
            return False
        ensure_client_connected()
        return run_async(user_client.is_user_authorized())
    except Exception:
        return False

# === لوحات الأزرار ===
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

def help_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔐 كيفية التسجيل", callback_data="help_login"),
        types.InlineKeyboardButton("👤 الأوامر", callback_data="help_commands")
    )
    markup.add(types.InlineKeyboardButton("🖼️ عن الصور", callback_data="help_photo"))
    markup.add(types.InlineKeyboardButton("🔙 الرئيسية", callback_data="main_menu"))
    return markup

# === أوامر البوت ===
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        "✅ <b>مرحباً!</b>\nاستخدم الأزرار أدناه للتحكم في حسابك الشخصي.\n\nابدأ بتسجيل الدخول أولاً.",
        reply_markup=main_keyboard()
    )

# === الأزرار ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global user_client
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    # ======= إغلاق =======
    if data == 'close' or data == 'cancel':
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
    if data == 'login_start':
        if is_authorized_sync():
            bot.edit_message_text(
                "✅ أنت متصل بالفعل.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_keyboard()
            )
        else:
            bot.edit_message_text(
                "📱 أرسل رقم هاتفك الآن (مثال: +1234567890)",
                call.message.chat.id,
                call.message.message_id
            )
            input_states[user_id] = 'phone'
        return

    # ======= تغيير الاسم =======
    if data == 'set_name_btn':
        if not is_authorized_sync():
            bot.edit_message_text("❌ قم بتسجيل الدخول أولاً!", call.message.chat.id, call.message.message_id)
            return
        bot.edit_message_text("👤 أرسل الاسم الجديد:", call.message.chat.id, call.message.message_id)
        input_states[user_id] = 'set_name'
        return

    # ======= تغيير السيرة =======
    if data == 'set_bio_btn':
        if not is_authorized_sync():
            bot.edit_message_text("❌ قم بتسجيل الدخول أولاً!", call.message.chat.id, call.message.message_id)
            return
        bot.edit_message_text("📝 أرسل السيرة الجديدة (حد 170 حرف):", call.message.chat.id, call.message.message_id)
        input_states[user_id] = 'set_bio'
        return

    # ======= تغيير الصورة =======
    if data == 'set_photo_btn':
        if not is_authorized_sync():
            bot.edit_message_text("❌ قم بتسجيل الدخول أولاً!", call.message.chat.id, call.message.message_id)
            return
        bot.edit_message_text("📷 أرسل <b>مسار الصورة</b> (مثال: photo.jpg):", call.message.chat.id, call.message.message_id)
        input_states[user_id] = 'set_photo'
        return

# === استقبال الرسائل ===
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    global user_client
    user_id = message.from_user.id
    text = message.text.strip()
    state = input_states.get(user_id)

    # تسجيل الدخول عبر رقم الهاتف
    if state == 'phone':
        if not text.startswith('+'):
            bot.reply_to(message, "❌ الرقم يجب أن يبدأ بـ +.\nأعد الإرسال:")
            return
        create_user_client()
        ensure_client_connected()
        try:
            run_async(user_client.send_code_request(text))
            login_states[user_id] = {'phone': text, 'state': 'code'}
            bot.reply_to(message, "✅ تم إرسال <b>رمز التحقق</b> إلى حسابك.\nأرسل الرمز الآن:")
            input_states[user_id] = 'code'
        except PhoneNumberInvalidError:
            bot.reply_to(message, "❌ رقم غير صالح. تحقق من التنسيق.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ أثناء إرسال الكود: {e}")
        return

    # إدخال رمز التحقق
    if state == 'code':
        phone = login_states[user_id]['phone']
        try:
            run_async(user_client.sign_in(phone, text))
            login_states[user_id]['state'] = 'authorized'
            bot.reply_to(message, "✅ تم تسجيل الدخول بنجاح!", reply_markup=main_keyboard())
            input_states.pop(user_id, None)
        except SessionPasswordNeededError:
            bot.reply_to(message, "🔒 الحساب يحتوي على <b>كلمة مرور 2FA</b>.\nأرسلها الآن:")
            input_states[user_id] = 'password'
        except PhoneCodeInvalidError:
            bot.reply_to(message, "❌ رمز تحقق غير صحيح.")
        except PhoneCodeExpiredError:
            bot.reply_to(message, "⌛ انتهت صلاحية الرمز. أعد الإرسال.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ في التحقق: {e}")
        return

    # كلمة المرور
    if state == 'password':
        try:
            run_async(user_client.sign_in(password=text))
            login_states[user_id]['state'] = 'authorized'
            input_states.pop(user_id, None)
            bot.reply_to(message, "✅ تم تسجيل الدخول باستخدام 2FA!", reply_markup=main_keyboard())
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ في كلمة المرور: {e}")
        return

    # تغيير الاسم
    if state == 'set_name':
        if not is_authorized_sync():
            bot.reply_to(message, "❌ يجب تسجيل الدخول أولاً.")
            return
        try:
            run_async(user_client(UpdateProfileRequest(first_name=text)))
            bot.reply_to(message, f"✅ تم تغيير الاسم إلى <b>{text}</b>")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {e}")
        input_states.pop(user_id, None)
        return

    # تغيير السيرة
    if state == 'set_bio':
        if not is_authorized_sync():
            bot.reply_to(message, "❌ يجب تسجيل الدخول أولاً.")
            return
        if len(text) > 170:
            bot.reply_to(message, "❌ السيرة طويلة جدًا (الحد 170 حرف).")
            return
        try:
            run_async(user_client(UpdateProfileRequest(about=text)))
            bot.reply_to(message, "✅ تم تغيير السيرة بنجاح!")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {e}")
        input_states.pop(user_id, None)
        return

    # تغيير الصورة
    if state == 'set_photo':
        if not is_authorized_sync():
            bot.reply_to(message, "❌ يجب تسجيل الدخول أولاً.")
            return
        if not os.path.exists(text):
            bot.reply_to(message, f"❌ الملف <code>{text}</code> غير موجود.")
            return
        try:
            file = run_async(user_client.upload_file(text))
            run_async(user_client(UploadProfilePhotoRequest(file)))
            bot.reply_to(message, f"✅ تم تغيير الصورة إلى <code>{text}</code>")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ أثناء تغيير الصورة: {e}")
        input_states.pop(user_id, None)
        return

    # لا يوجد حالة نشطة
    bot.reply_to(message, "استخدم /start أو الأزرار للتحكم.")

# === تشغيل البوت ===
if __name__ == '__main__':
    print("🚀 البوت يعمل الآن!")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)
