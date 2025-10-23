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
BOT_TOKEN = '8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k'  # من @BotFather
API_ID = '27227913'  # من my.telegram.org (رقم)
API_HASH = 'ba805b182eca99224403dbcd5d4f50aa'  # من my.telegram.org (سلسلة)

# لـ Heroku:
# BOT_TOKEN = os.getenv('BOT_TOKEN')
# API_ID = int(os.getenv('API_ID'))
# API_HASH = os.getenv('API_HASH')

# إنشاء البوت
bot = TeleBot(BOT_TOKEN)

# Telethon عميل الحساب الشخصي
user_client = None
login_states = {}  # {user_id: {'state': 'phone|code|password|authorized', 'phone': '+number'}}
input_states = {}  # {user_id: 'set_name|set_bio|set_photo'}

def create_user_client():
    """إنشاء عميل Telethon جديد"""
    global user_client
    user_session = StringSession()
    user_client = TelegramClient(user_session, API_ID, API_HASH)
    return user_client

async def is_authorized(user_id):
    """التحقق من الصلاحية"""
    state = login_states.get(user_id)
    if state and state.get('state') == 'authorized' and user_client:
        try:
            if await user_client.is_connected() and await user_client.is_user_authorized():
                return True
        except:
            pass
    return False

# === لوحة الأزرار الرئيسية (Inline Keyboard) ===
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

# لوحة تسجيل الدخول
def login_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📱 أرسل رقم الهاتف", callback_data="login_phone"))
    markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel"))
    return markup

# لوحة الرمز
def code_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔢 أرسل رمز التحقق", callback_data="login_code"))
    markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel"))
    return markup

# لوحة كلمة المرور
def password_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔒 أرسل كلمة المرور", callback_data="login_password"))
    markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel"))
    return markup

# لوحة المساعدة
def help_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔐 كيفية التسجيل", callback_data="help_login"),
        types.InlineKeyboardButton("👤 الأوامر", callback_data="help_commands")
    )
    markup.add(types.InlineKeyboardButton("🖼️ عن الصور", callback_data="help_photo"))
    markup.add(types.InlineKeyboardButton("🔙 الرئيسية", callback_data="main_menu"))
    return markup

# === معالج الأوامر الأساسية ===
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        '✅ مرحبا! اضغط على الأزرار أدناه للتحكم في حسابك الشخصي.\n\n'
        'إذا كنت جديدًا، ابدأ بـ "تسجيل الدخول" للاتصال بحسابك.',
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        '❓ مساعدة:\n'
        'استخدم الأزرار أدناه للتنقل بين الأوامر.\n'
        'كل أمر يطلب الإدخال اللازم (اسم، سيرة، صورة).',
        reply_markup=help_keyboard()
    )

# === معالج الأزرار (Callback Queries) ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    # منع التحديث المتكرر
    bot.answer_callback_query(call.id)
    
    if data == 'main_menu':
        bot.edit_message_text(
            'القائمة الرئيسية:',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_keyboard()
        )
        return

    if data == 'close':
        if user_id in login_states:
            del login_states[user_id]
        if user_id in input_states:
            del input_states[user_id]
        if user_client and user_client.is_connected():
            asyncio.create_task(user_client.disconnect())
            global user_client
            user_client = None
        bot.edit_message_text('تم الإغلاق. أعد /start.', call.message.chat.id, call.message.message_id)
        return

    # تسجيل الدخول
    if data == 'login_start':
        if await is_authorized(user_id):
            bot.edit_message_text(
                '✅ أنت متصل بالفعل! استخدم الأزرار الأخرى.',
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_keyboard()
            )
            return
        bot.edit_message_text(
            '🔐 ابدأ تسجيل الدخول في حسابك الشخصي:',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=login_keyboard()
        )
        login_states[user_id] = {'state': 'login_start'}
        return

    if data == 'login_phone':
        state = login_states.get(user_id)
        if not state:
            bot.answer_callback_query(call.id, "ابدأ بـ /start أولاً")
            return
        login_states[user_id]['state'] = 'phone'
        bot.edit_message_text(
            '📱 أرسل رقم هاتفك الآن:\n'
            'مثال: +1234567890\n\n'
            '(أرسل الرقم في الرسالة التالية)',
            call.message.chat.id,
            call.message.message_id
        )
        input_states[user_id] = 'phone'
        return

    if data == 'login_code':
        state = login_states.get(user_id)
        if state and state['state'] == 'phone':
            # إذا كان في مرحلة الرقم، ابدأ إرسال الرمز
            phone = state['phone']
            if not phone:
                bot.answer_callback_query(call.id, "أرسل الرقم أولاً")
                return
            create_user_client()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(user_client.connect())
                loop.run_until_complete(user_client.send_code_request(phone))
                login_states[user_id]['state'] = 'code'
                bot.edit_message_text(
                    f'✅ تم إرسال رمز التحقق إلى {phone}!\n\n'
                    'أرسل الرمز (5 أرقام) في الرسالة التالية:',
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=code_keyboard()
                )
                input_states[user_id] = 'code'
            except Exception as e:
                bot.edit_message_text(
                    f'❌ خطأ في إرسال الرمز: {str(e)}',
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=login_keyboard()
                )
            finally:
                loop.close()
            return
        # إذا كان في مرحلة أخرى، اطلب الرمز
        input_states[user_id] = 'code'
        bot.edit_message_text(
            '🔢 أرسل رمز التحقق (5 أرقام):',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=code_keyboard()
        )
        return

    if data == 'login_password':
        state = login_states.get(user_id)
        if state and state['state'] == 'code':
            login_states[user_id]['state'] = 'password'
            bot.edit_message_text(
                '🔒 كلمة مرور 2FA مطلوبة.\n'
                'أرسلها في الرسالة التالية:',
                call.message.chat.id,
                call.message.message_id,
                reply_markup=password_keyboard()
            )
            input_states[user_id] = 'password'
            return
        input_states[user_id] = 'password'
        bot.edit_message_text(
            '🔒 أرسل كلمة مرور 2FA:',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=password_keyboard()
        )
        return

    # أوامر التحكم
    if data == 'set_name_btn':
        if not await is_authorized(user_id):
            bot.edit_message_text(
                '❌ قم بتسجيل الدخول أولاً!',
                call.message.chat.id,
                call.message.message_id,
                reply_markup=login_keyboard()
            )
            return
        bot.edit_message_text(
            '👤 أرسل الاسم الجديد في الرسالة التالية:',
            call.message.chat.id,
            call.message.message_id
        )
        input_states[user_id] = 'set_name'
        return

    if data == 'set_bio_btn':
        if not await is_authorized(user_id):
            bot.edit_message_text(
                '❌ قم بتسجيل الدخول أولاً!',
                call.message.chat.id,
                call.message.message_id,
                reply_markup=login_keyboard()
            )
            return
        bot.edit_message_text(
            '📝 أرسل السيرة الذاتية الجديدة (حد أقصى 170 حرف):',
            call.message.chat.id,
            call.message.message_id
        )
        input_states[user_id] = 'set_bio'
        return

    if data == 'set_photo_btn':
        if not await is_authorized(user_id):
            bot.edit_message_text(
                '❌ قم بتسجيل الدخول أولاً!',
                call.message.chat.id,
                call.message.message_id,
                reply_markup=login_keyboard()
            )
            return
        bot.edit_message_text(
            '🖼️ أرسل مسار الصورة في الرسالة التالية:\n'
            'مثال: photo.jpg\n'
            '(ضع الصورة في مجلد الكود - يمكن تكرار التغيير):',
            call.message.chat.id,
            call.message.message_id
        )
        input_states[user_id] = 'set_photo'
        return

    if data == 'status_btn':
        if await is_authorized(user_id):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(user_client.connect())
                me = loop.run_until_complete(user_client.get_me())
                status_text = (
                    f'✅ الحساب متصل!\n\n'
                    f'👤 الاسم: {me.first_name} {me.last_name or ""}\n'
                    f'🆔 الـ ID: {me.id}\n'
                    f'📛 اليوزرنيم: @{me.username or "غير محدد"}\n'
                    f'📅 تاريخ الإنشاء: {me.date}\n\n'
                    f'يمكنك الآن تغيير الاسم، السيرة، أو الصورة.'
                )
                bot.edit_message_text(
                    status_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=main_keyboard()
                )
            except Exception as e:
                bot.edit_message_text(
                    f'❌ خطأ في قراءة الحساب: {str(e)}',
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=login_keyboard()
                )
            finally:
                loop.close()
        else:
            bot.edit_message_text(
                '❌ غير متصل بالحساب. اضغط "تسجيل الدخول" أولاً.',
                call.message.chat.id,
                call.message.message_id,
                reply_markup=login_keyboard()
            )
        return

    if data == 'help_btn':
        bot.edit_message_text(
            '❓ المساعدة:',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=help_keyboard()
        )
        return

    # مساعدة فرعية
    if data == 'help_login':
        bot.edit_message_text(
            '🔐 كيفية التسجيل:\n\n'
            '1️⃣ اضغط "تسجيل الدخول" → "أرسل رقم الهاتف"\n'
            '2️⃣ أرسل رقمك مع + (مثال: +1234567890)\n'
            '3️⃣ سيرسل رمز → اضغط "أرسل رمز التحقق" → أرسل 5 أرقام\n'
            '4️⃣ إذا لديك 2FA: "أرسل كلمة المرور" → أرسل الكلمة\n\n'
            '✅ التسجيل مؤقت (لا يحفظ جلسة) للأمان.',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=help_keyboard()
        )
        return

    if data == 'help_commands':
        bot.edit_message_text(
            '👤 الأوامر المتاحة:\n\n'
            '👤 **تغيير الاسم:**\n'
            'اضغط "تغيير الاسم" → أرسل الاسم الجديد\n\n'
            '📝 **تغيير السيرة:**\n'
            'اضغط "تغيير السيرة" → أرسل النص (حد 170 حرف)\n\n'
            '🖼️ **تغيير الصورة:**\n'
            '1. ضع الصورة (JPG/PNG) في مجلد الكود\n'
            '2. اضغط "تغيير الصورة" → أرسل المسار (مثال: photo.jpg)\n'
            '3. يمكن تكرار العملية مع صور مختلفة\n\n'
            '⚠️ جميع التغييرات فورية وتظهر في ملفك الشخصي.',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=help_keyboard()
        )
        return

    if data == 'help_photo':
        bot.edit_message_text(
            '🖼️ تفاصيل تغيير الصورة:\n\n'
            '✅ **كيفية العمل:**\n'
            '- ضع ملف الصورة في نفس مجلد الكود\n'
            '- الصيغ: JPG, JPEG, PNG\n'
            '- الحجم: أقل من 10MB\n\n'
            '📝 **الخطوات:**\n'
            '1. اضغط "تغيير الصورة"\n'
            '2. أرسل اسم الملف (مثال: photo1.jpg)\n'
            '3. الصورة الرئيسية تتحدث فورًا\n'
            '4. كرر مع صورة أخرى (photo2.jpg)\n\n'
            '🔄 **التكرار:** يمكن تغيير الصورة عدة مرات دون مشاكل\n'
            'الصورة السابقة لا تُحذف تلقائيًا (يمكن إضافتها لاحقًا)',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=help_keyboard()
        )
        return

    if data == 'cancel':
        if user_id in login_states:
            del login_states[user_id]
        if user_id in input_states:
            del input_states[user_id]
        if user_client and user_client.is_connected():
            asyncio.create_task(user_client.disconnect())
            global user_client
            user_client = None
        bot.edit_message_text(
            '❌ تم إلغاء العملية.',
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_keyboard()
        )
        return

# === معالج الرسائل النصية (للإدخال) ===
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    input_type = input_states.get(user_id)

    if input_type == 'phone':
        phone = text
        if not phone.startswith('+'):
            bot.reply_to(message, 
                '❌ الرقم يجب أن يبدأ بـ + (مثال: +1234567890)\nأعد الإرسال:',
                reply_markup=login_keyboard()
            )
            return
        
        login_states[user_id] = {'state': 'code', 'phone': phone}
        create_user_client()
        
        # تشغيل Telethon في thread منفصل
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(user_client.connect())
            loop.run_until_complete(user_client.send_code_request(phone))
            bot.reply_to(
                message,
                f'✅ تم إرسال رمز التحقق إلى {phone}!\n\n'
                'أرسل الرمز (5 أرقام) في الرسالة التالية:',
                reply_markup=code_keyboard()
            )
            input_states[user_id] = 'code'
        except PhoneNumberInvalidError:
            bot.reply_to(
                message,
                '❌ رقم هاتف غير صالح. تأكد من التنسيق الدولي:',
                reply_markup=login_keyboard()
            )
        except FloodWaitError as e:
            bot.reply_to(
                message,
                f'⏳ حد من Telegram: انتظر {e.seconds // 60} دقيقة:',
                reply_markup=login_keyboard()
            )
        except Exception as e:
            bot.reply_to(
                message,
                f'❌ خطأ في إرسال الرمز: {str(e)}',
                reply_markup=login_keyboard()
            )
        finally:
            loop.close()
        return

    if input_type == 'code':
        code = text
        if len(code) != 5 or not code.isdigit():
            bot.reply_to(
                message,
                '❌ الرمز يجب أن يكون 5 أرقام فقط.\nأعد الإرسال:',
                reply_markup=code_keyboard()
            )
            return
        
        state = login_states.get(user_id)
        phone = state['phone']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(user_client.sign_in(phone=phone, code=int(code)))
            state['state'] = 'authorized'
            del input_states[user_id]
            bot.reply_to(
                message,
                '✅ تم تسجيل الدخول بنجاح!\n'
                'الحساب الآن متصل. استخدم القائمة الرئيسية:',
                reply_markup=main_keyboard()
            )
        except SessionPasswordNeededError:
            state['state'] = 'password'
            bot.reply_to(
                message,
                '🔒 كلمة مرور 2FA مطلوبة.\nأرسلها في الرسالة التالية:',
                reply_markup=password_keyboard()
            )
            input_states[user_id] = 'password'
        except PhoneCodeInvalidError:
            bot.reply_to(
                message,
                '❌ الرمز غير صحيح. تحقق وأعد الإرسال:',
                reply_markup=code_keyboard()
            )
        except PhoneCodeExpiredError:
            del login_states[user_id]
            del input_states[user_id]
            bot.reply_to(
                message,
                '❌ الرمز منتهي الصلاحية.\nابدأ تسجيل جديد:',
                reply_markup=login_keyboard()
            )
        except Exception as e:
            bot.reply_to(
                message,
                f'❌ خطأ في الرمز: {str(e)}\nأعد المحاولة:',
                reply_markup=code_keyboard()
            )
        finally:
            loop.close()
        return

    if input_type == 'password':
        password = text
        state = login_states.get(user_id)
        phone = state['phone']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(user_client.sign_in(password=password))
            state['state'] = 'authorized'
            del input_states[user_id]
            bot.reply_to(
                message,
                '✅ تم تسجيل الدخول مع 2FA بنجاح!\n'
                'الحساب جاهز للاستخدام:',
                reply_markup=main_keyboard()
            )
        except Exception as e:
            bot.reply_to(
                message,
                f'❌ كلمة المرور غير صحيحة: {str(e)}\nأعد الإرسال:',
                reply_markup=password_keyboard()
            )
        finally:
            loop.close()
        return

    if input_type == 'set_name':
        new_name = text.strip()
        if not new_name:
            bot.reply_to(
                message,
                '❌ يجب إرسال اسم صالح:',
                reply_markup=main_keyboard()
            )
            del input_states[user_id]
            return
        
        if not await is_authorized(user_id):
            bot.reply_to(
                message,
                '❌ قم بتسجيل الدخول أولاً!',
                reply_markup=login_keyboard()
            )
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(user_client.connect())
            loop.run_until_complete(user_client(UpdateProfileRequest(first_name=new_name)))
            bot.reply_to(
                message,
                f'✅ تم تغيير الاسم إلى: **{new_name}**\n\n'
                'التغيير فوري في ملفك الشخصي!',
                reply_markup=main_keyboard(),
                parse_mode='Markdown'
            )
            # فصل الاتصال للأمان
            loop.run_until_complete(user_client.disconnect())
            global user_client
            user_client = None
            del login_states[user_id]
            del input_states[user_id]
        except Exception as e:
            bot.reply_to(
                message,
                f'❌ خطأ في تغيير الاسم: {str(e)}\n'
                'تأكد من الاتصال وأعد المحاولة:',
                reply_markup=main_keyboard()
            )
        finally:
            loop.close()
        return

    if input_type == 'set_bio':
        new_bio = text.strip()
        if len(new_bio) > 170:
            bot.reply_to(
                message,
                '❌ السيرة طويلة جداً (الحد الأقصى 170 حرف).\n'
                'أرسل سيرة أقصر:',
                reply_markup=main_keyboard()
            )
            del input_states[user_id]
            return
        
        if not await is_authorized(user_id):
            bot.reply_to(
                message,
                '❌ قم بتسجيل الدخول أولاً!',
                reply_markup=login_keyboard()
            )
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(user_client.connect())
            loop.run_until_complete(user_client(UpdateProfileRequest(about=new_bio)))
            bot.reply_to(
                message,
                f'✅ تم تغيير السيرة الذاتية إلى:\n\n**{new_bio}**\n\n'
                'التغيير فوري ومرئي للآخرين!',
                reply_markup=main_keyboard(),
                parse_mode='Markdown'
            )
            loop.run_until_complete(user_client.disconnect())
            global user_client
            user_client = None
            del login_states[user_id]
            del input_states[user_id]
        except Exception as e:
            bot.reply_to(
                message,
                f'❌ خطأ في تغيير السيرة: {str(e)}',
                reply_markup=main_keyboard()
            )
        finally:
            loop.close()
        return

    if input_type == 'set_photo':
        photo_path = text.strip()
        if not os.path.exists(photo_path):
            bot.reply_to(
                message,
                f'❌ الملف "{photo_path}" غير موجود!\n\n'
                'تأكد من:\n'
                '• وضع الصورة في مجلد الكود\n'
                '• كتابة المسار الصحيح (مثال: photo.jpg)\n\n'
                'أرسل المسار مرة أخرى:',
                reply_markup=main_keyboard()
            )
            del input_states[user_id]
            return
        
        if not photo_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            bot.reply_to(
                message,
                '❌ يدعم فقط صيغ JPG، JPEG، PNG.\n'
                'أرسل مسار صورة صالح:',
                reply_markup=main_keyboard()
            )
            del input_states[user_id]
            return
        
        if not await is_authorized(user_id):
            bot.reply_to(
                message,
                '❌ قم بتسجيل الدخول أولاً!',
                reply_markup=login_keyboard()
            )
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(user_client.connect())
            file = loop.run_until_complete(user_client.upload_file(photo_path))
            loop.run_until_complete(user_client(UploadProfilePhotoRequest(file)))
            
            bot.reply_to(
                message,
                f'✅ تم تغيير الصورة الشخصية بنجاح!\n\n'
                f'📁 الملف: **{photo_path}**\n'
                f'🔄 التحديث فوري في ملفك الشخصي\n\n'
                f'💡 يمكنك تكرار العملية مع صورة أخرى!',
                reply_markup=main_keyboard(),
                parse_mode='Markdown'
            )
            
            # فصل للأمان
            loop.run_until_complete(user_client.disconnect())
            global user_client
            user_client = None
            del login_states[user_id]
            del input_states[user_id]
            
        except Exception as e:
            bot.reply_to(
                message,
                f'❌ خطأ في تغيير الصورة: {str(e)}\n\n'
                'تأكد من:\n'
                '• حجم الصورة أقل من 10MB\n'
                '• الصورة في المجلد الصحيح\n'
                '• الاتصال نشط',
                reply_markup=main_keyboard()
            )
        finally:
            loop.close()
        return

    # إذا لم يكن إدخال، أعد إلى القائمة الرئيسية
    bot.reply_to(
        message,
        'للتحكم في الحساب، استخدم الأزرار في القائمة الرئيسية أو /start',
        reply_markup=main_keyboard()
    )

# === تشغيل البوت ===
if __name__ == '__main__':
    print("🚀 البوت يعمل الآن مع telebot + Telethon!")
    print("جميع الأوامر inline مع Inline Keyboards كاملة")
    print("اضغط Ctrl+C للإيقاف")
    
    # تشغيل telebot
    bot.infinity_polling(none_stop=True, interval=0, timeout=20)
