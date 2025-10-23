import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
import os

# === بيانات البوت الرسمي (من @BotFather) ===
BOT_TOKEN = '8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k'  # استبدل بالتوكن الحقيقي، مثل '123456789:ABC...'

# === بيانات الحساب الشخصي ===
API_ID = '27227913'  # رقم من my.telegram.org
API_HASH = 'ba805b182eca99224403dbcd5d4f50aa'  # سلسلة من my.telegram.org
SESSION_FILE = 'my_session.txt'  # ملف الجلسة

# قراءة سلسلة الجلسة
def load_session_string():
    if not os.path.exists(SESSION_FILE):
        raise FileNotFoundError(f'ملف {SESSION_FILE} غير موجود! أنشئه وأضع فيه سلسلة الجلسة.')
    with open(SESSION_FILE, 'r', encoding='utf-8') as f:
        session_string = f.read().strip()
    if not session_string:
        raise ValueError('ملف الجلسة فارغ!')
    return session_string

# إنشاء عميل Telethon (الحساب الشخصي)
session_string = load_session_string()
user_client = TelegramClient(StringSession(session_string), API_ID, API_HASH)

# دالة للاتصال بالعميل الشخصي
async def connect_user_client():
    await user_client.connect()
    if not await user_client.is_user_authorized():
        raise ValueError('الجلسة غير صالحة! أعد تسجيل الدخول.')
    print("العميل الشخصي متصل بنجاح!")
    return user_client

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('مرحبا! أنا بوت للتحكم في حسابك الشخصي. أرسل /help للأوامر.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
أوامر متاحة للتحكم في حسابك الشخصي:
- /set_name <الاسم الجديد> : تغيير الاسم الأول (مثال: /set_name محمد)
- /set_bio <السيرة الجديدة> : تغيير السيرة الذاتية (مثال: /set_bio أنا مطور!)
- /set_photo <مسار الصورة> : تغيير الصورة (مثال: /set_photo photo.jpg - ضع الصورة في مجلد الكود)
- /help : عرض هذه القائمة
- /status : حالة الاتصال

أرسل الأوامر إلى هذا البوت مباشرة. كن حذرًا!
    """
    await update.message.reply_text(help_text)

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('أرسل الاسم: /set_name <الاسم>')
        return
    new_name = ' '.join(context.args).strip()
    try:
        user_client = await connect_user_client()
        await user_client(UpdateProfileRequest(first_name=new_name))
        await update.message.reply_text(f'تم تغيير الاسم إلى: {new_name}')
    except Exception as e:
        await update.message.reply_text(f'خطأ في تغيير الاسم: {str(e)}')

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('أرسل السيرة: /set_bio <السيرة>')
        return
    new_bio = ' '.join(context.args).strip()
    try:
        user_client = await connect_user_client()
        await user_client(UpdateProfileRequest(about=new_bio))
        await update.message.reply_text(f'تم تغيير السيرة إلى: {new_bio}')
    except Exception as e:
        await update.message.reply_text(f'خطأ في تغيير السيرة: {str(e)}')

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('أرسل مسار الصورة: /set_photo <مسار> (مثل photo.jpg)')
        return
    photo_path = context.args[0].strip()
    if not os.path.exists(photo_path):
        await update.message.reply_text('الملف غير موجود! تأكد من مسار الصورة في مجلد الكود.')
        return
    try:
        user_client = await connect_user_client()
        file = await user_client.upload_file(photo_path)
        await user_client(UploadProfilePhotoRequest(file))
        await update.message.reply_text('تم تغيير الصورة بنجاح!')
    except Exception as e:
        await update.message.reply_text(f'خطأ في تغيير الصورة: {str(e)}')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_client = await connect_user_client()
        me = await user_client.get_me()
        await update.message.reply_text(f'الحالة: متصل. الحساب: {me.first_name} (@{me.username})')
    except Exception as e:
        await update.message.reply_text(f'خطأ في الاتصال: {str(e)}')

# دالة التشغيل الرئيسية
async def main():
    # إنشاء تطبيق البوت
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة المعالجات (Handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("set_name", set_name))
    application.add_handler(CommandHandler("set_bio", set_bio))
    application.add_handler(CommandHandler("set_photo", set_photo))
    application.add_handler(CommandHandler("status", status))

    # تشغيل البوت
    print("البوت يعمل الآن! ابحث عنه في Telegram وابدأ الدردشة.")
    print("اضغط Ctrl+C للإيقاف.")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
