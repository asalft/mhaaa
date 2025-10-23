from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.types import InputPhoto
import os

# بيانات الاتصال (استبدلها ببياناتك الحقيقية)
api_id = '27227913'  # رقم API ID من my.telegram.org
api_hash = 'ba805b182eca99224403dbcd5d4f50aa'  # سلسلة API Hash
session_file = 'my_session.txt'  # اسم ملف الجلسة (مثل my_account.session) أو استخدم string إذا كان لديك

# إنشاء العميل
client = TelegramClient(session_file, api_id, api_hash)

@client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    help_text = """
أوامر متاحة:
- /set_name <الاسم الجديد> : تغيير الاسم الأول
- /set_bio <السيرة الجديدة> : تغيير السيرة الذاتية
- /set_photo <مسار الصورة> : تغيير الصورة (مثال: photo.jpg)
- /help : عرض هذه القائمة

أرسل هذه الأوامر في رسالة خاصة مع نفس الحساب.
    """
    await event.reply(help_text)

@client.on(events.NewMessage(pattern='/set_name (.+)'))
async def set_name(event):
    new_name = event.pattern_match.group(1).strip()
    try:
        await client(UpdateProfileRequest(first_name=new_name))
        await event.reply(f'تم تغيير الاسم إلى: {new_name}')
    except Exception as e:
        await event.reply(f'خطأ في تغيير الاسم: {str(e)}')

@client.on(events.NewMessage(pattern='/set_bio (.+)'))
async def set_bio(event):
    new_bio = event.pattern_match.group(1).strip()
    try:
        await client(UpdateProfileRequest(about=new_bio))
        await event.reply(f'تم تغيير السيرة إلى: {new_bio}')
    except Exception as e:
        await event.reply(f'خطأ في تغيير السيرة: {str(e)}')

@client.on(events.NewMessage(pattern='/set_photo (.+)'))
async def set_photo(event):
    photo_path = event.pattern_match.group(1).strip()
    if not os.path.exists(photo_path):
        await event.reply('الملف غير موجود! تأكد من مسار الصورة.')
        return
    try:
        file = await client.upload_file(photo_path)
        await client(UploadProfilePhotoRequest(file))
        await event.reply('تم تغيير الصورة بنجاح!')
    except Exception as e:
        await event.reply(f'خطأ في تغيير الصورة: {str(e)}')

async def main():
    await client.start()  # سيقوم بتسجيل الدخول تلقائياً إذا كانت الجلسة موجودة
    print("البوت يعمل الآن! أرسل الأوامر في رسالة خاصة.")
    print("اضغط Ctrl+C للإيقاف.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
