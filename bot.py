# bot_login.py
import os
import json
import asyncio
import tempfile
from dotenv import load_dotenv

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.account import UpdateProfileRequest

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("8220021407:AAFWyT0UJpeu6qymzwmLh3Ks25GGWvFcZ_k")
OWNER_ID = int(os.getenv("OWNER_ID", "6583786208"))
API_ID = int(os.getenv("API_ID", "27227913"))
API_HASH = os.getenv("API_HASH", "ba805b182eca99224403dbcd5d4f50aa")
SESSION_STORE = os.getenv("SESSION_STORE", "./sessions.json")

# Conversation states
AWAIT_PHONE, AWAIT_CODE, AWAIT_PASS, AWAIT_NAME, AWAIT_PHOTO = range(5)

# In-memory clients cache: owner_id -> {"client": TelethonClient, "session": string}
clients = {}

# Helpers to persist sessions (very simple JSON storage)
def load_sessions():
    try:
        with open(SESSION_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_sessions(sessions):
    try:
        with open(SESSION_STORE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("فشل حفظ الجلسات:", e)

# Inline keyboard
def main_menu():
    kb = [
        [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data="login"),
         InlineKeyboardButton("⛔ تسجيل الخروج", callback_data="logout")],
        [InlineKeyboardButton("📸 تغيير الصورة", callback_data="change_photo"),
         InlineKeyboardButton("✏️ تغيير الاسم", callback_data="change_name")],
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("هذا البوت خاص بالمالك فقط.")
        return
    await update.message.reply_text(
        "أهلاً! استخدم الأزرار أدناه.\n"
        "اضغط على 'تسجيل الدخول' لبدء جلسة المستخدم عبر الهاتف.",
        reply_markup=main_menu()
    )

# Start login flow
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await q.edit_message_text("غير مصرح.")
        return

    data = q.data
    if data == "login":
        await q.edit_message_text("أرسل رقم هاتفك بصيغة دولية (مثال: +201234567890).")
        return AWAIT_PHONE
    elif data == "logout":
        # logout: disconnect and remove saved session
        sesss = load_sessions()
        sid = str(uid)
        if sid in sesss:
            try:
                # disconnect telethon client if exists
                entry = clients.get(uid)
                if entry:
                    c = entry.get("client")
                    if c and awaitable_is_connected(c):
                        try:
                            await c.disconnect()
                        except:
                            pass
                    clients.pop(uid, None)
                sesss.pop(sid, None)
                save_sessions(sesss)
                await q.edit_message_text("تم تسجيل الخروج وحذف الجلسة.")
            except Exception as e:
                await q.edit_message_text(f"حدث خطأ أثناء تسجيل الخروج: {e}")
        else:
            await q.edit_message_text("لا توجد جلسة محفوظة لتسجيل الخروج منها.")
    elif data == "change_name":
        await q.edit_message_text("أرسل الاسم الجديد. يمكنك كتابة 'الاسم الأول|اللقب' لو أحببت.")
        return AWAIT_NAME
    elif data == "change_photo":
        await q.edit_message_text("أرسل صورة جديدة الآن (كصورة).")
        return AWAIT_PHOTO
    else:
        await q.edit_message_text("خيار غير معروف.")

# Utility to check telethon client's connection (Telethon client has is_connected coroutine in newer versions)
async def awaitable_is_connected(client: TelegramClient):
    try:
        return client.is_connected()
    except TypeError:
        # if is_connected is coroutine
        try:
            return await client.is_connected()
        except:
            return False

# Receive phone number
async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END

    phone = update.message.text.strip()
    # create a temporary Telethon client with ephemeral StringSession to request code
    # using StringSession() (empty) so no saved session yet
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    try:
        await client.connect()
    except Exception as e:
        await update.message.reply_text(f"خطأ في الاتصال بـ Telegram: {e}")
        return ConversationHandler.END

    try:
        await client.send_code_request(phone)
        # store client and phone in context for later sign-in
        context.user_data["login_client_tmp"] = client
        context.user_data["login_phone"] = phone
        await update.message.reply_text("تم إرسال كود التسجيل إلى حسابك. أرسل الكود هنا.")
        return AWAIT_CODE
    except PhoneNumberInvalidError:
        await client.disconnect()
        await update.message.reply_text("رقم الهاتف غير صالح. حاول مجددًا بصيغة دولية.")
        return ConversationHandler.END
    except Exception as e:
        await client.disconnect()
        await update.message.reply_text(f"فشل إرسال الكود: {e}")
        return ConversationHandler.END

# Receive code
async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END

    code = update.message.text.strip()
    client: TelegramClient = context.user_data.get("login_client_tmp")
    phone = context.user_data.get("login_phone")
    if not client or not phone:
        await update.message.reply_text("انتهت الجلسة المؤقتة، أعد المحاولة من جديد (/start).")
        return ConversationHandler.END

    try:
        # Attempt to sign in with code
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            # 2FA is enabled; ask for password
            await update.message.reply_text("الحساب محمي بكلمة مرور (2FA). أرسل كلمة المرور الآن.")
            return AWAIT_PASS
        except PhoneCodeInvalidError:
            await update.message.reply_text("الكود غير صحيح. أعد المحاولة أو اطلب كود جديد.")
            await client.disconnect()
            return ConversationHandler.END

        # if signed in successfully:
        me = await client.get_me()
        # save session string
        session_str = client.session.save()
        # persist session to file
        sessions = load_sessions()
        sessions[str(uid)] = {"session": session_str}
        save_sessions(sessions)
        # store in-memory
        clients[uid] = {"client": client, "session": session_str, "me": me.to_dict()}
        await update.message.reply_text(f"تم تسجيل الدخول بنجاح إلى: {me.username or me.first_name}\nاستخدم الأزرار لتنفيذ أوامر.", reply_markup=main_menu())
        return ConversationHandler.END

    except Exception as e:
        await client.disconnect()
        await update.message.reply_text(f"فشل تسجيل الدخول: {e}")
        return ConversationHandler.END

# Receive 2FA password
async def receive_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END

    password = update.message.text.strip()
    client: TelegramClient = context.user_data.get("login_client_tmp")
    phone = context.user_data.get("login_phone")
    if not client or not phone:
        await update.message.reply_text("انتهت الجلسة المؤقتة، أعد المحاولة من جديد (/start).")
        return ConversationHandler.END

    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        session_str = client.session.save()
        sessions = load_sessions()
        sessions[str(uid)] = {"session": session_str}
        save_sessions(sessions)
        clients[uid] = {"client": client, "session": session_str, "me": me.to_dict()}
        await update.message.reply_text(f"تم تسجيل الدخول بنجاح (2FA) إلى: {me.username or me.first_name}\nاستخدم الأزرار.", reply_markup=main_menu())
        return ConversationHandler.END
    except Exception as e:
        await client.disconnect()
        await update.message.reply_text(f"فشل تسجيل الدخول بكلمة المرور: {e}")
        return ConversationHandler.END

# Change name handler
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END

    text = update.message.text.strip()
    first = None
    last = None
    if "|" in text:
        first, last = [p.strip() for p in text.split("|", 1)]
    else:
        first = text

    entry = clients.get(uid)
    if not entry:
        # try load session from store
        sessions = load_sessions()
        sess = sessions.get(str(uid))
        if not sess:
            await update.message.reply_text("لا يوجد حساب مسجل. سجل الدخول أولاً.")
            return ConversationHandler.END
        client = TelegramClient(StringSession(sess["session"]), API_ID, API_HASH)
        await client.connect()
        entry = {"client": client, "session": sess["session"]}
        clients[uid] = entry

    client: TelegramClient = entry["client"]
    try:
        await client(UpdateProfileRequest(first_name=first, last_name=last))
        await update.message.reply_text("تم تحديث الاسم بنجاح.", reply_markup=main_menu())
    except Exception as e:
        await update.message.reply_text(f"فشل تحديث الاسم: {e}")
    return ConversationHandler.END

# Change photo handler
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("الرجاء إرسال صورة (كصورة).")
        return ConversationHandler.END

    entry = clients.get(uid)
    if not entry:
        sessions = load_sessions()
        sess = sessions.get(str(uid))
        if not sess:
            await update.message.reply_text("لا يوجد حساب مسجل. سجل الدخول أولاً.")
            return ConversationHandler.END
        client = TelegramClient(StringSession(sess["session"]), API_ID, API_HASH)
        await client.connect()
        entry = {"client": client, "session": sess["session"]}
        clients[uid] = entry

    client: TelegramClient = entry["client"]
    photo = update.message.photo[-1]
    tmp_dir = tempfile.gettempdir()
    file_path = os.path.join(tmp_dir, f"tg_upload_{uid}.jpg")
    try:
        await photo.get_file().download(custom_path=file_path)
        uploaded = await client.upload_file(file_path)
        await client(UploadProfilePhotoRequest(uploaded))
        await update.message.reply_text("تم تحديث الصورة الشخصية.", reply_markup=main_menu())
    except Exception as e:
        await update.message.reply_text(f"فشل تحديث الصورة: {e}")
    finally:
        try:
            os.remove(file_path)
        except:
            pass
    return ConversationHandler.END

# Graceful shutdown: disconnect all telethon clients
async def shutdown_clients():
    for uid, entry in list(clients.items()):
        try:
            c: TelegramClient = entry.get("client")
            if c:
                try:
                    await c.disconnect()
                except:
                    pass
        except Exception:
            pass
    clients.clear()

def build_conversation():
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(callback_query_handler)],
        states={
            AWAIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            AWAIT_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)],
            AWAIT_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass)],
            AWAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            AWAIT_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    return conv

async def on_startup(app):
    # load saved sessions into memory lazily; do not connect them now to avoid long startup
    print("البوت شغّال. جاهز.")

async def on_shutdown(app):
    print("جاري فصل جلسات Telethon...")
    await shutdown_clients()
    print("انتهى الفصل.")

def main():
    if not BOT_TOKEN or not API_ID or not API_HASH or not OWNER_ID:
        print("تأكد من إعداد BOT_TOKEN و API_ID و API_HASH و OWNER_ID في ملف .env")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(build_conversation())
    # catch-all callback queries must be added (so inline buttons work)
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    app.post_init(on_startup)
    app.shutdown(on_shutdown)

    print("بدء التشغيل. كس..")
    app.run_polling()

if __name__ == "__main__":
    main()
