import asyncio
import json
import os
import logging
import re
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient, errors, events
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged  # <-- خط جدید

BOT_TOKEN = "8837232261:AAFwUp6dBEFTmYPrL6_46hxnPjatYmVb-0Y"
API_ID, API_HASH = 33561438, "0165edd763263f95445183b4143dd438"

CF = "config.json"
TF = "messages.txt"
TAF = "targets.json"
GTF = "general_targets.json"
SF = "stickers.json"
GF = "gifs.json"
MEDIA_DIR = "media_storage"
STICKER_DIR = os.path.join(MEDIA_DIR, "stickers")
GIF_DIR = os.path.join(MEDIA_DIR, "gifs")

os.makedirs(STICKER_DIR, exist_ok=True)
os.makedirs(GIF_DIR, exist_ok=True)

ADMINS = [8262076174]
CHANNEL_LINK = "https://t.me/ataker_guard"
OWNER_USERNAME = "@POLO_IR"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    if os.path.exists(CF):
        try:
            with open(CF, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "accounts": [], "groups": [], "delay": 5, "active": False, "idx": 0,
        "admins": ADMINS, "temp_admins": {}, "msg_idx": 0, "active_groups": [],
        "account_status": {}, "reply_groups": [], "bulk_join_status": False,
        "mention_delay": 3, "max_mention_per_round": 3
    }

def save_config(d):
    with open(CF, 'w', encoding='utf-8') as f: json.dump(d, f, indent=2, ensure_ascii=False)

def load_msgs():
    if os.path.exists(TF):
        try:
            with open(TF, 'r', encoding='utf-8') as f: return [l.strip() for l in f if l.strip()]
        except: pass
    return ["سلام و درود بر شما، ربات اتکر فعال است."]

def save_msgs(m):
    with open(TF, 'w', encoding='utf-8') as f: f.write("\n".join(m))

def load_targets():
    if os.path.exists(TAF):
        try:
            with open(TAF, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def save_targets(t):
    with open(TAF, 'w', encoding='utf-8') as f: json.dump(t, f, indent=2, ensure_ascii=False)

def load_general_targets():
    if os.path.exists(GTF):
        try:
            with open(GTF, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def save_general_targets(t):
    with open(GTF, 'w', encoding='utf-8') as f: json.dump(t, f, indent=2, ensure_ascii=False)

def load_stickers():
    if os.path.exists(SF):
        try:
            with open(SF, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def save_stickers(s):
    with open(SF, 'w', encoding='utf-8') as f: json.dump(s, f, indent=2, ensure_ascii=False)

def load_gifs():
    if os.path.exists(GF):
        try:
            with open(GF, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def save_gifs(g):
    with open(GF, 'w', encoding='utf-8') as f: json.dump(g, f, indent=2, ensure_ascii=False)

config, msgs, clients, tmp = load_config(), load_msgs(), {}, {}
stickers, gifs = load_stickers(), load_gifs()

reply_config = {
    "active": False,
    "target_link_1": "", "target_msg_id_1": None, "chat_id_1": None, "active_target_1": True,
    "target_link_2": "", "target_msg_id_2": None, "chat_id_2": None, "active_target_2": False,
    "delay": 2, "message": "", "use_stickers": False, "use_gifs": False
}
last_msg_indices, last_sticker_indices, last_gif_indices, account_mention_cooldown, reply_counters = {}, {}, {}, {}, {}

def get_random_message(phone):
    if not msgs: return None
    if phone not in last_msg_indices: last_msg_indices[phone] = -1
    avail = [i for i in range(len(msgs)) if i != last_msg_indices[phone]]
    if not avail: avail = list(range(len(msgs)))
    idx = random.choice(avail)
    last_msg_indices[phone] = idx
    return msgs[idx]

def get_random_sticker(phone):
    if not stickers: return None
    if phone not in last_sticker_indices: last_sticker_indices[phone] = -1
    avail = [i for i in range(len(stickers)) if i != last_sticker_indices[phone]]
    if not avail: avail = list(range(len(stickers)))
    idx = random.choice(avail)
    last_sticker_indices[phone] = idx
    return stickers[idx]

def get_random_gif(phone):
    if not gifs: return None
    if phone not in last_gif_indices: last_gif_indices[phone] = -1
    avail = [i for i in range(len(gifs)) if i != last_gif_indices[phone]]
    if not avail: avail = list(range(len(gifs)))
    idx = random.choice(avail)
    last_gif_indices[phone] = idx
    return gifs[idx]

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 وضعیت سیستم و گزارش‌ها", callback_data="status")],
        [InlineKeyboardButton("➕ افزودن اکانت جدید", callback_data="add_account"), InlineKeyboardButton("📋 مدیریت اکانت‌ها", callback_data="account_manager")],
        [InlineKeyboardButton("📁 مدیریت گروه‌های هدف", callback_data="groups"), InlineKeyboardButton("👥 مدیریت لیست هدف‌ها", callback_data="targets")],
        [InlineKeyboardButton("📤 آپلود لیست پیام‌ها (TXT)", callback_data="upload")],
        [InlineKeyboardButton("🚀 شروع عملیات اتکر", callback_data="start_auto"), InlineKeyboardButton("⏹ توقف عملیات اتکر", callback_data="stop_auto")],
        [InlineKeyboardButton("⏱ تنظیم تاخیر اتکر", callback_data="delay"), InlineKeyboardButton("💬 سیستم ریپ چت پیشرفته", callback_data="reply_chat")],
        [InlineKeyboardButton("🌐 مدیریت ریپ عمومی", callback_data="general_reply_menu")],
        [InlineKeyboardButton("👑 مدیریت ادمین‌های ربات", callback_data="admin_panel"), InlineKeyboardButton("🔗 عضویت گروهی اکانت‌ها", callback_data="bulk_join")],
        [InlineKeyboardButton("ℹ️ درباره سیستم و راهنما", callback_data="about")]
    ])

def about_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 کانال رسمی اطلاع‌رسانی", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👤 ارتباط مستقیم با مالک و پشتیبانی", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ])

def admin_panel_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ اعطای دسترسی موقت ادمین", callback_data="add_temp_admin")],
        [InlineKeyboardButton("📋 مشاهده لیست ادمین‌ها", callback_data="list_admins")],
        [InlineKeyboardButton("🗑 لغو دسترسی ادمین", callback_data="remove_admin")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ])

def reply_chat_menu():
    t1_status = "✅ فعال" if reply_config["active_target_1"] else "❌ غیرفعال"
    t2_status = "✅ فعال" if reply_config["active_target_2"] else "❌ غیرفعال"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 شروع ربات ریپ چت", callback_data="start_reply"), InlineKeyboardButton("🔴 توقف ربات ریپ چت", callback_data="stop_reply")],
        [InlineKeyboardButton(f"🎯 تنظیم لینک هدف ۱ ({t1_status})", callback_data="set_reply_link_1"), InlineKeyboardButton("🗑 پاک‌سازی ۱", callback_data="clear_reply_link_1")],
        [InlineKeyboardButton(f"🎯 تنظیم لینک هدف ۲ ({t2_status})", callback_data="set_reply_link_2"), InlineKeyboardButton("🗑 پاک‌سازی ۲", callback_data="clear_reply_link_2")],
        [InlineKeyboardButton(f"🔄 تغییر وضعیت هدف ۱", callback_data="toggle_target_1"), InlineKeyboardButton(f"🔄 تغییر وضعیت هدف ۲", callback_data="toggle_target_2")],
        [InlineKeyboardButton("⏱ تنظیم تاخیر زمانی ریپ", callback_data="set_reply_delay")],
        [InlineKeyboardButton("🎴 تنظیمات استیکرهای ریپ", callback_data="sticker_settings"), InlineKeyboardButton("🎬 تنظیمات گیف‌های ریپ", callback_data="gif_settings")],
        [InlineKeyboardButton("📁 انتخاب گروه‌های ویژه ریپ چت", callback_data="reply_groups")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ])

def general_reply_menu():
    targets = load_general_targets()
    kb = []
    if not targets:
        kb.append([InlineKeyboardButton("❌ هیچ یوزری ثبت نشده است", callback_data="noop")])
    else:
        for t in targets[:10]:
            kb.append([InlineKeyboardButton(f"🗑 حذف: {t}", callback_data=f"del_gen_target_{t}")])
    kb.extend([
        [InlineKeyboardButton("➕ افزودن آیدی هدف عمومی جدید", callback_data="add_gen_target")],
        [InlineKeyboardButton("🗑 پاک‌سازی کامل لیست عمومی", callback_data="clear_gen_targets")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ])
    return InlineKeyboardMarkup(kb)

def sticker_settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن استیکر جدید (ارسال پشت سر هم)", callback_data="add_sticker")],
        [InlineKeyboardButton("📋 لیست استیکرهای ذخیره‌شده", callback_data="list_stickers"), InlineKeyboardButton("🗑 پاک‌سازی کامل استیکرها", callback_data="clear_stickers")],
        [InlineKeyboardButton("🔁 فعال/غیرفعال‌سازی ارسال استیکر", callback_data="toggle_stickers")],
        [InlineKeyboardButton("🔙 بازگشت به مدیریت ریپ چت", callback_data="reply_chat")]
    ])

def gif_settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن گیف جدید (ارسال پشت سر هم)", callback_data="add_gif")],
        [InlineKeyboardButton("📋 لیست گیف‌های ذخیره‌شده", callback_data="list_gifs"), InlineKeyboardButton("🗑 پاک‌سازی کامل گیف‌ها", callback_data="clear_gifs")],
        [InlineKeyboardButton("🔁 فعال/غیرفعال‌سازی ارسال گیف", callback_data="toggle_gifs")],
        [InlineKeyboardButton("🔙 بازگشت به مدیریت ریپ چت", callback_data="reply_chat")]
    ])

def account_manager_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 مشاهده لیست کامل اکانت‌ها", callback_data="list_accounts")],
        [InlineKeyboardButton("✅ تغییر وضعیت فعال/غیرفعال اکانت", callback_data="toggle_account")],
        [InlineKeyboardButton("🗑 حذف یک اکانت از سیستم", callback_data="remove_account"), InlineKeyboardButton("📊 آمار تفکیکی اکانت‌ها", callback_data="accounts_status")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ])

def group_manager_menu():
    kb = []
    auto_groups, reply_groups = config.get("active_groups", []), config.get("reply_groups", [])
    if not config["groups"]:
        kb.append([InlineKeyboardButton("❌ در حال حاضر هیچ گروهی ثبت نشده است", callback_data="noop")])
    else:
        for i, g in enumerate(config["groups"]):
            is_auto = "✅" if g in auto_groups else "❌"
            is_reply = "🔄" if g in reply_groups else "⭕"
            kb.append([InlineKeyboardButton(f"اتکر: {is_auto} | ریپ: {is_reply} | {g[:30]}...", callback_data=f"toggle_group_{g}")])
    kb.extend([
        [InlineKeyboardButton("➕ افزودن گروه جدید به لیست", callback_data="add_group")],
        [InlineKeyboardButton("🗑 پاک‌سازی کل گروه‌ها", callback_data="clear_groups")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ])
    return InlineKeyboardMarkup(kb)

def reply_groups_menu():
    kb = []
    reply_groups = config.get("reply_groups", [])
    if not config["groups"]:
        kb.append([InlineKeyboardButton("❌ هیچ گروهی ثبت نشده است", callback_data="noop")])
    else:
        for i, g in enumerate(config["groups"]):
            is_reply = "✅ فعال در ریپ" if g in reply_groups else "❌ غیرفعال"
            kb.append([InlineKeyboardButton(f"{is_reply} - {g[:30]}...", callback_data=f"toggle_reply_group_{g}")])
    kb.append([InlineKeyboardButton("🔙 بازگشت به مدیریت ریپ چت", callback_data="reply_chat")])
    return InlineKeyboardMarkup(kb)

def targets_menu():
    targets = load_targets()
    kb = []
    if not targets:
        kb.append([InlineKeyboardButton("❌ هیچ هدف یا یوزری ثبت نشده است", callback_data="noop")])
    else:
        for t in targets[:15]:
            kb.append([InlineKeyboardButton(f"🗑 حذف هدف: {t[:25]}", callback_data=f"del_target_{t}")])
    kb.extend([
        [InlineKeyboardButton("➕ افزودن هدف جدید", callback_data="add_target")],
        [InlineKeyboardButton("🗑 پاک‌سازی تمامی هدف‌ها", callback_data="clear_targets")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ])
    return InlineKeyboardMarkup(kb)

async def get_client(phone):
    if phone in clients:
        c = clients[phone]
        if c.is_connected():
            return c
    try:
        # استفاده از ConnectionTcpAbridged برای اتصال پایدارتر
        c = TelegramClient(f"sess_{phone}", API_ID, API_HASH, connection=ConnectionTcpAbridged, timeout=30)
        await c.connect()
        if await c.is_user_authorized():
            clients[phone] = c
            return c
        else:
            await c.disconnect()
            return None
    except Exception as e:
        logger.error(f"خطا در اتصال اکانت {phone}: {e}")
        return None

async def login(phone):
    try:
        if phone in tmp:
            try: await tmp[phone]["c"].disconnect()
            except: pass
            del tmp[phone]

        session_name = f"sess_{phone}"
        session_file = f"{session_name}.session"
        if os.path.exists(session_file):
            try:
                if phone in clients:
                    try: await clients[phone].disconnect()
                    except: pass
                    del clients[phone]
                os.remove(session_file)
            except: pass

        # استفاده از ConnectionTcpAbridged با timeout بیشتر
        c = TelegramClient(session_name, API_ID, API_HASH, connection=ConnectionTcpAbridged, timeout=30)
        await c.connect()
        
        try:
            r = await c.send_code_request(phone)
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            r = await c.send_code_request(phone)
        except Exception as e:
            await c.disconnect()
            return False, f"❌ خطا در اتصال به سرور تلگرام یا ارسال کد: {str(e)[:60]}"

        tmp[phone] = {"c": c, "h": r.phone_code_hash, "tm": datetime.now(), "tr": 0}
        return True, "✅ کد تایید ورود با موفقیت به شماره شما ارسال گردید. لطفا کد دریافتی را وارد کنید."
    except Exception as e:
        return False, f"❌ خطای بحرانی در احراز هویت: {str(e)[:60]}"

async def verify(phone, code):
    try:
        if phone not in tmp: return False, "❌ اطلاعات نشست این شماره منقضی شده است. لطفا دوباره تلاش کنید."
        d = tmp[phone]
        if datetime.now() - d["tm"] > timedelta(minutes=10):
            try: await d["c"].disconnect()
            except: pass
            del tmp[phone]
            return False, "❌ زمان مجاز برای ورود کد به پایان رسیده است."

        c_code = re.sub(r'\D', '', str(code))
        if len(c_code) != 5: return False, "❌ کد تایید باید دقیقاً ۵ رقم باشد."

        d["tr"] += 1
        if d["tr"] > 5:
            try: await d["c"].disconnect()
            except: pass
            del tmp[phone]
            return False, "❌ تعداد تلاش‌های ناموفق بیش از حد مجاز است."

        try:
            await d["c"].sign_in(phone=phone, code=c_code, phone_code_hash=d["h"])
        except errors.PhoneCodeInvalidError:
            return False, f"❌ کد وارد شده اشتباه است! {5 - d['tr']} تلاش باقی مانده."
        except errors.PhoneCodeExpiredError:
            return False, "❌ کد تایید منقضی شده است."
        except errors.SessionPasswordNeededError:
            return False, "❌ این اکانت دارای تایید دو مرحله‌ای (Password) است که در این نسخه پشتیبانی نمی‌شود."
        except Exception as e:
            return False, f"❌ خطا در بررسی کد: {str(e)[:60]}"

        if await d["c"].is_user_authorized():
            clients[phone] = d["c"]
            del tmp[phone]
            if phone not in config["accounts"]:
                config["accounts"].append(phone)
                config["account_status"][phone] = True
                save_config(config)
            return True, f"✅ اکانت با شماره {phone} با موفقیت تایید و به سیستم افزوده شد."
        return False, "❌ خطای ناشناخته در تأیید نهایی حساب کاربری."
    except Exception as e:
        return False, f"❌ خطای سیستم: {str(e)[:60]}"

async def join_group(phone, group_link):
    try:
        c = await get_client(phone)
        if not c: return False, f"❌ اکانت {phone} معتبر یا متصل نیست"
        link = group_link.strip().replace('https://', '').replace('http://', '').replace('t.me/', '')
        if link.startswith('+') or link.startswith('joinchat/'):
            hash_val = link.replace('joinchat/', '').replace('+', '')
            await c(ImportChatInviteRequest(hash_val))
        else:
            await c(JoinChannelRequest(link))
        return True, f"✅ اکانت {phone} با موفقیت به گروه پیوست."
    except errors.UserAlreadyParticipantError:
        return True, f"ℹ️ اکانت {phone} از قبل عضو این گروه بوده است."
    except Exception as e:
        return False, f"❌ اکانت {phone}: {str(e)[:45]}"

async def join_all_accounts_to_group(group_link):
    tasks = []
    for phone in config["accounts"]:
        if config.get("account_status", {}).get(phone, True):
            tasks.append(join_group(phone, group_link))
    if tasks:
        return await asyncio.gather(*tasks)
    return []

async def mention(c, g, m):
    try:
        if not c.is_connected(): await c.connect()
        chat = await c.get_entity(g)
        targets = load_targets()
        if not targets: return 0
        ms = []
        for t in targets[:15]:
            t = t.strip()
            if t.startswith('@'):
                try:
                    u = await c.get_entity(t)
                    if u: ms.append(f'<a href="tg://user?id={u.id}">@{t[1:]}</a>')
                except: pass
            elif t.isdigit() or (t.startswith('-') and t[1:].isdigit()):
                try:
                    u = await c.get_entity(int(t))
                    if u:
                        un = f"@{u.username}" if u.username else "کاربر"
                        ms.append(f'<a href="tg://user?id={int(t)}">{un}</a>')
                except: pass
        if not ms: return 0
        await c.send_message(chat, f"{' '.join(ms)}\n\n{m}", parse_mode='html')
        return len(ms)
    except:
        return 0

async def auto_loop():
    logger.info("🚀 موتور اتکر هوشمند و ارسال منشن آغاز به کار کرد.")
    fail_count = 0
    global account_mention_cooldown
    while config["active"]:
        try:
            active_groups = config.get("active_groups", [])
            if not active_groups: active_groups = config["groups"]
            if not active_groups or not config["accounts"]:
                await asyncio.sleep(5)
                continue

            for g in active_groups:
                if g not in config["groups"] or not config["active"]: break

                current_time = datetime.now()
                for phone in list(account_mention_cooldown.keys()):
                    if (current_time - account_mention_cooldown[phone]).seconds >= config.get("mention_delay", 3):
                        del account_mention_cooldown[phone]

                available_accounts = []
                for p in config["accounts"]:
                    if not config.get("account_status", {}).get(p, True): continue
                    if p not in account_mention_cooldown: available_accounts.append(p)

                selected_accounts = available_accounts

                if selected_accounts:
                    tasks = [send_mention_with_account(p, g) for p in selected_accounts]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for i, p in enumerate(selected_accounts):
                        if i < len(results) and isinstance(results[i], int) and results[i] > 0:
                            account_mention_cooldown[p] = datetime.now()
                            fail_count = 0
                    success_count = sum(1 for r in results if isinstance(r, int) and r > 0)
                    if success_count == 0: fail_count += 1

                await asyncio.sleep(config.get("mention_delay", 3))
                if fail_count > 10:
                    await asyncio.sleep(60)
                    fail_count = 0
        except Exception as e:
            logger.error(f"خطا در حلقه اتکر: {e}")
            await asyncio.sleep(10)

async def send_mention_with_account(phone, group):
    try:
        c = await get_client(phone)
        if not c: return 0
        message_text = get_random_message(phone)
        if not message_text: return 0
        return await mention(c, group, message_text)
    except:
        return 0

async def send_sticker_to_group(phone, group, sticker_path, reply_to=None):
    try:
        c = await get_client(phone)
        if not c: return False
        chat_entity = await c.get_entity(group)
        if os.path.exists(sticker_path):
            await c.send_file(chat_entity, sticker_path, reply_to=reply_to)
            return True
        return False
    except: return False

async def send_gif_to_group(phone, group, gif_path, reply_to=None):
    try:
        c = await get_client(phone)
        if not c: return False
        chat_entity = await c.get_entity(group)
        if os.path.exists(gif_path):
            await c.send_file(chat_entity, gif_path, reply_to=reply_to)
            return True
        return False
    except: return False

async def execute_reply_for_target(phone, chat_id, target_msg_id):
    try:
        c = await get_client(phone)
        if not c: return False

        await asyncio.sleep(random.uniform(0.2, 1.2))

        if phone not in reply_counters: reply_counters[phone] = 0
        counter = reply_counters[phone]
        reply_counters[phone] = (counter + 1) % 4

        use_sticker = reply_config.get("use_stickers", False) and stickers
        use_gif = reply_config.get("use_gifs", False) and gifs

        if counter == 2 and use_sticker:
            sticker_path = get_random_sticker(phone)
            if sticker_path and await send_sticker_to_group(phone, chat_id, sticker_path, target_msg_id):
                return True
        elif counter == 3 and use_gif:
            gif_path = get_random_gif(phone)
            if gif_path and await send_gif_to_group(phone, chat_id, gif_path, target_msg_id):
                return True

        message_text = get_random_message(phone)
        if message_text:
            if target_msg_id:
                await c.send_message(chat_id, message_text, reply_to=target_msg_id)
            else:
                await c.send_message(chat_id, message_text)
            return True
        return False
    except: return False

async def reply_chat_function():
    logger.info("💬 سیستم ریپ‌چت هوشمند با دو لینک هدف آغاز به کار کرد.")
    fail_count = 0
    while reply_config["active"]:
        try:
            has_active_target = (reply_config["active_target_1"] and reply_config["target_link_1"] and reply_config["chat_id_1"]) or \
                                (reply_config["active_target_2"] and reply_config["target_link_2"] and reply_config["chat_id_2"])
            if not has_active_target:
                await asyncio.sleep(5)
                continue
            if not msgs and not stickers and not gifs:
                await asyncio.sleep(5)
                continue

            tasks = []
            reply_groups = config.get("reply_groups", [])
            if not reply_groups: reply_groups = config["groups"]

            for phone in config["accounts"]:
                if not config.get("account_status", {}).get(phone, True): continue
                for g in reply_groups:
                    if g not in config["groups"]: continue

                    if reply_config["active_target_1"] and reply_config["chat_id_1"] and reply_config["target_msg_id_1"]:
                        tasks.append(execute_reply_for_target(phone, reply_config["chat_id_1"], reply_config["target_msg_id_1"]))

                    if reply_config["active_target_2"] and reply_config["chat_id_2"] and reply_config["target_msg_id_2"]:
                        tasks.append(execute_reply_for_target(phone, reply_config["chat_id_2"], reply_config["target_msg_id_2"]))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for r in results if r is True)
                if success_count > 0: fail_count = 0
                else: fail_count += 1

            await asyncio.sleep(reply_config["delay"])
            if fail_count > 10:
                await asyncio.sleep(60)
                fail_count = 0
        except Exception as e:
            await asyncio.sleep(10)

async def setup_general_reply_listeners():
    for phone in config["accounts"]:
        c = await get_client(phone)
        if not c: continue
        try:
            @c.on(events.NewMessage(incoming=True))
            async def general_reply_listener(event):
                try:
                    sender = await event.get_sender()
                    if not sender: return
                    gen_targets = load_general_targets()
                    if not gen_targets: return

                    sender_id_str = str(sender.id)
                    sender_username = f"@{sender.username}" if sender.username else ""

                    matched = False
                    for gt in gen_targets:
                        gt = gt.strip()
                        if gt == sender_id_str or gt == sender_username or (gt.startswith('@') and gt.lower() == sender_username.lower()):
                            matched = True
                            break

                    if matched:
                        msg_text = get_random_message(phone)
                        if msg_text:
                            await event.reply(msg_text)
                except: pass
        except: pass

def check_admin_access(user_id):
    if user_id in config.get("admins", ADMINS): return True
    temp_admins = config.get("temp_admins", {})
    if str(user_id) in temp_admins:
        if datetime.now() < datetime.fromisoformat(temp_admins[str(user_id)]): return True
        else:
            del temp_admins[str(user_id)]
            config["temp_admins"] = temp_admins
            save_config(config)
    return False

async def add_temp_admin(user_id, days):
    temp_admins = config.get("temp_admins", {})
    temp_admins[str(user_id)] = (datetime.now() + timedelta(days=days)).isoformat()
    config["temp_admins"] = temp_admins
    save_config(config)
    return f"✅ ادمین با آیدی عددی {user_id} با موفقیت به مدت {days} روز به سیستم افزوده شد."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_admin_access(update.effective_user.id):
        return await update.message.reply_text("❌ شما دسترسی لازم برای استفاده از این ربات را ندارید!")
    await update.message.reply_text(
        "🤖 **سیستم مدیریت هوشمند اتکر و ریپ‌چت (نسخه پیشرفته v2.5)**\n\n"
        "🔹 از طریق دکمه‌های شیک و منظم زیر می‌توانید تمامی بخش‌های سیستم، اکانت‌ها، گروه‌ها و ارسال رسانه‌ها را کنترل کنید:",
        reply_markup=main_menu(), parse_mode='Markdown'
    )

async def user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_admin_access(user_id):
        return await update.message.reply_text("❌ دسترسی غیرمجاز!")
    active_accounts = sum(1 for p in config["accounts"] if config.get("account_status", {}).get(p, True))
    targets = load_targets()
    gen_targets = load_general_targets()
    reply_groups = config.get("reply_groups", [])
    text = (
        f"📊 **گزارش جامع وضعیت سیستم اتکر و ریپ‌چت**\n\n"
        f"🔹 **وضعیت موتورها:**\n"
        f"• وضعیت اتکر اصلی: {'فعال ✅' if config['active'] else 'غیرفعال ❌'}\n"
        f"• وضعیت ریپ چت: {'فعال ✅' if reply_config['active'] else 'غیرفعال ❌'}\n\n"
        f"👥 **آمار اکانت‌های متصل:**\n"
        f"• کل اکانت‌ها: {len(config['accounts'])}\n"
        f"• اکانت‌های فعال و آماده: {active_accounts}\n"
        f"• اکانت‌های غیرفعال شده: {len(config['accounts']) - active_accounts}\n\n"
        f"📁 **گروه‌ها و هدف‌ها:**\n"
        f"• گروه‌های فعال اتکر: {len(config.get('active_groups', [])) or len(config['groups'])}\n"
        f"• گروه‌های فعال ریپ‌چت: {len(reply_groups)}\n"
        f"• هدف‌های منشن: {len(targets)} | هدف‌های ریپ عمومی: {len(gen_targets)}\n\n"
        f"📝 **محتوا و رسانه‌ها:**\n"
        f"• متن‌های پیام: {len(msgs)}\n"
        f"• استیکرهای ذخیره شده: {len(stickers)}\n"
        f"• گیف‌های ذخیره شده: {len(gifs)}\n"
    )
    kb = [
        [InlineKeyboardButton("🔄 بروزرسانی وضعیت", callback_data="refresh_panel")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    if not check_admin_access(user_id) and data not in ["about", "back_main", "refresh_panel"]:
        return await query.edit_message_text("❌ شما دسترسی ندارید!", reply_markup=main_menu())

    if data == "refresh_panel":
        await query.edit_message_text("🔄 وضعیت سیستم با موفقیت بروزرسانی شد.", reply_markup=main_menu())
    elif data == "status":
        active_accounts = sum(1 for p in config["accounts"] if config.get("account_status", {}).get(p, True))
        await query.edit_message_text(f"📊 وضعیت سیستم:\n• کل اکانت‌ها: {len(config['accounts'])}\n• اکانت‌های فعال: {active_accounts}\n• گروه‌ها: {len(config['groups'])}", reply_markup=main_menu())
    elif data == "about":
        await query.edit_message_text("ℹ️ **راهنمای جامع سیستم اتکر و ریپ‌چت**", reply_markup=about_menu(), parse_mode='Markdown')
    elif data == "bulk_join":
        await query.edit_message_text("🔗 **عضویت گروهی اکانت‌ها**\n\nلینک گروه مورد نظر را ارسال کنید:")
        context.user_data['action'] = 'bulk_join'
    elif data == "add_account":
        await query.edit_message_text("📱 **افزودن اکانت جدید**\n\nلطفاً شماره تلفن اکانت خود را وارد کنید (مثلا +989123456789):")
        context.user_data['action'] = 'add_acc'
    elif data == "groups":
        await query.edit_message_text("📁 **مدیریت گروه‌ها**", reply_markup=group_manager_menu(), parse_mode='Markdown')
    elif data == "add_group":
        await query.edit_message_text("📁 **افزودن گروه جدید**\n\nلینک گروه یا آیدی آن را ارسال کنید:")
        context.user_data['action'] = 'add_group'
    elif data.startswith("toggle_group_"):
        g = data.replace("toggle_group_", "")
        ag = config.setdefault("active_groups", [])
        if g in ag: ag.remove(g)
        else: ag.append(g)
        save_config(config)
        await query.edit_message_text("✅ وضعیت گروه در اتکر تغییر یافت.", reply_markup=group_manager_menu())
    elif data.startswith("toggle_reply_group_"):
        g = data.replace("toggle_reply_group_", "")
        rg = config.setdefault("reply_groups", [])
        if g in rg: rg.remove(g)
        else: rg.append(g)
        save_config(config)
        await query.edit_message_text("✅ وضعیت گروه در ریپ‌چت تغییر یافت.", reply_markup=group_manager_menu())
    elif data == "clear_groups":
        config["groups"], config["active_groups"], config["reply_groups"] = [], [], []
        save_config(config)
        await query.edit_message_text("🗑 تمامی گروه‌ها با موفقیت پاک شدند.", reply_markup=main_menu())
    elif data == "targets":
        await query.edit_message_text("👥 **مدیریت لیست هدف‌ها**", reply_markup=targets_menu())
    elif data == "add_target":
        await query.edit_message_text("🎯 **افزودن هدف جدید**\n\nیوزرنیم هدف (مثلا @username) یا آیدی عددی را وارد کنید:")
        context.user_data['action'] = 'add_target'
    elif data.startswith("del_target_"):
        t = data.replace("del_target_", "")
        tg = load_targets()
        if t in tg: tg.remove(t); save_targets(tg)
        await query.edit_message_text("✅ هدف مورد نظر حذف شد.", reply_markup=targets_menu())
    elif data == "clear_targets":
        save_targets([])
        await query.edit_message_text("🗑 تمامی هدف‌ها پاک شدند.", reply_markup=main_menu())

    elif data == "general_reply_menu":
        await query.edit_message_text("🌐 **مدیریت لیست ریپ عمومی**\n\nدر این بخش می‌توانید آیدی هر کاربری را وارد کنید تا در گروه‌های مشترک به او پاسخ داده شود:", reply_markup=general_reply_menu())
    elif data == "add_gen_target":
        await query.edit_message_text("🌐 **افزودن آیدی هدف عمومی**\n\nیوزرنیم یا آیدی عددی کاربر مورد نظر را بفرستید:")
        context.user_data['action'] = 'add_gen_target'
    elif data.startswith("del_gen_target_"):
        gt = data.replace("del_gen_target_", "")
        gt_list = load_general_targets()
        if gt in gt_list: gt_list.remove(gt); save_general_targets(gt_list)
        await query.edit_message_text("✅ هدف عمومی مورد نظر حذف شد.", reply_markup=general_reply_menu())
    elif data == "clear_gen_targets":
        save_general_targets([])
        await query.edit_message_text("🗑 تمامی هدف‌های عمومی پاک شدند.", reply_markup=general_reply_menu())
    elif data == "upload":
        await query.edit_message_text("📤 **آپلود لیست پیام‌ها**\n\nفایل متنی (TXT) پیام‌ها را ارسال کنید:")
        context.user_data['action'] = 'waiting_file'
    elif data == "start_auto":
        config["active"] = True; save_config(config)
        await query.edit_message_text("🚀 عملیات اتکر با موفقیت شروع شد!", reply_markup=main_menu())
        asyncio.create_task(auto_loop())
    elif data == "stop_auto":
        config["active"] = False; save_config(config)
        await query.edit_message_text("⏹ عملیات اتکر متوقف شد.", reply_markup=main_menu())
    elif data == "delay":
        await query.edit_message_text("⏱ **تنظیم تاخیر اتکر**\n\nمقدار تاخیر بر حسب ثانیه را وارد کنید:")
        context.user_data['action'] = 'delay'
    elif data == "reply_chat":
        await query.edit_message_text("💬 **سیستم پیشرفته ریپ‌چت (دو لینک هدف)**", reply_markup=reply_chat_menu())
    elif data == "reply_groups":
        await query.edit_message_text("📁 **انتخاب گروه‌های ویژه ریپ‌چت**", reply_markup=reply_groups_menu())
    elif data == "start_reply":
        reply_config["active"] = True
        await query.edit_message_text("💬 سیستم ریپ‌چت فعال شد.", reply_markup=reply_chat_menu())
        asyncio.create_task(reply_chat_function())
        asyncio.create_task(setup_general_reply_listeners())
    elif data == "stop_reply":
        reply_config["active"] = False
        await query.edit_message_text("⏹ سیستم ریپ‌چت متوقف شد.", reply_markup=reply_chat_menu())
    elif data == "set_reply_link_1":
        await query.edit_message_text("🎯 **تنظیم لینک پیام هدف ۱**\n\nلینک پیام مورد نظر را ارسال کنید:")
        context.user_data['action'] = 'set_reply_link_1'
    elif data == "set_reply_link_2":
        await query.edit_message_text("🎯 **تنظیم لینک پیام هدف ۲**\n\nلینک پیام مورد نظر را ارسال کنید:")
        context.user_data['action'] = 'set_reply_link_2'
    elif data == "clear_reply_link_1":
        reply_config["target_link_1"], reply_config["target_msg_id_1"], reply_config["chat_id_1"] = "", None, None
        await query.edit_message_text("🗑 لینک هدف ۱ پاک شد.", reply_markup=reply_chat_menu())
    elif data == "clear_reply_link_2":
        reply_config["target_link_2"], reply_config["target_msg_id_2"], reply_config["chat_id_2"] = "", None, None
        await query.edit_message_text("🗑 لینک هدف ۲ پاک شد.", reply_markup=reply_chat_menu())
    elif data == "toggle_target_1":
        reply_config["active_target_1"] = not reply_config["active_target_1"]
        await query.edit_message_text(f"✅ وضعیت هدف ۱ تغییر یافت: {'فعال' if reply_config['active_target_1'] else 'غیرفعال'}", reply_markup=reply_chat_menu())
    elif data == "toggle_target_2":
        reply_config["active_target_2"] = not reply_config["active_target_2"]
        await query.edit_message_text(f"✅ وضعیت هدف ۲ تغییر یافت: {'فعال' if reply_config['active_target_2'] else 'غیرفعال'}", reply_markup=reply_chat_menu())
    elif data == "set_reply_delay":
        await query.edit_message_text("⏱ مقدار تاخیر ریپ‌چت (ثانیه) را وارد کنید:")
        context.user_data['action'] = 'set_reply_delay'
    elif data == "sticker_settings":
        await query.edit_message_text("🎴 **مدیریت استیکرها**", reply_markup=sticker_settings_menu())
    elif data == "add_sticker":
        await query.edit_message_text("🎴 **افزودن استیکر (حالت آپلود گروهی)**\n\nاستیکرهای خود را **پشت سر هم** ارسال کنید. پس از اتمام از دکمه بازگشت استفاده کنید:")
        context.user_data['action'] = 'add_sticker'
    elif data == "list_stickers":
        await query.edit_message_text(f"🎴 تعداد کل استیکرها: {len(stickers)} عدد", reply_markup=sticker_settings_menu())
    elif data == "clear_stickers":
        stickers.clear(); save_stickers(stickers)
        await query.edit_message_text("🗑 تمامی استیکرها پاک شدند.", reply_markup=sticker_settings_menu())
    elif data == "toggle_stickers":
        reply_config["use_stickers"] = not reply_config.get("use_stickers", False)
        await query.edit_message_text(f"✅ وضعیت ارسال استیکر: {'فعال' if reply_config['use_stickers'] else 'غیرفعال'}", reply_markup=sticker_settings_menu())
    elif data == "gif_settings":
        await query.edit_message_text("🎬 **مدیریت گیف‌ها**", reply_markup=gif_settings_menu())
    elif data == "add_gif":
        await query.edit_message_text("🎬 **افزودن گیف (حالت آپلود گروهی)**\n\nگیف‌ها یا ویدیوهای خود را **پشت سر هم** ارسال کنید. پس از اتمام از دکمه بازگشت استفاده کنید:")
        context.user_data['action'] = 'add_gif'
    elif data == "list_gifs":
        await query.edit_message_text(f"🎬 تعداد کل گیف‌ها: {len(gifs)} عدد", reply_markup=gif_settings_menu())
    elif data == "clear_gifs":
        gifs.clear(); save_gifs(gifs)
        await query.edit_message_text("🗑 تمامی گیف‌ها پاک شدند.", reply_markup=gif_settings_menu())
    elif data == "toggle_gifs":
        reply_config["use_gifs"] = not reply_config.get("use_gifs", False)
        await query.edit_message_text(f"✅ وضعیت ارسال گیف: {'فعال' if reply_config['use_gifs'] else 'غیرفعال'}", reply_markup=gif_settings_menu())
    elif data == "account_manager":
        await query.edit_message_text("📋 **مدیریت اکانت‌ها**", reply_markup=account_manager_menu())
    elif data == "list_accounts":
        acc_list = "\n".join([f"• {p} ({'فعال ✅' if config.get('account_status', {}).get(p, True) else 'غیرفعال ❌'})" for p in config['accounts']]) or "هیچ اکانتی ثبت نشده است."
        await query.edit_message_text(f"📋 لیست اکانت‌ها:\n\n{acc_list}", reply_markup=account_manager_menu())
    elif data == "toggle_account":
        await query.edit_message_text("📱 شماره اکانت را وارد کنید:")
        context.user_data['action'] = 'toggle_account'
    elif data == "remove_account":
        await query.edit_message_text("🗑 شماره اکانت جهت حذف را وارد کنید:")
        context.user_data['action'] = 'remove_account'
    elif data == "accounts_status":
        await query.edit_message_text(f"📊 کل اکانت‌ها: {len(config['accounts'])}", reply_markup=account_manager_menu())
    elif data == "admin_panel":
        await query.edit_message_text("👑 **پنل مدیریت ادمین‌ها**", reply_markup=admin_panel_menu())
    elif data == "add_temp_admin":
        await query.edit_message_text("انتخاب مدت زمان:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("۷ روزه", callback_data="temp_admin_7")], [InlineKeyboardButton("🔙", callback_data="admin_panel")]]))
    elif data.startswith("temp_admin_"):
        await query.edit_message_text("آیدی عددی ادمین جدید را وارد کنید:")
        context.user_data['action'] = data
    elif data == "list_admins":
        await query.edit_message_text(f"👑 ادمین‌های اصلی: {ADMINS}\n ادمین‌های موقت: {list(config.get('temp_admins', {}).keys())}", reply_markup=admin_panel_menu())
    elif data == "remove_admin":
        await query.edit_message_text("آیدی عددی ادمین را برای حذف وارد کنید:")
        context.user_data['action'] = 'remove_admin'
    elif data == "back_main":
        context.user_data['action'] = None
        await query.edit_message_text("🤖 **منوی اصلی سیستم**", reply_markup=main_menu(), parse_mode='Markdown')
    elif data == "noop":
        await query.edit_message_text("⚠️ غیرفعال", reply_markup=main_menu())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    text = update.message.text.strip()
    if not check_admin_access(update.effective_user.id): return
    if text.lower() == ".panel": return await user_panel(update, context)
    if not action: return

    if action == 'add_acc':
        success, msg = await login(text)
        if success: context.user_data['phone'], context.user_data['action'] = text, 'verify'
        await update.message.reply_text(msg)
    elif action == 'verify':
        success, msg = await verify(context.user_data.get('phone'), text)
        await update.message.reply_text(msg)
        if success: context.user_data['action'] = None
    elif action == 'bulk_join':
        await update.message.reply_text("🔄 در حال عضویت گروهی تمامی اکانت‌ها...")
        res = await join_all_accounts_to_group(text)
        sc = sum(1 for s, _ in res if s)
        await update.message.reply_text(f"🔗 نتیجه عضویت گروهی:\n• موفق: {sc}\n• ناموفق: {len(res)-sc}")
        context.user_data['action'] = None
    elif action == 'add_group':
        if text not in config["groups"]:
            config["groups"].append(text)
            config.setdefault("active_groups", []).append(text)
            save_config(config)
            await update.message.reply_text("🔄 در حال عضویت اکانت‌ها در گروه جدید...")
            await join_all_accounts_to_group(text)
        await update.message.reply_text(f"✅ گروه با موفقیت اضافه شد: {text}")
        context.user_data['action'] = None
    elif action == 'add_target':
        tg = load_targets()
        if text not in tg:
            tg.append(text)
            save_targets(tg)
        await update.message.reply_text(f"✅ هدف جدید (یوزرنیم یا آیدی عددی) با موفقیت اضافه شد.")
        context.user_data['action'] = None
    elif action == 'add_gen_target':
        gt_list = load_general_targets()
        if text not in gt_list:
            gt_list.append(text)
            save_general_targets(gt_list)
        await update.message.reply_text(f"✅ هدف عمومی با موفقیت به لیست ریپ عمومی اضافه شد.")
        context.user_data['action'] = None
    elif action == 'delay':
        config["delay"] = int(text)
        save_config(config)
        context.user_data['action'] = None
        await update.message.reply_text("✅ تاخیر اتکر با موفقیت ثبت شد.")
    elif action == 'set_reply_link_1':
        reply_config["target_link_1"] = text
        parts = text.split("/")
        if len(parts) >= 5:
            reply_config["chat_id_1"] = int(parts[4]) if parts[3] == "c" else parts[3]
            reply_config["target_msg_id_1"] = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else (int(parts[4]) if parts[4].isdigit() else None)
            reply_config["active_target_1"] = True
            await update.message.reply_text("✅ لینک پیام هدف ۱ با موفقیت تحلیل و ثبت شد.")
            context.user_data['action'] = None
        else:
            await update.message.reply_text("❌ لینک وارد شده نامعتبر است.")
    elif action == 'set_reply_link_2':
        reply_config["target_link_2"] = text
        parts = text.split("/")
        if len(parts) >= 5:
            reply_config["chat_id_2"] = int(parts[4]) if parts[3] == "c" else parts[3]
            reply_config["target_msg_id_2"] = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else (int(parts[4]) if parts[4].isdigit() else None)
            reply_config["active_target_2"] = True
            await update.message.reply_text("✅ لینک پیام هدف ۲ با موفقیت تحلیل و ثبت شد.")
            context.user_data['action'] = None
        else:
            await update.message.reply_text("❌ لینک وارد شده نامعتبر است.")
    elif action == 'set_reply_delay':
        reply_config["delay"] = int(text)
        context.user_data['action'] = None
        await update.message.reply_text("✅ تاخیر ریپ‌چت ثبت شد.")
    elif action.startswith('temp_admin_'):
        res_msg = await add_temp_admin(int(text), int(action.split('_')[2]))
        await update.message.reply_text(res_msg)
        context.user_data['action'] = None
    elif action == 'remove_admin':
        ta = config.get("temp_admins", {})
        if text in ta:
            del ta[text]
            config["temp_admins"] = ta
            save_config(config)
            await update.message.reply_text("✅ دسترسی ادمین مورد نظر لغو شد.")
        else:
            await update.message.reply_text("❌ ادمین مورد نظر یافت نشد.")
        context.user_data['action'] = None
    elif action == 'toggle_account':
        if text in config["account_status"]:
            config["account_status"][text] = not config.get("account_status", {}).get(text, True)
            save_config(config)
            await update.message.reply_text("✅ وضعیت اکانت تغییر یافت.")
        else:
            await update.message.reply_text("❌ شماره اکانت یافت نشد.")
        context.user_data['action'] = None
    elif action == 'remove_account':
        if text in config["accounts"]:
            config["accounts"].remove(text)
            if text in config["account_status"]: del config["account_status"][text]
            save_config(config)
            await update.message.reply_text("✅ اکانت با موفقیت از سیستم حذف شد.")
        else:
            await update.message.reply_text("❌ اکانت یافت نشد.")
        context.user_data['action'] = None

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('action') != 'waiting_file': return
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    content = await file.download_as_bytearray()
    lines = [l.strip() for l in content.decode('utf-8').splitlines() if l.strip()]
    save_msgs(lines)
    global msgs
    msgs = lines
    await update.message.reply_text(f"✅ فایل با موفقیت پردازش شد و {len(lines)} پیام بارگذاری گردید.")
    context.user_data['action'] = None

async def media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get('action')
    try:
        if action == 'add_sticker' and update.message.sticker:
            file = await context.bot.get_file(update.message.sticker.file_id)
            file_path = os.path.join(STICKER_DIR, f"sticker_{random.randint(10000, 99999)}.webp")
            await file.download_to_drive(file_path)
            if file_path not in stickers:
                stickers.append(file_path)
                save_stickers(stickers)
            # اکشن ریست نمی‌شود تا کاربر بتواند استیکرهای بعدی را پشت سر هم ارسال کند
            await update.message.reply_text(f"✅ استیکر دریافت و ذخیره شد. (تعداد کل: {len(stickers)})\nمی‌توانید استیکر بعدی را بفرستید.")

        elif action == 'add_gif' and (update.message.animation or update.message.video or update.message.document):
            media_obj = update.message.animation or update.message.video or update.message.document
            if not media_obj:
                return
            file = await context.bot.get_file(media_obj.file_id)
            file_path = os.path.join(GIF_DIR, f"gif_{random.randint(10000, 99999)}.mp4")
            await file.download_to_drive(file_path)
            if file_path not in gifs:
                gifs.append(file_path)
                save_gifs(gifs)
            # اکشن ریست نمی‌شود تا کاربر بتواند گیف‌های بعدی را پشت سر هم ارسال کند
            await update.message.reply_text(f"✅ گیف/ویدیو دریافت و ذخیره شد. (تعداد کل گیف‌ها: {len(gifs)})\nمی‌توانید گیف بعدی را بفرستید.")
    except Exception as e:
        logger.error(f"خطا در ذخیره رسانه: {e}")
        await update.message.reply_text(f"❌ خطا در پردازش و ذخیره رسانه: {str(e)[:50]}")

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", user_panel))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.Document.Category("application/text"), document_handler))
    app.add_handler(MessageHandler(filters.Sticker.ALL | filters.ANIMATION | filters.VIDEO | filters.Document.ALL, media_handler))
    logger.info("🤖 ربات پیشرفته اتکر و ریپ‌چت با موفقیت روشن شد و آماده به کار است!")
    app.run_polling()

if __name__ == "__main__":
    import sys
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n👋 ربات متوقف شد.")
    except Exception as e:
        print(f"❌ خطای ناشناخته در اجرای ربات: {e}")