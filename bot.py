
import asyncio
from telebot import TeleBot, types
from pyrogram import Client
from pyrogram.errors import FloodWait
import os

api_id = 27227913
api_hash = 'ba805b182eca99224403dbcd5d4f50aa'
session_string = "1AZWarzYBu3uqo-jioOzSFVj_tIgCcnLRmAaI0CGqrQ0_1rVr9iR333lxIJgpR956IVccBBcmhXyPGHdGppFD-1nV19gikNvhkLwNF1VCKlB72IaFd3tbYnLIK5Pn92a7InaF3SvrL0WUPTsmUY8nsAyTHHUkR07ZYzOZU3E1A19RIhov4wa_O09DS8M2tbTUVSezlHo5ip4VwairQa_GrpMl0eB9TgWfG215gXM5GQfcMnGpLVBLPPK2fyacVm3aUU1gVyX3qWz2r2OzOOnbC_ub-ZDLgfVlMHiXrCgUqjSlVxHVMiLlvhhprTV7v9PwCupL8mW-kjxkeFiUNGqWW3l-AuAVDdU="

bot_token = "8274634944:AAEOrWf0oBAgwaYcIRHAynVzDv43xqgXzec"
bot = TeleBot(bot_token)

client = Client("my_account", api_id=api_id, api_hash=api_hash, session_string=session_string)
client.start()

loop = asyncio.get_event_loop()

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
        photos = bot.get_user_profile_photos(user_id)
        if photos.total_count > 0:
            # إرسال آخر صورة شخصية للمستخدم
            bot.send_photo(call.message.chat.id, photos.photos[0][-1].file_id)
        else:
            bot.send_message(call.message.chat.id, "لم أتمكن من العثور على صورة شخصية لك.")
    except Exception as e:
        bot.send_message(call.message.chat.id, "حدث خطأ أثناء محاولة جلب الصورة.")

@bot.callback_query_handler(func=lambda call: call.data == "post_to_groups")
def post_to_groups(call):
    bot.send_message(call.message.chat.id, "أرسل لي محتوى الرسالة.")
    bot.register_next_step_handler(call.message, get_message_content)

def get_message_content(message):
    content = message.text
    bot.send_message(message.chat.id, "أرسل لي عدد الرسائل.")
    bot.register_next_step_handler(message, lambda msg: get_number_of_messages(msg, content))

def get_number_of_messages(message, content):
    try:
        number_of_messages = int(message.text)
        bot.send_message(message.chat.id, "أرسل لي الثواني لتكرار الرسالة.")
        bot.register_next_step_handler(message, lambda msg: get_delay(msg, content, number_of_messages))
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال رقم صحيح لعدد الرسائل.")
        bot.register_next_step_handler(message, lambda msg: get_number_of_messages(msg, content))

def get_delay(message, content, number_of_messages):
    try:
        delay = int(message.text)
        bot.send_message(message.chat.id, "أرسل لي معرف المجموعة.")
        bot.register_next_step_handler(message, lambda msg: post_messages(msg, content, number_of_messages, delay))
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال رقم صحيح للثواني.")
        bot.register_next_step_handler(message, lambda msg: get_delay(msg, content, number_of_messages))

def post_messages(message, content, number_of_messages, delay):
    group_id = message.text
    loop.run_until_complete(async_post_to_group(content, number_of_messages, delay, group_id))

async def async_post_to_group(content, number_of_messages, delay, group_id):
    for _ in range(number_of_messages):
        try:
            await client.send_message(group_id, content)
            await asyncio.sleep(delay)
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ أثناء نشر الرسالة: {e}")
            return
    bot.send_message(message.chat.id, "تم نشر الرسائل بنجاح.")

@bot.callback_query_handler(func=lambda call: call.data == "change_info")
def change_info(call):
    markup = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("تغيير الاسم", callback_data="change_name")],
        [types.InlineKeyboardButton("تغيير اسم المستخدم", callback_data="change_username")],
        [types.InlineKeyboardButton("تغيير النبذة", callback_data="change_bio")],
        [types.InlineKeyboardButton("تغيير الصورة الشخصية", callback_data="change_photo")]
    ])
    bot.edit_message_text("اختر ما تريد تغييره:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "change_photo")
def change_photo(call):
    bot.send_message(call.message.chat.id, "أرسل لي الصورة الجديدة لتغييرها.")
    bot.register_next_step_handler(call.message, handle_photo)

def handle_photo(message):
    if message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # احفظ الصورة كملف مؤقت
        with open("temp_photo.jpg", "wb") as new_file:
            new_file.write(downloaded_file)

        # تحديث صورة الملف الشخصي
        loop.run_until_complete(async_set_photo("temp_photo.jpg", message))

        # احذف الملف المؤقت بعد الاستخدام
        os.remove("temp_photo.jpg")
    else:
        bot.send_message(message.chat.id, "لم يتم استلام صورة. الرجاء المحاولة مرة أخرى.")

async def async_set_photo(photo_path, message):
    try:
        with client:
            await client.set_profile_photo(photo=photo_path)
        bot.send_message(message.chat.id, "تم تغيير الصورة الشخصية بنجاح.")
    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "change_name")
def change_name(call):
    bot.send_message(call.message.chat.id, "أرسل لي الاسم الجديد.")
    bot.register_next_step_handler(call.message, set_name)

def set_name(message):
    loop.run_until_complete(async_set_name(message))

async def async_set_name(message):
    with client:
        await client.update_profile(first_name=message.text)
    bot.send_message(message.chat.id, f"تم تغيير الاسم إلى {message.text}")

@bot.callback_query_handler(func=lambda call: call.data == "change_username")
def change_username(call):
    bot.send_message(call.message.chat.id, "أرسل لي اسم المستخدم الجديد.")
    bot.register_next_step_handler(call.message, set_username)

def set_username(message):
    loop.run_until_complete(async_set_username(message))

async def async_set_username(message):
    try:
        await client.set_username(message.text)
        bot.send_message(message.chat.id, f"تم تغيير اسم المستخدم إلى {message.text}")
    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "change_bio")
def change_bio(call):
    bot.send_message(call.message.chat.id, "أرسل لي النبذة الجديدة.")
    bot.register_next_step_handler(call.message, set_bio)

def set_bio(message):
    loop.run_until_complete(async_set_bio(message))

async def async_set_bio(message):
    try:
        await client.update_profile(bio=message.text)
        bot.send_message(message.chat.id, f"تم تغيير النبذة إلى {message.text}")
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "channels")
def channels(call):
    markup = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("انضمام إلى قناة", callback_data="join_channel")],
        [types.InlineKeyboardButton("مغادرة من قناة", callback_data="leave_channel")]
    ])
    bot.edit_message_text("اختر ما تريد فعله في القنوات:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "join_channel")
def join_channel(call):
    bot.send_message(call.message.chat.id, "أرسل لي رابط القناة للانضمام إليها.")
    bot.register_next_step_handler(call.message, join_channel_action)

def join_channel_action(message):
    loop.run_until_complete(async_join_channel(message))

async def async_join_channel(message):
    try:
        await client.join_chat(message.text)
        bot.send_message(message.chat.id, f"تم الانضمام إلى القناة {message.text}")
    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    bot.send_message(call.message.chat.id, "أرسل لي رابط القناة للمغادرة منها.")
    bot.register_next_step_handler(call.message, leave_channel_action)

def leave_channel_action(message):
    loop.run_until_complete(async_leave_channel(message))

async def async_leave_channel(message):
    try:
        await client.leave_chat(message.text)
        bot.send_message(message.chat.id, f"تم مغادرة القناة {message.text}")
    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")

if __name__ == "__main__":
    bot.polling(none_stop=True)
