import json
import random
import time
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "7848560462:AAFvw76U_kl2BpCnm3oqHNi6dKfNnPEianM"
ADMIN_ID = 7434281447  # Thay bằng Telegram ID của bạn
CHANNELS = ["@keokmfree24"]  # Danh sách kênh yêu cầu tham gia
MIN_WITHDRAW = 10000
REF_REWARD = 1500
DATA_FILE = "users.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def check_channels(user_id, context):
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def get_main_menu():
    keyboard = [
        [KeyboardButton("💰 Số dư"), KeyboardButton("🏧 Rút tiền")],
        [KeyboardButton("🗓️ Điểm danh"), KeyboardButton("👫 Mời bạn bè")],
        [KeyboardButton("📊 Thống kê"), KeyboardButton("🏆 Top ref")],
        [KeyboardButton("📜 Lịch sử rút")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = user.id
    data = load_data()

    if str(chat_id) not in data:
        ref = update.message.text[7:] if update.message.text.startswith("/start ") else None
        data[str(chat_id)] = {
            "balance": 0,
            "bank": "Chưa cập nhật",
            "acc": "Chưa cập nhật",
            "ref": ref,
            "refs": [],
            "joined": str(datetime.now()),
            "last_checkin": "0",
            "history": []
        }
        if ref and ref in data and str(chat_id) not in data[ref]["refs"]:
            data[ref]["refs"].append(str(chat_id))
            data[ref]["balance"] += REF_REWARD
            await context.bot.send_message(
                chat_id=int(ref),
                text=f"ID {chat_id} đã tham gia bot bằng link giới thiệu của bạn.\n+{REF_REWARD} VND vào tài khoản!"
            )
        save_data(data)

    if not await check_channels(chat_id, context):
        join_buttons = [[InlineKeyboardButton(f"Tham gia {ch}", url=f"https://t.me/{ch[1:]}")] for ch in CHANNELS]
        join_buttons.append([InlineKeyboardButton("Tôi đã tham gia", callback_data="check_join")])
        await update.message.reply_text("Vui lòng tham gia các kênh sau để tiếp tục:", reply_markup=InlineKeyboardMarkup(join_buttons))
        return

    await update.message.reply_text("Chào mừng bạn quay lại!", reply_markup=get_main_menu())

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if await check_channels(user_id, context):
        await query.edit_message_text("Xác minh thành công! /start Lại để bắt đầu sử dụng bot.")
    else:
        await query.edit_message_text("Bạn chưa tham gia đủ nhóm!")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data:
        await update.message.reply_text("Vui lòng dùng /start để bắt đầu.")
        return

    user = data[user_id]

    if msg == "💰 Số dư":
        text = (
            f"Thông tin tài khoản\n\n"
            f"Số dư: {user['balance']} VND\n"
            
           
            f"ID Telegram: {user_id}\n"
            f"Ngày đăng ký: {user['joined'][:10]}"
        )
        await update.message.reply_text(text)

    elif msg == "🗓️ Điểm danh":
        now = datetime.now()
        last = datetime.fromtimestamp(float(user["last_checkin"])) if user["last_checkin"] != "0" else None
        if not last or (now - last).total_seconds() > 86400:
            amount = random.randint(700, 800)
            user["balance"] += amount
            user["last_checkin"] = str(time.time())
            await update.message.reply_text(
                f"Điểm danh thành công!\nBạn nhận: {amount} VND\nLúc: {now.strftime('%H:%M:%S %d/%m/%Y')}"
            )
        else:
            await update.message.reply_text("Bạn đã điểm danh hôm nay. Quay lại sau 24h.")

    elif msg == "👫 Mời bạn bè":
        link = f"https://t.me/kiemtiennhacai789_bot?start={user_id}"
        await update.message.reply_text(
            f"Mời bạn bè – Nhận thưởng!\nThưởng: {REF_REWARD} VND\nĐã mời: {len(user['refs'])} người\nLink: {link}"
        )

    elif msg == "📊 Thống kê":
        total_users = len(data)
        total_balance = sum(u["balance"] for u in data.values())
        total_withdraw = sum(sum(int(h["amount"]) for h in u.get("history", [])) for u in data.values())
        await update.message.reply_text(
            f"Thống kê hiện tại\nTổng người dùng: {total_users}\nTổng số dư: {total_balance} VND\nTổng đã rút: {total_withdraw} VND"
        )

    elif msg == "🏆 Top ref":
        ranking = sorted(data.items(), key=lambda x: len(x[1]["refs"]), reverse=True)[:10]
        if not ranking:
            await update.message.reply_text("Chưa có người dùng nào mời bạn bè.")
        else:
            result = "\n".join([f"{i+1}. {k} — {len(v['refs'])} ref" for i, (k, v) in enumerate(ranking)])
            await update.message.reply_text(f"Top giới thiệu:\n{result}")

    elif msg == "📜 Lịch sử rút":
        history = user.get("history", [])
        if not history:
            await update.message.reply_text("Bạn chưa có lịch sử rút tiền nào.")
        else:
            lines = [f"{h['time']}: {h['amount']} VND -> {h['acc']}" for h in history]
            await update.message.reply_text("\n".join(lines))

    elif msg == "🏧 Rút tiền":
        if user["balance"] < MIN_WITHDRAW:
            await update.message.reply_text(f"Số dư < {MIN_WITHDRAW} VND, không thể rút.")
        else:
            await update.message.reply_text("Gửi cú pháp: /rut STK-NGANHANG")

    elif msg.startswith("/set_minrut ") and user_id == str(ADMIN_ID):
        try:
            globals()["MIN_WITHDRAW"] = int(msg.split()[1])
            await update.message.reply_text(f"Đã chỉnh số tiền rút tối thiểu: {MIN_WITHDRAW} VND")
        except:
            await update.message.reply_text("Sai cú pháp. Dùng: /set_minrut 10000")

    elif msg.startswith("/set_ref ") and user_id == str(ADMIN_ID):
        try:
            globals()["REF_REWARD"] = int(msg.split()[1])
            await update.message.reply_text(f"Đã chỉnh tiền thưởng mời ref: {REF_REWARD} VND")
        except:
            await update.message.reply_text("Sai cú pháp. Dùng: /set_ref 1500")

    elif msg.startswith("/thongbao ") and user_id == str(ADMIN_ID):
        notice = msg[10:]
        for uid in data:
            try:
                await context.bot.send_message(chat_id=int(uid), text=f"[THÔNG BÁO TỪ ADMIN]\n\n{notice}")
            except:
                continue
        await update.message.reply_text("Đã gửi thông báo đến tất cả người dùng.")

    elif msg.startswith("/congtien ") and user_id == str(ADMIN_ID):
        try:
            parts = msg.split()
            uid, amount = parts[1], int(parts[2])
            if uid in data:
                data[uid]["balance"] += amount
                save_data(data)
                await update.message.reply_text(f"Đã cộng {amount} VND cho {uid}")
                await context.bot.send_message(chat_id=int(uid), text=f"Bạn vừa được cộng {amount} VND từ admin.")
            else:
                await update.message.reply_text("User không tồn tại.")
        except:
            await update.message.reply_text("Sai cú pháp. Dùng: /congtien ID 1000")

    elif msg == "/admin" and user_id == str(ADMIN_ID):
        await update.message.reply_text(
            "LỆNH ADMIN:\n"
            "/set_minrut [sotien]\n"
            "/set_ref [sotien]\n"
            "/thongbao [noidung]\n"
            "/congtien [id] [sotien]"
        )

    save_data(data)

async def rut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user = data.get(user_id)

    if not user or user["balance"] < MIN_WITHDRAW:
        await update.message.reply_text("Không đủ điều kiện rút tiền.")
        return

    try:
        acc = update.message.text[5:].strip()
        if not acc:
            raise ValueError("Thông tin không hợp lệ")
        amount = user["balance"]
        keyboard = [
            [InlineKeyboardButton("Duyệt", callback_data=f"approve_{user_id}_{amount}_{acc}")],
            [InlineKeyboardButton("Từ chối", callback_data=f"reject_{user_id}")]
        ]
        text = (
            f"Yêu cầu rút tiền:\n\n"
            f"ID: {user_id}\n"
            f"TÊN: {user['bank']}\n"
            f"STK: {user['acc']}\n"
            f"NGÂN HÀNG: {acc}\n"
            f"Số tiền: {amount} VND"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text("Yêu cầu rút đã được gửi. Vui lòng đợi duyệt.")
    except:
        await update.message.reply_text("Sai cú pháp. Dùng: /rut STK-NGANHANG")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    all_data = load_data()

    if data[0] == "approve":
        uid, amount, acc = data[1], int(data[2]), "_".join(data[3:])
        user = all_data.get(uid)
        if user and user["balance"] >= amount:
            user["balance"] -= amount
            user["history"].append({"time": datetime.now().strftime("%d/%m/%Y %H:%M"), "amount": amount, "acc": acc})
            save_data(all_data)
            await context.bot.send_message(chat_id=int(uid), text="Yêu cầu rút tiền của bạn đã được duyệt!")
            await query.edit_message_text("Đã duyệt yêu cầu rút tiền.")
    elif data[0] == "reject":
        uid = data[1]
        await context.bot.send_message(chat_id=int(uid), text="Yêu cầu rút tiền của bạn đã bị từ chối bởi admin.")
        await query.edit_message_text("Đã từ chối yêu cầu.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rut", rut))

    # Lệnh admin
    app.add_handler(CommandHandler("admin", handle_buttons))
    app.add_handler(CommandHandler("set_minrut", handle_buttons))
    app.add_handler(CommandHandler("set_ref", handle_buttons))
    app.add_handler(CommandHandler("thongbao", handle_buttons))
    app.add_handler(CommandHandler("congtien", handle_buttons))

    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(approve|reject)_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    app.run_polling()

if __name__ == "__main__":
    main()