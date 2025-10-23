import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.custom import InlineKeyboardMarkup, InlineKeyboardButton  # للأزرار Inline
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
BOT_TOKEN = '8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k'  # من @BotFather
API_ID = '27227913'  # من my.telegram.org (رقم)
API_HASH = 'ba805b182eca99224403dbcd5d4f50aa'  # من my.telegram.org (سلسلة)

# لـ Heroku: 
# BOT_TOKEN = os.getenv('BOT_TOKEN')
# API_ID = int(os.getenv('API_ID'))
# API_HASH = os.getenv('API_HASH')

# عميل البوت
bot_client = TelegramClient('bot_session', API_ID, API_HASH)

# متغيرات
user_client = None
login_states = {}  # {sender_id: {'state': 'phone|code|password|authorized|name|bio|photo', 'phone': '+number', 'input_for': 'command'}}
input_handlers = {}  # {sender_id: handler function} لقراءة الإدخال

def create_user_client():
    global user_client
    user_session = StringSession()
    user_client = TelegramClient(user_session, API_ID, API_HASH)
    return user_client

async def is_authorized(sender_id):
    state = login_states.get(sender_id)
    if state and state.get('state') == 'authorized' and user_client:
        try:
            if user_client.is_connected() and await user_client.is_user_authorized():
                return True
        except:
            pass
    return False

# لوحة الأزرار الرئيسية
def main_keyboard():
    buttons = [
        [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data='login_start')],
        [InlineKeyboardButton("👤 تغيير الاسم", callback_data='set_name'),
         InlineKeyboardButton("📝 تغيير السيرة", callback_data='set_bio')],
        [InlineKeyboardButton("🖼️ تغيير الصورة", callback_data='set_photo')],
        [InlineKeyboardButton("📊 حالة الحساب", callback_data='status'),
         InlineKeyboardButton("❓ مساعدة", callback_data='help')],
        [InlineKeyboardButton("❌ إغلاق", callback_data='close')]
    ]
    return InlineKeyboardMarkup(buttons)

# لوحة تسجيل الدخول
def login_keyboard():
    buttons = [
        [InlineKeyboardButton("📱 أرسل رقم الهاتف", callback_data='login_phone')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='cancel')]
    ]
    return InlineKeyboardMarkup(buttons)

# لوحة بعد الرمز (إذا 2FA)
def password_keyboard():
    buttons = [
        [InlineKeyboardButton("🔒 أرسل كلمة المرور", callback_data='login_password')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='cancel')]
    ]
    return InlineKeyboardMarkup(buttons)

# لوحة المساعدة
def help_keyboard():
    buttons = [
        [InlineKeyboardButton("🔐 كيفية التسجيل", callback_data='help_login'),
         InlineKeyboardButton("👤 الأوامر الرئيسية", callback_data='help_commands')],
        [InlineKeyboardButton("🖼️ عن الصور", callback_data='help_photo')],
        [InlineKeyboardButton("🔙 الرئيسية", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply(
        '✅ مرحبا! اضغط على الأزرار أدناه للتحكم في حسابك الشخصي.\n\n'
        'إذا كنت جديدًا، ابدأ بـ "تسجيل الدخول".',
        reply_markup=main_keyboard()
    )

# معالج الأزرار Callback
@bot_client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    sender_id = event.sender_id
    await event.answer()  # إخفاء "typing"

    if data == 'main_menu':
        await event.edit('القائمة الرئيسية:', reply_markup=main_keyboard())
        return

    if data == 'close':
        await event.edit('تم الإغلاق. أعد /start.', reply_markup=None)
        if sender_id in login_states:
            del login_states[sender_id]
        if user_client:
            await user_client.disconnect()
            user_client = None
        return

    if data == 'login_start':
        if await is_authorized(sender_id):
            await event.edit('أنت متصل بالفعل! استخدم الأزرار الأخرى.', reply_markup=main_keyboard())
            return
        await event.edit('ابدأ تسجيل الدخول:', reply_markup=login_keyboard())
        login_states[sender_id] = {'state': 'login_start'}
        return

    if data == 'login_phone':
        state = login_states.get(sender_id)
        if not state:
            await event.edit('ابدأ بـ /start أولاً.', reply_markup=main_keyboard())
            return
        login_states[sender_id]['state'] = 'phone'
        await event.edit('أرسل رقم هاتفك الآن (مثال: +1234567890):\n(ارسل في الرسالة التالية)', reply_markup=None)
        # تهيئة الإدخال
        input_handlers[sender_id] = 'phone'
        return

    if data == 'login_code':
        state = login_states.get(sender_id)
        if state['state'] != 'phone':
            await event.edit('أرسل الرمز الآن (5 أرقام):', reply_markup=None)
            input_handlers[sender_id] = 'code'
            return
        login_states[sender_id]['state'] = 'code'
        await event.edit('تم إرسال الرمز! أرسله الآن (مثال: 12345):', reply_markup=None)
        input_handlers[sender_id] = 'code'
        return

    if data == 'login_password':
        state = login_states.get(sender_id)
        if state['state'] != 'code':
            await event.edit('أرسل كلمة مرور 2FA الآن:', reply_markup=None)
            input_handlers[sender_id] = 'password'
            return
        login_states[sender_id]['state'] = 'password'
        await event.edit('كلمة مرور 2FA مطلوبة. أرسلها في الرسالة التالية:', reply_markup=password_keyboard())
        input_handlers[sender_id] = 'password'
        return

    if data == 'set_name':
        if not await is_authorized(sender_id):
            await event.edit('تسجيل أولاً!', reply_markup=login_keyboard())
            return
        await event.edit('أرسل الاسم الجديد في الرسالة التالية:', reply_markup=None)
        input_handlers[sender_id] = 'set_name'
        return

    if data == 'set_bio':
        if not await is_authorized(sender_id):
            await event.edit('تسجيل أولاً!', reply_markup=login_keyboard())
            return
        await event.edit('أرسل السيرة الجديدة في الرسالة التالية (حد 170 حرف):', reply_markup=None)
        input_handlers[sender_id] = 'set_bio'
        return

    if data == 'set_photo':
        if not await is_authorized(sender_id):
            await event.edit('تسجيل أولاً!', reply_markup=login_keyboard())
            return
        await event.edit('أرسل مسار الصورة في الرسالة التالية (مثال: photo.jpg - ضعها في مجلد الكود):', reply_markup=None)
        input_handlers[sender_id] = 'set_photo'
        return

    if data == 'status':
        if await is_authorized(sender_id):
            try:
                me = await user_client.get_me()
                text = f'✅ متصل!\nاسم: {me.first_name}\nيوزر: @{me.username or "غير"}\nID: {me.id}'
                await event.edit(text, reply_markup=main_keyboard())
            except Exception as e:
                await event.edit(f'❌ خطأ: {str(e)}', reply_markup=login_keyboard())
        else:
            await event.edit('غير متصل. تسجيل أولاً!', reply_markup=login_keyboard())
        return

    if data == 'help':
        await event.edit('مساعدة:', reply_markup=help_keyboard())
        return

    if data == 'help_login':
        await event.edit(
            '🔐 كيفية التسجيل:\n'
            '1. نقر "تسجيل الدخول" → "أرسل رقم الهاتف" → أرسل +رقمك.\n'
            '2. يرسل رمز → "أرسل الرمز" → أرسل 5 أرقام.\n'
            '3. إذا 2FA: "أرسل كلمة المرور" → أرسل الكلمة.\n\n'
            'التسجيل مؤقت (لا يحفظ جلسة).',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رئيسية", callback_data='main_menu')]])
        )
        return

    if data == 'help_commands':
        await event.edit(
            '👤 الأوامر:\n'
            '- تغيير الاسم: نقر الزر → أرسل الاسم.\n'
            '- تغيير السيرة: نقر → أرسل النص (قصير).\n'
            '- تغيير الصورة: نقر → أرسل مسار (photo.jpg).\n\n'
            'يمكن تكرار الصورة دون مشاكل.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رئيسية", callback_data='main_menu')]])
        )
        return

    if data == 'help_photo':
        await event.edit(
            '🖼️ عن الصورة:\n'
            '- ضع الصورة (JPG/PNG، <10MB) في مجلد الكود.\n'
            '- نقر "تغيير الصورة" → أرسل المسار (مثال: photo1.jpg).\n'
            '- يحدث الصورة الرئيسية فورًا ويدعم التكرار (غيّر عدة مرات).\n'
            '- للحذف: استخدم /delete (غير inline حاليًا).',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رئيسية", callback_data='main_menu')]])
        )
        return

    if data == 'cancel':
        if sender_id in login_states:
            del login_states[sender_id]
        if sender_id in input_handlers:
            del input_handlers[sender_id]
        if user_client:
            await user_client.disconnect()
            user_client = None
        await event.edit('❌ إلغاء.', reply_markup=main_keyboard())
        return

# معالج الرسائل النصية (للإدخال بعد الأزرار)
@bot_client.on(events.NewMessage)
async def message_handler(event):
    text = event.text.strip()
    sender_id = event.sender_id
    input_type = input_handlers.get(sender_id)

    if input_type == 'phone':
        phone = text
        if not phone.startswith('+'):
            await event.reply('الرقم يجب + (مثال: +1234567890). أعد الإرسال.')
            return
        login_states[sender_id]['state'] = 'code'
        login_states[sender_id]['phone'] = phone
        create_user_client()
        await user_client.connect()
        try:
            await user_client.send_code_request(phone)
            await event.reply('رمز مرسل! أرسل الرمز (5 أرقام):', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ إعادة إرسال", callback_data='login_code')]]))
            input_handlers[sender_id] = 'code'
        except PhoneNumberInvalidError:
            await event.reply('رقم غير صالح.')
            input_handlers[sender_id] = None
        except FloodWaitError as e:
            await event.reply(f'انتظر {e.seconds} ثوانٍ.')
        except Exception as e:
            await event.reply(f'خطأ: {str(e)}')
        return

    if input_type == 'code':
        code = text
        if len(code) != 5 or not code.isdigit():
            await event.reply('5 أرقام فقط. أعد الإرسال.')
            return
        state = login_states.get(sender_id)
        phone = state['phone']
        try:
            await user_client.sign_in(phone=phone, code=int(code))
            state['state'] = 'authorized'
            del input_handlers[sender_id]
            await event.reply('✅ تسجيل ناجح! استخدم القائمة.', reply_markup=main_keyboard())
        except SessionPasswordNeededError:
            state['state'] = 'password'
            await event.reply('2FA مطلوب. أرسل الكلمة:', reply_markup=password_keyboard())
            input_handlers[sender_id] = 'password'
        except PhoneCodeInvalidError:
            await event.reply('رمز خاطئ. أعد الإرسال.')
        except PhoneCodeExpiredError:
            del login_states[sender_id]
            del input_handlers[sender_id]
            await event.reply('منتهي. ابدأ تسجيل جديد.', reply_markup=login_keyboard())
        except Exception as e:
            await event.reply(f'خطأ: {str(e)}')
        return

    if input_type == 'password':
        password = text
        state = login_states.get(sender_id)
        phone = state['phone']
        try:
            await user_client.sign_in(password=password)
            state['state'] = 'authorized'
            del input_handlers[sender_id]
            await event.reply('✅ 2FA ناجح! القائمة جاهزة.', reply_markup=main_keyboard())
        except Exception as e:
            await event.reply(f'كلمة خاطئة: {str(e)}. أعد الإرسال.')
        return

    if input_type == 'set_name':
        new_name = text.strip()
        if not new_name:
            await event.reply('اسم صالح مطلوب.', reply_markup=main_keyboard())
            del input_handlers[sender_id]
            return
        if not await is_authorized(sender_id):
            await event.reply('تسجيل أولاً!', reply_markup=login_keyboard())
            return
        try:
            await user_client(UpdateProfileRequest(first_name=new_name))
            await event.reply(f'✅ الاسم الجديد: {new_name}', reply_markup=main_keyboard())
            await user_client.disconnect()
            user_client = None
            del login_states[sender_id]
            del input_handlers[sender_id]
        except Exception as e:
            await event.reply(f'❌ خطأ: {str(e)}', reply_markup=main_keyboard())
        return

    if input_type == 'set_bio':
        new_bio = text.strip()
        if len(new_bio) > 170:
            await event.reply('سيرة طويلة (حد 170 حرف). أعد.', reply_markup=main_keyboard())
            del input_handlers[sender_id]
            return
        if not await is_authorized(sender_id):
            await event.reply('تسجيل أولاً!', reply_markup=login_keyboard())
            return
        try:
            await user_client(UpdateProfileRequest(about=new_bio))
            await event.reply(f'✅ السيرة الجديدة: {new_bio}', reply_markup=main_keyboard())
            await user_client.disconnect()
            user_client = None
            del login_states[sender_id]
            del input_handlers[sender_id]
        except Exception as e:
            await event.reply(f'❌ خطأ: {str(e)}', reply_markup=main_keyboard())
        return

    if input_type == 'set_photo':
        photo_path = text.strip()
        if not os.path.exists(photo_path):
            await event.reply(f'ملف "{photo_path}" غير موجود! ضعه في المجلد.', reply_markup=main_keyboard())
            del input_handlers[sender_id]
            return
        if not photo_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            await event.reply('فقط JPG/PNG.', reply_markup=main_keyboard())
            del input_handlers[sender_id]
            return
        if not await is_authorized(sender_id):
            await event.reply('تسجيل أولاً!', reply_markup=login_keyboard())
            return
        try:
            file = await user_client.upload_file(photo_path)
            await user_client(UploadProfilePhotoRequest(file))
            await event.reply(f'✅ الصورة الجديدة من "{photo_path}" (تكرار ممكن)!', reply_markup=main_keyboard())
            await user_client.disconnect()
            user_client = None
            del login_states[sender_id]
            del input_handlers[sender_id]
        except Exception as e:
            await event.reply(f'❌ خطأ: {str(e)} (حجم <10MB؟)', reply_markup=main_keyboard())
        return

    # إذا لم يكن إدخال، تجاهل أو أعد اللوحة
    await event.reply('استخدم الأزرار أو /start.', reply_markup=main_keyboard())

async def main():
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ البوت يعمل مع Inline Keyboards كاملة!")
    print("أرسل /start للبدء. جميع الأوامر بالأزرار.")
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
