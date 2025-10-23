import os
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest

# بيانات API
API_ID = 27227913  # ضع API_ID الخاص بك
API_HASH = 'ba805b182eca99224403dbcd5d4f50aa'  # ضع API_HASH الخاص بك
BOT_TOKEN = '8396394703:AAFaGheS7ExQG7IDQJQRbkonMf66Id5Y'  # ضع توكن البوت الخاص بك

user_sessions = {}

# عميل البوت
bot_client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id

    if user_id in user_sessions and user_sessions[user_id].get('logged_in'):
        await show_main_menu(event)
    else:
        await show_login_menu(event)

async def show_login_menu(event):
    buttons = [
        [Button.inline("📱 تسجيل الدخول", b"login")],
        [Button.inline("ℹ️ مساعدة", b"help")]
    ]
    await event.reply("🔒 **مرحباً بك في بوت التحكم بالحساب**\n\nلتتمكن من استخدام البوت، تحتاج لتسجيل الدخول إلى حسابك Telegram\n\nانقر على الزر أدناه للبدء:", buttons=buttons)

async def show_main_menu(event):
    buttons = [
        [Button.inline("🖼 تغيير الصورة", b"change_profile"), Button.inline("✏️ تغيير الاسم", b"change_name")],
        [Button.inline("🔄 تغيير متكرر", b"auto_change"), Button.inline("📊 معلومات الحساب", b"account_info")],
        [Button.inline("🚪 تسجيل الخروج", b"logout")]
    ]
    await event.reply("🎮 **لوحة التحكم الرئيسية**\n\nاختر الأمر الذي تريد تنفيذه:", buttons=buttons)

@bot_client.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data.decode('utf-8')
    
    if data == "login":
        await start_login_process(event)
    elif data == "help":
        await show_help(event)
    elif data == "change_profile":
        await change_profile_start(event)
    elif data == "change_name":
        await change_name_start(event)
    elif data == "auto_change":
        await auto_change_start(event)
    elif data == "account_info":
        await account_info(event)
    elif data == "logout":
        await logout_user(event)
    elif data.startswith("confirm_"):
        await handle_confirmation(event, data)

async def start_login_process(event):
    user_id = event.sender_id
    user_sessions[user_id] = {'step': 'phone', 'client': None, 'logged_in': False}

    await event.edit("📱 **مرحلة إدخال رقم الهاتف**\n\nالرجاء إرسال رقم هاتفك مع مفتاح الدولة\n\nمثال: +201234567890", buttons=[[Button.inline("🔙 رجوع", b="help")]])

async def show_help(event):
    await event.edit("ℹ️ تعليمات استخدام البوت\n\n• البوت يسمح لك بالتحكم في حسابك الشخصي\n• تحتاج لتسجيل الدخول أولاً باستخدام رقم الهاتف\n• يمكنك تغيير الصورة والاسم بشكل يدوي أو تلقائي\n• بيانات التسجيل محفوظة بشكل آمن\n\nانقر على زر تسجيل الدخول للبدء:", buttons=[[Button.inline("📱 تسجيل الدخول", b="login")]])

@bot_client.on(events.NewMessage)
async def handle_messages(event):
    user_id = event.sender_id

    # تجاهل الرسائل من القنوات والمجموعات  
    if not event.is_private:  
        return  

    # إذا كان المستخدم في عملية تسجيل دخول  
    if user_id in user_sessions and not user_sessions[user_id].get('logged_in'):
        await handle_login_steps(event)
        
    # إذا كان المستخدم مسجل دخوله  
    if user_id in user_sessions and user_sessions[user_id].get('logged_in'):
        # معالجة الأوامر النصية  
        if event.text.startswith('/'):
            return
        
        # إذا كان في عملية تغيير الصورة
        if user_sessions[user_id].get('waiting_for_photo'):
            await handle_photo_upload(event)
        # إذا كان في عملية تغيير الاسم 
        elif user_sessions[user_id].get('waiting_for_name'):
            await handle_name_change(event)

async def handle_login_steps(event):
    user_id = event.sender_id
    session_data = user_sessions[user_id]
    step = session_data['step']

    try:
        if step == 'phone':
            phone = event.text.strip()
            
            if not phone.startswith('+'):
                await event.reply("❌ الرجاء إدخال رقم الهاتف مع مفتاح الدولة بدءاً بـ +")  
                return
            
            session_data['client'] = TelegramClient(f'sessions/{user_id}_session', API_ID, API_HASH)
            client = session_data['client']
            
            await client.connect()
            await client.send_code_request(phone)
            
            session_data['phone'] = phone
            session_data['step'] = 'code'

            await event.reply("🔐 **مرحلة إدخال كود التحقق**\n\nتم إرسال كود التحقق إلى حسابك\nالرجاء إرسال الكود مع المسافات بين الأرقام\n\nمثال: 1 2 3 4 5")
            
        elif step == 'code':
            code = event.text.strip().replace(' ', '')

            if not code.isdigit():
                await event.reply("❌ الرجاء إدخال كود تحقق صحيح (أرقام فقط)")
                return
            
            client = session_data['client']

            try:
                await client.sign_in(session_data['phone'], code)
                
                session_data['logged_in'] = True
                me = await client.get_me()
                
                session_data['user_info'] = {
                    'first_name': me.first_name,
                    'username': me.username,
                    'phone': me.phone
                }

                await event.reply(f"✅ **تم تسجيل الدخول بنجاح!**\n\n👤 الاسم: {me.first_name or 'غير محدد'}\n📞 الهاتف: {me.phone}\n🔗 اليوزر: @{me.username or 'غير محدد'}\n\nيمكنك الآن استخدام جميع ميزات البوت")
                await show_main_menu(event)
                
            except Exception as e:
                if "two-steps" in str(e):
                    session_data['step'] = 'password'
                    await event.reply("🔒 **مرحلة التحقق بخطوتين**\n\nحسابك محمي بكلمة مرور ثنائية\nالرجاء إرسال كلمة المرور:")
                else:
                    await event.reply(f"❌ خطأ في التسجيل: {str(e)}")
                    await cleanup_session(user_id)

        elif step == 'password':
            password = event.text.strip()
            client = session_data['client']

            try:
                await client.sign_in(password=password)
                session_data['logged_in'] = True

                me = await client.get_me()
                session_data['user_info'] = {
                    'first_name': me.first_name,
                    'username': me.username,
                    'phone': me.phone
                }

                await event.reply(f"✅ **تم تسجيل الدخول بنجاح!**\n\n👤 الاسم: {me.first_name or 'غير محدد'}\n📞 الهاتف: {me.phone}\n🔗 اليوزر: @{me.username or 'غير محدد'}\n\nيمكنك الآن استخدام جميع ميزات البوت")
                await show_main_menu(event)
                
            except Exception as e:
                await event.reply(f"❌ خطأ في كلمة المرور: {str(e)}")
                await cleanup_session(user_id)
    
    except Exception as e:
        await event.reply(f"❌ حدث خطأ أثناء التسجيل: {str(e)}")
        await cleanup_session(user_id)

async def change_profile_start(event):
    user_id = event.sender_id

    if not await check_user_login(user_id):  
        await event.answer("❌ الرجاء تسجيل الدخول أولاً", alert=True)  
        return  

    user_sessions[user_id]['waiting_for_photo'] = True  

    await event.edit("🖼 **تغيير صورة الملف الشخصي**\n\nالرجاء إرسال الصورة التي تريد وضعها كصورة ملفك الشخصي:", buttons=[[Button.inline("🔙 رجوع", b="help")]])

async def handle_photo_upload(event):
    user_id = event.sender_id

    if not event.media:  
        await event.reply("❌ الرجاء إرسال صورة صحيحة")  
        return  

    try:  
        client = user_sessions[user_id]['client']  
        
        # تحميل الصورة  
        photo_path = await event.download_media(file="temp_photo.jpg")  
        
        # حذف الصور السابقة  
        photos = await client.get_profile_photos('me')  
        if photos:  
            await client(DeletePhotosRequest(photos))  
        
        # رفع الصورة الجديدة  
        uploaded_file = await client.upload_file(photo_path)  
        await client(UploadProfilePhotoRequest(file=uploaded_file))  
        
        # تنظيف  
        if os.path.exists(photo_path):  
            os.remove(photo_path)  
        
        user_sessions[user_id]['waiting_for_photo'] = False  
        
        await event.reply("✅ تم تغيير صورة الملف الشخصي بنجاح!")  
        await show_main_menu(event)  
        
    except Exception as e:  
        await event.reply(f"❌ خطأ في تغيير الصورة: {str(e)}")  
        user_sessions[user_id]['waiting_for_photo'] = False

async def change_name_start(event):
    user_id = event.sender_id

    if not await check_user_login(user_id):  
        await event.answer("❌ الرجاء تسجيل الدخول أولاً", alert=True)  
        return  

    user_sessions[user_id]['waiting_for_name'] = True  

    await event.edit("✏️ **تغيير اسم الملف الشخصي**\n\nالرجاء إرسال الاسم الجديد:", buttons=[[Button.inline("🔙 رجوع", b="help")]])

async def handle_name_change(event):
    user_id = event.sender_id
    new_name = event.text.strip()

    try:
        if new_name and len(new_name) > 0:
            client = user_sessions[user_id]['client']  
            await client(UpdateProfileRequest(first_name=new_name))  
            
            user_sessions[user_id]['waiting_for_name'] = False  
            user_sessions[user_id]['user_info']['first_name'] = new_name  
            
            await event.reply(f"✅ تم تغيير الاسم إلى: {new_name}")  
            await show_main_menu(event)  
        else:
            await event.reply("❌ الاسم يجب أن لا يكون فارغًا!")  
            user_sessions[user_id]['waiting_for_name'] = False  
        
    except Exception as e:  
        await event.reply(f"❌ خطأ في تغيير الاسم: {str(e)}")  
        user_sessions[user_id]['waiting_for_name'] = False

async def auto_change_start(event):
    user_id = event.sender_id

    if not await check_user_login(user_id):  
        await event.answer("❌ الرجاء تسجيل الدخول أولاً", alert=True)  
        return  

    await event.edit("🔄 **التغيير المتكرر للصورة**\n\nهذه الميزة تسمح بتغيير الصورة عدة مرات تلقائياً\n\nسيتم إضافتها في تحديث قريب!", buttons=[[Button.inline("🔙 رجوع", b="help")]])

async def account_info(event):
    user_id = event.sender_id

    if not await check_user_login(user_id):  
        await event.answer("❌ الرجاء تسجيل الدخول أولاً", alert=True)  
        return  

    user_info = user_sessions[user_id]['user_info']  

    await event.edit(f"📊 **معلومات الحساب**\n\n👤 الاسم: {user_info['first_name'] or 'غير محدد'}\n📞 الهاتف: {user_info['phone']}\n🔗 اليوزر: @{user_info['username'] or 'غير محدد'}\n\n🆔 ID: {user_id}", buttons=[[Button.inline("🔙 رجوع", b="help")]])

async def logout_user(event):
    user_id = event.sender_id

    buttons = [[Button.inline("✅ نعم، تأكيد", b="confirm_logout"), Button.inline("❌ إلغاء", b="help")]]
    
    await event.edit("🚪 **تسجيل الخروج**\n\nهل أنت متأكد من أنك تريد تسجيل الخروج؟\nسيتم إغلاق جلسة حسابك في البوت.", buttons=buttons)()

async def handle_confirmation(event, data):
    user_id = event.sender_id

    if data == "confirm_logout":  
        await cleanup_session(user_id)  
        await event.edit("✅ **تم تسجيل الخروج بنجاح**\n\nشكراً لاستخدامك البوت\nيمكنك تسجيل الدخول مرة أخرى في أي وقت", buttons=[[Button.inline("📱 تسجيل الدخول", b="login")]])

async def check_user_login(user_id):
    if user_id not in user_sessions or not user_sessions[user_id].get('logged_in'):  
        return False  

    try:  
        client = user_sessions[user_id]['client']  
        if not client.is_connected():  
            await client.connect()  
        return True  
    except:  
        return False

async def cleanup_session(user_id):
    if user_id in user_sessions:
        try:
            client = user_sessions[user_id].get('client')
            if client and client.is_connected():
                await client.disconnect()
        except:
            pass
        del user_sessions[user_id]

async def main():
    # إنشاء مجلد الجلسات إذا لم يكن موجوداً
    if not os.path.exists('sessions'):
        os.makedirs('sessions')

    print("✅ البوت يعمل الآن!")  
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    bot_client.loop.run_until_complete(main())
