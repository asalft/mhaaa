import asyncio
from telebot import TeleBot, types
from pyrogram import Client
from pyrogram.errors import FloodWait, PhoneCodeInvalid, SessionPasswordNeeded
import os
import logging

# إعداد اللوج
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# بيانات API تليجرام (احصل عليها من my.telegram.org)
api_id = 27227913
api_hash = 'ba805b182eca99224403dbcd5d4f50aa'

# رقم الهاتف للتسجيل (أدخل رقمك بالشكل الدولي، مثل +1234567890)
phone_number = "+9647776215642"  # غيّر هذا برقمك الحقيقي

bot_token = "8274634944:AAEOrWf0oBAgwaYcIRHAynVzDv43xqgXzec"
bot = TeleBot(bot_token)

client = Client("my_account", api_id=api_id, api_hash=api_hash, phone_number=phone_number)

# دالة لتشغيل العميل (ستطلب الكود إذا لزم الأمر عبر الـ terminal)
async def start_client():
    try:
        await client.start()
        logger.info("تم تسجيل الدخول بنجاح عبر رقم الهاتف")
    except PhoneCodeInvalid:
        logger.error("كود التحقق غير صحيح. أعد المحاولة")
    except SessionPasswordNeeded:
        password = input("أدخل كلمة مرور حسابك (2FA): ")
        await client.check_password(password)
        logger.info("تم تسجيل الدخول بنجاح بعد كلمة المرور")
    except Exception as e:
        logger.error(f"خطأ في تسجيل الدخول: {e}")

# دالة لإيقاف العميل
async def stop_client():
    await client.stop()

@bot.message_handler(commands=["start"])
def start(message):
    markup = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("تغيير معلومات الحساب", callback_data="change_info")],
        [types.InlineKeyboardButton("قنوات", callback_data="channels")],
        [types.InlineKeyboardButton("نشر في المجموعات", callback_data="post_to_groups")],
        [types.InlineKeyboardButton("📸 صورتي", callback_data="send_photo")]  # زر "صورتي"
    ])
    bot.send_message(message.chat.id, "مرحبًا! اختر من الخيارات التالية:", reply_markup=markup)

# دالة لإرسال صورة الملف الشخصي
@bot.callback_query_handler(func=lambda call: call.data == "send_photo")
def send_profile_photo(call):
    user_id = call.from_user.id
    try:
        # جلب الصورة الشخصية للمستخدم
        photos = bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            # إرسال آخر صورة شخصية للمستخدم
            bot.send_photo(call.message.chat.id, photos.photos[0][-1].file_id)
        else:
            bot.send_message(call.message.chat.id, "لم أتمكن من العثور على صورة شخصية لك.")
    except Exception as e:
        logger.error(f"Error getting profile photo: {e}")
        bot.send_message(call.message.chat.id, "حدث خطأ أثناء محاولة جلب الصورة.")

# متغيرات لتخزين البيانات المؤقتة
user_data = {}

@bot.callback_query_handler(func=lambda call: call.data == "post_to_groups")
def post_to_groups(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_content'}
    bot.send_message(call.message.chat.id, "أرسل لي محتوى الرسالة.")
    bot.register_next_step_handler(call.message, get_message_content)

def get_message_content(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    content = message.text
    user_data[user_id]['content'] = content
    user_data[user_id]['step'] = 'waiting_number'
    bot.send_message(message.chat.id, "أرسل لي عدد الرسائل.")
    bot.register_next_step_handler(message, lambda msg: get_number_of_messages(msg, content))

def get_number_of_messages(message, content):
    user_id = message.from_user.id
    if user_id not in user_data:
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    try:
        number_of_messages = int(message.text)
        user_data[user_id]['number_of_messages'] = number_of_messages
        user_data[user_id]['step'] = 'waiting_delay'
        bot.send_message(message.chat.id, "أرسل لي الثواني لتكرار الرسالة.")
        bot.register_next_step_handler(message, lambda msg: get_delay(msg, content, number_of_messages))
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال رقم صحيح لعدد الرسائل.")
        bot.register_next_step_handler(message, lambda msg: get_number_of_messages(msg, content))

def get_delay(message, content, number_of_messages):
    user_id = message.from_user.id
    if user_id not in user_data:
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    try:
        delay = int(message.text)
        user_data[user_id]['delay'] = delay
        user_data[user_id]['step'] = 'waiting_group'
        bot.send_message(message.chat.id, "أرسل لي معرف المجموعة (مثال: @groupname أو -100123456789).")
        bot.register_next_step_handler(message, lambda msg: post_messages(msg, content, number_of_messages, delay))
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال رقم صحيح للثواني.")
        bot.register_next_step_handler(message, lambda msg: get_delay(msg, content, number_of_messages))

def post_messages(message, content, number_of_messages, delay):
    user_id = message.from_user.id
    if user_id not in user_data:
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    group_id = message.text.strip()
    # تنظيف user_data بعد الانتهاء
    user_data.pop(user_id, None)
    
    # تشغيل المهمة في الخلفية
    asyncio.create_task(async_post_to_group(content, number_of_messages, delay, group_id, message.chat.id))

async def async_post_to_group(content, number_of_messages, delay, group_id, chat_id):
    success_count = 0
    try:
        for i in range(number_of_messages):
            try:
                await client.send_message(group_id, content)
                success_count += 1
                if i < number_of_messages - 1:  # لا تنتظر بعد آخر رسالة
                    await asyncio.sleep(delay)
                bot.send_message(chat_id, f"تم إرسال الرسالة {i+1}/{number_of_messages}")
            except FloodWait as e:
                logger.warning(f"Flood wait for {e.x} seconds")
                await asyncio.sleep(e.x)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                bot.send_message(chat_id, f"خطأ أثناء إرسال الرسالة {i+1}: {str(e)}")
                continue
        
        bot.send_message(chat_id, f"تم نشر {success_count} من أصل {number_of_messages} رسائل بنجاح.")
    except Exception as e:
        logger.error(f"General error in posting: {e}")
        bot.send_message(chat_id, f"خطأ عام أثناء النشر: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "change_info")
def change_info(call):
    markup = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("تغيير الاسم", callback_data="change_name")],
        [types.InlineKeyboardButton("تغيير اسم المستخدم", callback_data="change_username")],
        [types.InlineKeyboardButton("تغيير النبذة", callback_data="change_bio")],
        [types.InlineKeyboardButton("تغيير الصورة الشخصية", callback_data="change_photo")],
        [types.InlineKeyboardButton("تكرار الصورة", callback_data="repeat_photo")]  # زر جديد لتكرار الصورة
    ])
    bot.edit_message_text("اختر ما تريد تغييره:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

# معالج لتكرار الصورة
@bot.callback_query_handler(func=lambda call: call.data == "repeat_photo")
def repeat_photo(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_repeat_photo'}
    bot.send_message(call.message.chat.id, "أرسل لي الصورة لتكرار تعيينها.")
    bot.register_next_step_handler(call.message, handle_repeat_photo)

def handle_repeat_photo(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]['step'] != 'waiting_repeat_photo':
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    if message.photo:
        try:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # احفظ الصورة كملف مؤقت
            photo_path = f"temp_repeat_photo_{user_id}.jpg"
            with open(photo_path, "wb") as new_file:
                new_file.write(downloaded_file)

            user_data[user_id]['photo_path'] = photo_path
            user_data[user_id]['step'] = 'waiting_repeat_number'
            bot.send_message(message.chat.id, "أرسل عدد التكرارات.")
            bot.register_next_step_handler(message, get_repeat_number)
            
        except Exception as e:
            logger.error(f"Error handling repeat photo: {e}")
            bot.send_message(message.chat.id, f"حدث خطأ أثناء معالجة الصورة: {str(e)}")
    else:
        bot.send_message(message.chat.id, "لم يتم استلام صورة. الرجاء المحاولة مرة أخرى.")
        bot.register_next_step_handler(message, handle_repeat_photo)

def get_repeat_number(message):
    user_id = message.from_user.id
    if user_id not in user_data or 'photo_path' not in user_data[user_id]:
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    try:
        number = int(message.text)
        user_data[user_id]['number'] = number
        user_data[user_id]['step'] = 'waiting_repeat_delay'
        bot.send_message(message.chat.id, "أرسل الثواني بين كل تعيين (مثال: 5 لـ 5 ثواني).")
        bot.register_next_step_handler(message, get_repeat_delay)
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال رقم صحيح لعدد التكرارات.")
        bot.register_next_step_handler(message, get_repeat_number)

def get_repeat_delay(message):
    user_id = message.from_user.id
    if user_id not in user_data or 'photo_path' not in user_data[user_id]:
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    try:
        delay = int(message.text)
        photo_path = user_data[user_id]['photo_path']
        number = user_data[user_id]['number']
        
        # تشغيل المهمة في الخلفية
        asyncio.create_task(async_repeat_photo(photo_path, number, delay, message))
        
        # تنظيف user_data
        user_data.pop(user_id, None)
        
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال رقم صحيح للثواني.")
        bot.register_next_step_handler(message, get_repeat_delay)

async def async_repeat_photo(photo_path, number, delay, message):
    success_count = 0
    chat_id = message.chat.id
    try:
        for i in range(number):
            try:
                await client.set_profile_photo(photo=photo_path)
                success_count += 1
                if i < number - 1:
                    await asyncio.sleep(delay)
                bot.send_message(chat_id, f"تم تعيين الصورة {i+1}/{number}")
            except FloodWait as e:
                logger.warning(f"Flood wait for {e.x} seconds")
                await asyncio.sleep(e.x)
            except Exception as e:
                logger.error(f"Error setting photo: {e}")
                bot.send_message(chat_id, f"خطأ أثناء تعيين الصورة {i+1}: {str(e)}")
                continue
        
        bot.send_message(chat_id, f"تم تكرار تعيين الصورة {success_count} من أصل {number} مرة بنجاح.")
    except Exception as e:
        logger.error(f"General error in repeat photo: {e}")
        bot.send_message(chat_id, f"خطأ عام أثناء تكرار الصورة: {str(e)}")
    finally:
        # حذف الملف المؤقت
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except:
                pass

@bot.callback_query_handler(func=lambda call: call.data == "change_photo")
def change_photo(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_photo'}
    bot.send_message(call.message.chat.id, "أرسل لي الصورة الجديدة لتغييرها.")
    bot.register_next_step_handler(call.message, handle_photo)

def handle_photo(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]['step'] != 'waiting_photo':
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    if message.photo:
        try:
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # احفظ الصورة كملف مؤقت
            photo_path = f"temp_photo_{user_id}.jpg"
            with open(photo_path, "wb") as new_file:
                new_file.write(downloaded_file)

            # تشغيل المهمة في الخلفية
            asyncio.create_task(async_set_photo(photo_path, message))
            
            # تنظيف user_data
            user_data.pop(user_id, None)
            
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            bot.send_message(message.chat.id, f"حدث خطأ أثناء معالجة الصورة: {str(e)}")
    else:
        bot.send_message(message.chat.id, "لم يتم استلام صورة. الرجاء المحاولة مرة أخرى.")
        bot.register_next_step_handler(message, handle_photo)

async def async_set_photo(photo_path, message):
    try:
        await client.set_profile_photo(photo=photo_path)
        bot.send_message(message.chat.id, "تم تغيير الصورة الشخصية بنجاح.")
    except Exception as e:
        logger.error(f"Error setting profile photo: {e}")
        bot.send_message(message.chat.id, f"خطأ في تغيير الصورة: {str(e)}")
    finally:
        # حذف الملف المؤقت
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except:
                pass

@bot.callback_query_handler(func=lambda call: call.data == "change_name")
def change_name(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_name'}
    bot.send_message(call.message.chat.id, "أرسل لي الاسم الجديد.")
    bot.register_next_step_handler(call.message, set_name)

def set_name(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]['step'] != 'waiting_name':
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    # تشغيل المهمة في الخلفية
    asyncio.create_task(async_set_name(message.text, message))
    user_data.pop(user_id, None)

async def async_set_name(first_name, message):
    try:
        await client.update_profile(first_name=first_name)
        bot.send_message(message.chat.id, f"تم تغيير الاسم إلى: {first_name}")
    except Exception as e:
        logger.error(f"Error setting name: {e}")
        bot.send_message(message.chat.id, f"خطأ في تغيير الاسم: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "change_username")
def change_username(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_username'}
    bot.send_message(call.message.chat.id, "أرسل لي اسم المستخدم الجديد (بدون @).")
    bot.register_next_step_handler(call.message, set_username)

def set_username(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]['step'] != 'waiting_username':
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    username = message.text.strip().lstrip('@')  # إزالة @ إن وجد
    # تشغيل المهمة في الخلفية
    asyncio.create_task(async_set_username(username, message))
    user_data.pop(user_id, None)

async def async_set_username(username, message):
    try:
        await client.set_username(username)
        bot.send_message(message.chat.id, f"تم تغيير اسم المستخدم إلى @{username}")
    except Exception as e:
        logger.error(f"Error setting username: {e}")
        bot.send_message(message.chat.id, f"خطأ في تغيير اسم المستخدم: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "change_bio")
def change_bio(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_bio'}
    bot.send_message(call.message.chat.id, "أرسل لي النبذة الجديدة.")
    bot.register_next_step_handler(call.message, set_bio)

def set_bio(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]['step'] != 'waiting_bio':
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    # تشغيل المهمة في الخلفية
    asyncio.create_task(async_set_bio(message.text, message))
    user_data.pop(user_id, None)

async def async_set_bio(bio, message):
    try:
        await client.update_profile(bio=bio)
        bot.send_message(message.chat.id, f"تم تغيير النبذة إلى: {bio}")
    except Exception as e:
        logger.error(f"Error setting bio: {e}")
        bot.send_message(message.chat.id, f"خطأ في تغيير النبذة: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "channels")
def channels(call):
    markup = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("انضمام إلى قناة", callback_data="join_channel")],
        [types.InlineKeyboardButton("مغادرة من قناة", callback_data="leave_channel")]
    ])
    bot.edit_message_text("اختر ما تريد فعله في القنوات:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "join_channel")
def join_channel(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_join_channel'}
    bot.send_message(call.message.chat.id, "أرسل لي رابط القناة أو معرفها للانضمام إليها (مثال: @channelname أو t.me/channelname).")
    bot.register_next_step_handler(call.message, join_channel_action)

def join_channel_action(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]['step'] != 'waiting_join_channel':
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    channel = message.text.strip()
    # تشغيل المهمة في الخلفية
    asyncio.create_task(async_join_channel(channel, message))
    user_data.pop(user_id, None)

async def async_join_channel(channel, message):
    try:
        await client.join_chat(channel)
        bot.send_message(message.chat.id, f"تم الانضمام إلى القناة {channel} بنجاح.")
    except Exception as e:
        logger.error(f"Error joining channel: {e}")
        bot.send_message(message.chat.id, f"خطأ في الانضمام إلى القناة: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    user_id = call.from_user.id
    user_data[user_id] = {'step': 'waiting_leave_channel'}
    bot.send_message(call.message.chat.id, "أرسل لي رابط القناة أو معرفها للمغادرة منها (مثال: @channelname أو t.me/channelname).")
    bot.register_next_step_handler(call.message, leave_channel_action)

def leave_channel_action(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id]['step'] != 'waiting_leave_channel':
        bot.send_message(message.chat.id, "يرجى البدء من جديد باستخدام /start")
        return
    
    channel = message.text.strip()
    # تشغيل المهمة في الخلفية
    asyncio.create_task(async_leave_channel(channel, message))
    user_data.pop(user_id, None)

async def async_leave_channel(channel, message):
    try:
        await client.leave_chat(channel)
        bot.send_message(message.chat.id, f"تم مغادرة القناة {channel} بنجاح.")
    except Exception as e:
        logger.error(f"Error leaving channel: {e}")
        bot.send_message(message.chat.id, f"خطأ في المغادرة من القناة: {str(e)}")

# معالج للأخطاء
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    if user_id in user_data:
        step = user_data[user_id].get('step')
        if step == 'waiting_content':
            get_message_content(message)
            return
        elif step == 'waiting_number':
            get_number_of_messages(message, user_data[user_id].get('content', ''))
            return
        elif step == 'waiting_delay':
            content = user_data[user_id].get('content', '')
            number = user_data[user_id].get('number_of_messages', 1)
            get_delay(message, content, number)
            return
        elif step == 'waiting_group':
            content = user_data[user_id].get('content', '')
            number = user_data[user_id].get('number_of_messages', 1)
            delay = user_data[user_id].get('delay', 1)
            post_messages(message, content, number, delay)
            return
        elif step == 'waiting_photo':
            handle_photo(message)
            return
        elif step == 'waiting_repeat_photo':
            handle_repeat_photo(message)
            return
        elif step == 'waiting_repeat_number':
            get_repeat_number(message)
            return
        elif step == 'waiting_repeat_delay':
            get_repeat_delay(message)
            return
        elif step == 'waiting_name':
            set_name(message)
            return
        elif step == 'waiting_username':
            set_username(message)
            return
        elif step == 'waiting_bio':
            set_bio(message)
            return
        elif step == 'waiting_join_channel':
            join_channel_action(message)
            return
        elif step == 'waiting_leave_channel':
            leave_channel_action(message)
            return

async def main():
    """الدالة الرئيسية لتشغيل البوت"""
    try:
        # تشغيل عميل pyrogram
        await start_client()
        logger.info("Client started successfully")
        
        # تشغيل البوت
        logger.info("Bot started successfully")
        bot.polling(none_stop=True, interval=0, timeout=20)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await stop_client()
        logger.info("Client stopped")

if __name__ == "__main__":
    # تشغيل الدالة الرئيسية
    asyncio.run(main())
