import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, PhoneNumberInvalidError
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest

# === بيانات البوت والحساب ===
BOT_TOKEN = '8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k'  # من @BotFather (استبدل بالتوكن الحقيقي)
API_ID = '27227913'  # من my.telegram.org
API_HASH = 'ba805b182eca99224403dbcd5d4f50aa'  # من my.telegram.org

# حالات التسجيل (لـ ConversationHandler)
PHONE, CODE, PASSWORD = range(3)

# عميل Telethon ديناميكي (بدون جلسة محفوظة)
user_client = None

async def get_client():
    """إنشاء عميل جديد دون جلسة محفوظة"""
    global user_client
    if user_client is None or not user_client.is_connected():
        user_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await user_client.connect()
    return user_client

# === أوامر عامة ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔑 تسجيل الدخول", callback_data='login')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'مرحبا! أنا بوت للتحكم في حسابك الشخصي.\n'
        'للعمل، اضغط الزر لبدء تسجيل الدخول عبر رقم الهاتف.\n'
        'ثم أرسل الأوامر مثل /set_name.',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
أوامر متاحة بعد تسجيل الدخول:
- /set_name <الاسم> : تغيير الاسم (مثال: /set_name محمد)
- /set_bio <السيرة> : تغيير السيرة (مثال: /set_bio أنا مطور!)
- /set_photo <مسار الصورة> : تغيير الصورة (مثال: /set_photo photo.jpg - ضعها في مجلد الكود)
- /status : حالة الاتصال
- /help : هذه القائمة

ملاحظة: يجب تسجيل الدخول لكل عملية (لا جلسة محفوظة).
    """
    await update.message.reply_text(help_text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        client = await get_client()
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            await update.message.reply_text(f'✅ متصل. الحساب: {me.first_name} (@{me.username})')
        else:
            keyboard = [[InlineKeyboardButton("🔑 تسجيل الدخول", callback_data='login')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                '❌ غير مصرح. اضغط الزر لبدء تسجيل الدخول.',
                reply_markup=reply_markup
            )
    except Exception as e:
        await update.message.reply_text(f'خطأ في الاتصال: {str(e)}')

# === معالج زر تسجيل الدخول ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'login':
        await query.edit_message_text('أرسل رقم هاتفك لتسجيل الدخول (مثال: +1234567890):')
        return PHONE
    return ConversationHandler.END

# === Conversation Handler لتسجيل الدخول ===
async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_number = update.message.text.strip()
    if not phone_number.startswith('+'):
        await update.message.reply_text('الرقم يجب أن يبدأ بـ + (مثال: +1234567890). جرب مرة أخرى:')
        return PHONE
    context.user_data['phone'] = phone_number
    try:
        client = await get_client()
        await client.send_code_request(phone_number)
        await update.message.reply_text(f'تم إرسال رمز التحقق إلى {phone_number}.\nأرسل الرمز (مثال: 12345):')
        return CODE
    except PhoneNumberInvalidError:
        await update.message.reply_text('رقم هاتف غير صالح. جرب مرة أخرى:')
        return PHONE
    except Exception as e:
        await update.message.reply_text(f'خطأ في إرسال الرمز: {str(e)}. جرب مرة أخرى:')
        return PHONE

async def code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    phone = context.user_data['phone']
    try:
        client = await get_client()
        await client.sign_in(phone, code)
        await update.message.reply_text('تم تسجيل الدخول بنجاح! الآن يمكنك إرسال الأوامر.')
        await client.disconnect()  # فصل للأمان (بدون حفظ)
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await update.message.reply_text('كلمة مرور 2FA مطلوبة. أرسلها الآن:')
        return PASSWORD
    except PhoneCodeInvalidError:
        await update.message.reply_text('رمز غير صالح. أرسل الرمز الصحيح:')
        return CODE
    except PhoneCodeExpiredError:
        await update.message.reply_text('الرمز منتهي الصلاحية. أعد إرسال الرمز بإرسال رقم الهاتف مرة أخرى.')
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f'خطأ في الرمز: {str(e)}. جرب مرة أخرى:')
        return CODE

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    phone = context.user_data['phone']
    try:
        client = await get_client()
        await client.sign_in(password=password)
        await update.message.reply_text('تم تسجيل الدخول بنجاح مع 2FA! الآن يمكنك إرسال الأوامر.')
        await client.disconnect()  # فصل للأمان
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f'كلمة مرور خاطئة: {str(e)}. جرب مرة أخرى:')
        return PASSWORD

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('تم إلغاء تسجيل الدخول.')
    return ConversationHandler.END

# === أوامر التحكم (تطلب تسجيلًا إذا لزم) ===
async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('أرسل الاسم: /set_name <الاسم>')
        return
    new_name = ' '.join(context.args).strip()
    try:
        client = await get_client()
        await client.connect()
        await client.sign_in()  # إذا لم يكن متصلًا، سيطلب التسجيل (لكن هنا نفترض تم التسجيل مسبقًا أو نضيف logic)
        # للبساطة، نفترض أن التسجيل تم في الجلسة الحالية؛ إذا فشل، يعيد الخطأ
        await client(UpdateProfileRequest(first_name=new_name))
        await update.message.reply_text(f'تم تغيير الاسم إلى: {new_name}')
        await client.disconnect()
    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔑 تسجيل الدخول أولاً", callback_data='login')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f'خطأ (ربما غير متصل): {str(e)}. اضغط الزر للتسجيل.', reply_markup=reply_markup)

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('أرسل السيرة: /set_bio <السيرة>')
        return
    new_bio = ' '.join(context.args).strip()
    try:
        client = await get_client()
        await client.connect()
        await client(UpdateProfileRequest(about=new_bio))
        await update.message.reply_text(f'تم تغيير السيرة إلى: {new_bio}')
        await client.disconnect()
    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔑 تسجيل الدخول أولاً", callback_data='login')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f'خطأ: {str(e)}. اضغط الزر للتسجيل.', reply_markup=reply_markup)

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('أرسل مسار الصورة: /set_photo <مسار>')
        return
    photo_path = context.args[0].strip()
    if not os.path.exists(photo_path):
        await update.message.reply_text('الملف غير موجود!')
        return
    try:
        client = await get_client()
        await client.connect()
        file = await client.upload_file(photo_path)
        await client(UploadProfilePhotoRequest(file))
        await update.message.reply_text('تم تغيير الصورة بنجاح!')
        await client.disconnect()
    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔑 تسجيل الدخول أولاً", callback_data='login')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f'خطأ في الصورة: {str(e)}. اضغط الزر.', reply_markup=reply_markup)

# === التشغيل الرئيسي ===
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation Handler للتسجيل
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(button_handler)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, code)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # إضافة المعالجات
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("set_name", set_name))
    application.add_handler(CommandHandler("set_bio", set_bio))
    application.add_handler(CommandHandler("set_photo", set_photo))

    print("البوت يعمل الآن! ابحث عنه في Telegram وابدأ بـ /start.")
    print("اضغط Ctrl+C للإيقاف.")

    application.run_polling()

if __name__ == '__main__':
    main()
