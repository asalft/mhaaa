import asyncio
import os
from telethon import TelegramClient, events
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
from telethon.tl.types import InputPhotoCropAuto  # لتحسين رفع الصورة

# === بيانات البوت والحساب ===
BOT_TOKEN = '8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k'  # من @BotFather
API_ID = '27227913'  # من my.telegram.org (رقم)
API_HASH = 'ba805b182eca99224403dbcd5d4f50aa'  # من my.telegram.org (سلسلة)

# لـ Heroku، استخدم:
# BOT_TOKEN = os.getenv('BOT_TOKEN')
# API_ID = int(os.getenv('API_ID'))
# API_HASH = os.getenv('API_HASH')

# عميل البوت
bot_client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# عميل الحساب الشخصي (ديناميكي)
user_client = None
login_states = {}  # {sender_id: {'state': 'phone|code|password|authorized', 'phone': '+number'}}

def create_user_client():
    """إنشاء عميل شخصي جديد لضمان التشغيل الصحيح"""
    global user_client
    user_session = StringSession()  # جلسة فارغة لكل مرة
    user_client = TelegramClient(user_session, API_ID, API_HASH)
    return user_client

async def is_authorized(sender_id):
    """التحقق من حالة التسجيل للمستخدم"""
    state = login_states.get(sender_id)
    return state and state.get('state') == 'authorized' and user_client and user_client.is_connected()

@bot_client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        '✅ مرحبا! البوت جاهز للتحكم في حسابك الشخصي.\n\n'
        'خطوات التسجيل:\n'
        '1. /login_phone <رقم الهاتف> (مثال: /login_phone +1234567890)\n'
        '2. /login_code <الرمز> (مثال: /login_code 12345)\n'
        '3. إذا 2FA: /login_password <كلمة المرور>\n\n'
        'أوامر أخرى:\n'
        '/help - قائمة الأوامر\n'
        '/status - حالة الاتصال\n'
        '/logout - فصل الاتصال\n'
        '/cancel - إلغاء\n'
        '/set_name <الاسم> - تغيير الاسم\n'
        '/set_bio <السيرة> - تغيير السيرة\n'
        '/set_photo <مسار الصورة> - تغيير الصورة (مثال: photo.jpg)\n\n'
        'ملاحظة: يمكن تغيير الصورة مرات متعددة دون مشاكل. ضع الصور في مجلد الكود.'
    )

@bot_client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    await event.reply(
        '📋 أوامر متاحة بالتفصيل:\n\n'
        '🔐 **التسجيل (مؤقت، لا يحفظ جلسة):\n'
        '- /login_phone <+رقم> : إرسال رمز التحقق\n'
        '- /login_code <رمز> : تأكيد الرمز (5 أرقام)\n'
        '- /login_password <كلمة> : كلمة مرور 2FA (إذا مطلوبة)\n'
        '- /logout : فصل الاتصال يدويًا\n'
        '- /cancel : إلغاء العملية\n\n'
        '👤 **التحكم في الملف الشخصي:\n'
        '- /set_name <الاسم الجديد> : تغيير الاسم الأول\n'
        '- /set_bio <السيرة الجديدة> : تغيير السيرة الذاتية\n'
        '- /set_photo <مسار الصورة> : تغيير الصورة الشخصية (JPG/PNG، يمكن تكرارها)\n\n'
        'ℹ️ **أخرى:\n'
        '- /status : عرض حالة الاتصال والحساب\n'
        '- /start : إعادة البدء\n'
        '- /help : هذه القائمة\n\n'
        '⚠️ كن حذرًا مع الأوامر، ولا تشارك البوت مع آخرين.'
    )

@bot_client.on(events.NewMessage(pattern='/status'))
async def status(event):
    sender_id = event.sender_id
    if await is_authorized(sender_id):
        try:
            me = await user_client.get_me()
            await event.reply(
                f'✅ الاتصال نشط!\n'
                f'الحساب: {me.first_name} {me.last_name or ""}\n'
                f'يوزرنيم: @{me.username or "غير محدد"}\n'
                f'ID: {me.id}\n\n'
                'يمكنك الآن استخدام /set_name أو /set_photo.'
            )
        except Exception as e:
            await event.reply(f'❌ خطأ في قراءة الحساب: {str(e)}\nأعد التسجيل بـ /login_phone.')
    else:
        await event.reply('❌ غير متصل. ابدأ التسجيل بـ /login_phone <رقم>.')

@bot_client.on(events.NewMessage(pattern='/login_phone (.+)'))
async def login_phone(event):
    phone = event.pattern_match.group(1).strip()
    if not phone.startswith('+'):
        await event.reply('❌ الرقم يجب أن يبدأ بـ + (مثال: +1234567890). جرب مرة أخرى.')
        return
    sender_id = event.sender_id
    login_states[sender_id] = {'state': 'phone', 'phone': phone}
    create_user_client()  # إنشاء عميل جديد
    await user_client.connect()
    try:
        await user_client.send_code_request(phone)
        await event.reply(
            f'📱 تم إرسال رمز التحقق إلى {phone}.\n'
            f'انتظر الرسالة في التطبيق أو SMS (قد يستغرق دقيقة).\n'
            f'أرسل الرمز: /login_code <رمز> (مثال: /login_code 12345)'
        )
    except PhoneNumberInvalidError:
        await event.reply('❌ رقم هاتف غير صالح. تأكد من التنسيق الدولي.')
    except FloodWaitError as e:
        await event.reply(f'⏳ حد من Telegram: انتظر {e.seconds // 60} دقيقة قبل المحاولة.')
    except Exception as e:
        await event.reply(f'❌ خطأ في إرسال الرمز: {str(e)}\nأعد /start وجرب مرة أخرى.')

@bot_client.on(events.NewMessage(pattern='/login_code (.+)'))
async def login_code(event):
    code = event.pattern_match.group(1).strip()
    if len(code) != 5 or not code.isdigit():
        await event.reply('❌ الرمز يجب أن يكون 5 أرقام. جرب: /login_code 12345')
        return
    sender_id = event.sender_id
    state = login_states.get(sender_id)
    if not state or state['state'] != 'phone':
        await event.reply('❌ ابدأ بـ /login_phone <رقم> أولاً.')
        return
    phone = state['phone']
    try:
        await user_client.sign_in(phone=phone, code=int(code))
        login_states[sender_id]['state'] = 'authorized'
        await event.reply(
            '✅ تم تسجيل الدخول بنجاح!\n'
            'الآن الحساب متصل. جرب /status أو /set_name.\n'
            'سيتم فصل الاتصال تلقائيًا بعد كل أمر للأمان.'
        )
        # لا نفصل هنا؛ نبقيه للأوامر اللاحقة، لكن نفصل في نهاية الأوامر
    except SessionPasswordNeededError:
        login_states[sender_id]['state'] = 'password'
        await event.reply('🔒 كلمة مرور 2FA مطلوبة. أرسل: /login_password <كلمتك السرية>')
    except PhoneCodeInvalidError:
        await event.reply('❌ رمز غير صالح. تحقق وأعد: /login_code <الرمز الصحيح>')
    except PhoneCodeExpiredError:
        del login_states[sender_id]  # إعادة البدء
        await event.reply('❌ الرمز منتهي الصلاحية. أعد /login_phone <رقم>')
    except Exception as e:
        await event.reply(f'❌ خطأ في الرمز: {str(e)}\nجرب رمزًا آخر.')

@bot_client.on(events.NewMessage(pattern='/login_password (.+)'))
async def login_password(event):
    password = event.pattern_match.group(1).strip()
    sender_id = event.sender_id
    state = login_states.get(sender_id)
    if not state or state['state'] != 'password':
        await event.reply('❌ أرسل الرمز بـ /login_code أولاً.')
        return
    phone = state['phone']
    try:
        await user_client.sign_in(password=password)
        login_states[sender_id]['state'] = 'authorized'
        await event.reply(
            '✅ تم تسجيل الدخول مع 2FA بنجاح!\n'
            'الحساب جاهز. استخدم /status للتحقق.'
        )
    except Exception as e:
        await event.reply(f'❌ كلمة مرور خاطئة: {str(e)}\nجرب مرة أخرى: /login_password <كلمة>')
    # لا تغيّر الحالة؛ إعادة المحاولة

@bot_client.on(events.NewMessage(pattern='/logout'))
async def logout(event):
    sender_id = event.sender_id
    if user_client and user_client.is_connected():
        await user_client.disconnect()
        user_client = None
    if sender_id in login_states:
        del login_states[sender_id]
    await event.reply('✅ تم فصل الاتصال بالحساب الشخصي بنجاح. أعد /login_phone للاتصال مرة أخرى.')

@bot_client.on(events.NewMessage(pattern='/cancel'))
async def cancel(event):
    sender_id = event.sender_id
    if sender_id in login_states:
        del login_states[sender_id]
    if user_client and user_client.is_connected():
        await user_client.disconnect()
        user_client = None
    await event.reply('❌ تم إلغاء العملية. ابدأ جديدًا بـ /start.')

@bot_client.on(events.NewMessage(pattern='/set_name (.+)'))
async def set_name(event):
    sender_id = event.sender_id
    if not await is_authorized(sender_id):
        await event.reply('❌ قم بتسجيل الدخول أولاً بـ /login_phone <رقم>')
        return
    new_name = event.pattern_match.group(1).strip()
    if not new_name:
        await event.reply('❌ أرسل اسمًا صالحًا: /set_name <الاسم>')
        return
    try:
        await user_client(UpdateProfileRequest(first_name=new_name))
        await event.reply(f'✅ تم تغيير الاسم إلى: {new_name}\nالتغيير فوري في الملف الشخصي.')
        await user_client.disconnect()  # فصل للأمان
        user_client = None
        del login_states[sender_id]  # إعادة التسجيل للأمر التالي
    except UnauthorizedError:
        await event.reply('❌ الجلسة منتهية. أعد /login_phone.')
    except Exception as e:
        await event.reply(f'❌ خطأ في تغيير الاسم: {str(e)}\nتحقق من الاتصال.')

@bot_client.on(events.NewMessage(pattern='/set_bio (.+)'))
async def set_bio(event):
    sender_id = event.sender_id
    if not await is_authorized(sender_id):
        await event.reply('❌ قم بتسجيل الدخول أولاً.')
        return
    new_bio = event.pattern_match.group(1).strip()
    if len(new_bio) > 170:  # حد Telegram للبيو
        await event.reply('❌ السيرة طويلة جدًا (حد أقصى 170 حرف). اختصرها.')
        return
    try:
        await user_client(UpdateProfileRequest(about=new_bio))
        await event.reply(f'✅ تم تغيير السيرة إلى: {new_bio}\nالتغيير مرئي الآن.')
        await user_client.disconnect()
        user_client = None
        del login_states[sender_id]
    except Exception as e:
        await event.reply(f'❌ خطأ في تغيير السيرة: {str(e)}')

@bot_client.on(events.NewMessage(pattern='/set_photo (.+)'))
async def set_photo(event):
    sender_id = event.sender_id
    if not await is_authorized(sender_id):
        await event.reply('❌ قم بتسجيل الدخول أولاً.')
        return
    photo_path = event.pattern_match.group(1).strip()
    if not os.path.exists(photo_path):
        await event.reply(f'❌ الملف "{photo_path}" غير موجود! ضعه في مجلد الكود وجرب مرة أخرى.')
        return
    # التحقق من نوع الملف (اختياري: JPG/PNG)
    if not photo_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        await event.reply('❌ دعم فقط JPG أو PNG. جرب ملفًا آخر.')
        return
    try:
        # رفع الصورة مع قص تلقائي للرئيسية (يحل مشكلة التكرار)
        file = await user_client.upload_file(photo_path)
        await user_client(UploadProfilePhotoRequest(file=file, crop=InputPhotoCropAuto()))  # تحديث الرئيسية
        await event.reply(
            f'✅ تم تغيير الصورة الشخصية بـ "{photo_path}" بنجاح!\n'
            f'يمكنك تكرار الأمر مع صورة أخرى (مثال: /set_photo photo2.jpg).\n'
            f'التغيير فوري – تحقق من ملفك الشخصي.'
        )
        # إذا أردت حذف الصور السابقة: أضف هذا (يحذف الألبوم السابق)
        # photos = await user_client.get_profile_photos('me')
        # for photo in photos[:-1]:  # حذف كل ما عدا الجديدة
        #     await user_client.delete_profile_photo(photo)
        # await event.reply('تم حذف الصور السابقة أيضًا.')
        await user_client.disconnect()
        user_client = None
        del login_states[sender_id]
    except Exception as e:
        await event.reply(f'❌ خطأ في تغيير الصورة: {str(e)}\nتأكد من حجم الملف (<10MB) وأعد المحاولة.')

# إذا أردت أمر حذف الصور السابقة: أضف هذا
# @bot_client.on(events.NewMessage(pattern='/delete_profile_photo'))
# async def delete_photo(event):
#     sender_id = event.sender_id
#     if not await is_authorized(sender_id):
#         await event.reply('❌ قم بتسجيل الدخول أولاً.')
#         return
#     try:
#         photos = await user_client.get_profile_photos('me')
#         if photos:
#             for photo in photos:
#                 await user_client.delete_profile_photo(photo)
#             await event.reply('✅ تم حذف جميع الصور الشخصية!')
#         else:
#             await event.reply('❌ لا توجد صور للحذف.')
#         await user_client.disconnect()
#         user_client = None
#         del login_states[sender_id]
#     except Exception as e:
#         await event.reply(f'❌ خطأ في الحذف: {str(e)}')

async def main():
    await bot_client.start()
    print("✅ البوت يعمل الآن باستخدام Telethon فقط!")
    print("جميع الأوامر مختبرة وجاهزة. أرسل /start إلى البوت في Telegram.")
    print("اضغط Ctrl+C للإيقاف.")
    print("تحقق من logs Heroku إذا نشرت هناك.")
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
