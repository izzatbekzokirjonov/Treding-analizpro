from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from database.db import (
    get_all_users, get_pending_payments,
    approve_payment, reject_payment,
    activate_premium, get_user,
    get_all_settings, get_setting, set_setting,
    get_user_language
)
from locales.texts import t

router = Router()


# ─── States ───────────────────────────────────────────────
class AdminState(StatesGroup):
    broadcast = State()
    give_premium_id = State()
    # Channel settings
    set_channel_id = State()
    set_channel_username = State()
    # Payment settings
    set_ton_wallet = State()
    set_visa_card = State()
    set_visa_owner = State()
    set_price_uzs = State()
    set_price_stars = State()
    set_price_ton = State()


# ─── Helpers ──────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def on_off(val: str) -> str:
    return "✅ Yoqilgan" if val == "1" else "❌ O'chirilgan"


# ─── Main Admin Panel ──────────────────────────────────────
def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="adm_stats")
    builder.button(text="💳 To'lovlar", callback_data="adm_payments")
    builder.button(text="📢 Kanal sozlama", callback_data="adm_channel")
    builder.button(text="💰 To'lov sozlama", callback_data="adm_payment_settings")
    builder.button(text="👑 Premium berish", callback_data="adm_give_premium")
    builder.button(text="📣 Xabar yuborish", callback_data="adm_broadcast")
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: Message, lang: str = "uz"):
    if not is_admin(message.from_user.id):
        await message.answer(t(lang, "admin_only"))
        return
    await message.answer("🔧 <b>Admin Panel</b>", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "adm_main")
async def cb_admin_main(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text("🔧 <b>Admin Panel</b>", reply_markup=admin_main_keyboard())
    await callback.answer()


# ─── Statistics ───────────────────────────────────────────
@router.callback_query(F.data == "adm_stats")
async def cb_stats(callback: CallbackQuery, lang: str = "uz"):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return

    users = await get_all_users()
    total = len(users)
    premium_count = sum(1 for u in users if u["is_premium"])
    total_analyses = sum(u["analysis_count"] for u in users)
    pending = await get_pending_payments()

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data="adm_main")

    await callback.message.edit_text(
        t(lang, "stats",
          total=total,
          premium=premium_count,
          analyses=total_analyses,
          pending=len(pending)),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# ─── Channel Settings ─────────────────────────────────────
@router.callback_query(F.data == "adm_channel")
async def cb_channel_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return

    s = await get_all_settings()
    channel_id = s.get("channel_id", "") or "❌ Kiritilmagan"
    channel_username = s.get("channel_username", "") or "❌ Kiritilmagan"
    required = on_off(s.get("channel_required", "0"))
    auto_post = on_off(s.get("channel_auto_post", "0"))

    text = (
        "📢 <b>Kanal Sozlamalari</b>\n\n"
        f"🆔 Channel ID: <code>{channel_id}</code>\n"
        f"👤 Username: {channel_username}\n"
        f"🔒 Majburiy obuna: {required}\n"
        f"📤 Auto post: {auto_post}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🆔 Channel ID kiriting", callback_data="adm_set_channel_id")
    builder.button(text="👤 Username kiriting", callback_data="adm_set_channel_username")
    builder.button(text=f"🔒 Majburiy: {required}", callback_data="adm_toggle_required")
    builder.button(text=f"📤 Auto post: {auto_post}", callback_data="adm_toggle_autopost")
    builder.button(text="◀️ Orqaga", callback_data="adm_main")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm_toggle_required")
async def cb_toggle_required(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    current = await get_setting("channel_required")
    new_val = "0" if current == "1" else "1"
    await set_setting("channel_required", new_val)
    await cb_channel_settings(callback)


@router.callback_query(F.data == "adm_toggle_autopost")
async def cb_toggle_autopost(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    current = await get_setting("channel_auto_post")
    new_val = "0" if current == "1" else "1"
    await set_setting("channel_auto_post", new_val)
    await cb_channel_settings(callback)


@router.callback_query(F.data == "adm_set_channel_id")
async def cb_set_channel_id(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text(
        "🆔 Kanal ID ni kiriting.\n\n"
        "<i>Masalan: -1001234567890</i>\n\n"
        "ID olish uchun: @userinfobot ga kanaldan forward qiling"
    )
    await state.set_state(AdminState.set_channel_id)
    await callback.answer()


@router.message(AdminState.set_channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("channel_id", message.text.strip())
    await state.clear()
    await message.answer(f"✅ Channel ID saqlandi: <code>{message.text.strip()}</code>",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="📢 Kanal sozlama", callback_data="adm_channel"
                         ).as_markup())


@router.callback_query(F.data == "adm_set_channel_username")
async def cb_set_channel_username(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text(
        "👤 Kanal username kiriting.\n\n"
        "<i>Masalan: @mychannel yoki mychannel</i>"
    )
    await state.set_state(AdminState.set_channel_username)
    await callback.answer()


@router.message(AdminState.set_channel_username)
async def process_channel_username(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    username = message.text.strip().lstrip("@")
    await set_setting("channel_username", username)
    await state.clear()
    await message.answer(f"✅ Channel username saqlandi: @{username}",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="📢 Kanal sozlama", callback_data="adm_channel"
                         ).as_markup())


# ─── Payment Settings ─────────────────────────────────────
@router.callback_query(F.data == "adm_payment_settings")
async def cb_payment_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return

    s = await get_all_settings()
    ton = s.get("ton_wallet", "") or "❌ Kiritilmagan"
    visa = s.get("visa_card", "") or "❌ Kiritilmagan"
    visa_owner = s.get("visa_owner", "") or "❌ Kiritilmagan"
    price_uzs = s.get("premium_price_uzs", "50000")
    price_stars = s.get("premium_price_stars", "299")
    price_ton = s.get("premium_price_ton", "5")

    text = (
        "💰 <b>To'lov Sozlamalari</b>\n\n"
        f"💎 <b>TON Hamyon:</b>\n<code>{ton}</code>\n\n"
        f"💳 <b>Visa/Uzcard:</b>\n<code>{visa}</code>\n"
        f"👤 Egasi: {visa_owner}\n\n"
        f"📊 <b>Narxlar:</b>\n"
        f"• UZS: {price_uzs} so'm\n"
        f"• Telegram Stars: {price_stars} ⭐\n"
        f"• TON: {price_ton} TON"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💎 TON hamyon", callback_data="adm_set_ton")
    builder.button(text="💳 Visa/Uzcard", callback_data="adm_set_visa")
    builder.button(text="👤 Karta egasi", callback_data="adm_set_visa_owner")
    builder.button(text="💵 Narx (UZS)", callback_data="adm_set_price_uzs")
    builder.button(text="⭐ Narx (Stars)", callback_data="adm_set_price_stars")
    builder.button(text="💎 Narx (TON)", callback_data="adm_set_price_ton")
    builder.button(text="◀️ Orqaga", callback_data="adm_main")
    builder.adjust(2, 2, 2, 1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# TON wallet
@router.callback_query(F.data == "adm_set_ton")
async def cb_set_ton(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text(
        "💎 TON hamyon manzilini kiriting:\n\n"
        "<i>Masalan: UQA1B2C3D4E5F6...</i>"
    )
    await state.set_state(AdminState.set_ton_wallet)
    await callback.answer()


@router.message(AdminState.set_ton_wallet)
async def process_ton_wallet(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("ton_wallet", message.text.strip())
    await state.clear()
    await message.answer("✅ TON hamyon saqlandi!",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="💰 To'lov sozlama", callback_data="adm_payment_settings"
                         ).as_markup())


# Visa card
@router.callback_query(F.data == "adm_set_visa")
async def cb_set_visa(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text(
        "💳 Karta raqamini kiriting:\n\n"
        "<i>Masalan: 8600 1234 5678 9012</i>"
    )
    await state.set_state(AdminState.set_visa_card)
    await callback.answer()


@router.message(AdminState.set_visa_card)
async def process_visa_card(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("visa_card", message.text.strip())
    await state.clear()
    await message.answer("✅ Karta raqami saqlandi!",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="💰 To'lov sozlama", callback_data="adm_payment_settings"
                         ).as_markup())


# Visa owner
@router.callback_query(F.data == "adm_set_visa_owner")
async def cb_set_visa_owner(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text("👤 Karta egasining ismini kiriting:")
    await state.set_state(AdminState.set_visa_owner)
    await callback.answer()


@router.message(AdminState.set_visa_owner)
async def process_visa_owner(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("visa_owner", message.text.strip())
    await state.clear()
    await message.answer("✅ Karta egasi saqlandi!",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="💰 To'lov sozlama", callback_data="adm_payment_settings"
                         ).as_markup())


# Prices
@router.callback_query(F.data == "adm_set_price_uzs")
async def cb_set_price_uzs(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text("💵 Oylik narxni UZS da kiriting (faqat raqam):\n<i>Masalan: 50000</i>")
    await state.set_state(AdminState.set_price_uzs)
    await callback.answer()


@router.message(AdminState.set_price_uzs)
async def process_price_uzs(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    await set_setting("premium_price_uzs", message.text.strip())
    await state.clear()
    await message.answer(f"✅ Narx saqlandi: {message.text.strip()} so'm",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="💰 To'lov sozlama", callback_data="adm_payment_settings"
                         ).as_markup())


@router.callback_query(F.data == "adm_set_price_stars")
async def cb_set_price_stars(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text("⭐ Stars narxini kiriting (faqat raqam):\n<i>Masalan: 299</i>")
    await state.set_state(AdminState.set_price_stars)
    await callback.answer()


@router.message(AdminState.set_price_stars)
async def process_price_stars(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    await set_setting("premium_price_stars", message.text.strip())
    await state.clear()
    await message.answer(f"✅ Narx saqlandi: {message.text.strip()} ⭐",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="💰 To'lov sozlama", callback_data="adm_payment_settings"
                         ).as_markup())


@router.callback_query(F.data == "adm_set_price_ton")
async def cb_set_price_ton(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text("💎 TON narxini kiriting:\n<i>Masalan: 5</i>")
    await state.set_state(AdminState.set_price_ton)
    await callback.answer()


@router.message(AdminState.set_price_ton)
async def process_price_ton(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("premium_price_ton", message.text.strip())
    await state.clear()
    await message.answer(f"✅ Narx saqlandi: {message.text.strip()} TON",
                         reply_markup=InlineKeyboardBuilder().button(
                             text="💰 To'lov sozlama", callback_data="adm_payment_settings"
                         ).as_markup())


# ─── Pending Payments ─────────────────────────────────────
@router.callback_query(F.data == "adm_payments")
async def cb_admin_payments(callback: CallbackQuery, lang: str = "uz"):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return

    pending = await get_pending_payments()
    if not pending:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Orqaga", callback_data="adm_main")
        await callback.message.edit_text(t(lang, "no_pending"), reply_markup=builder.as_markup())
        await callback.answer()
        return

    await callback.message.edit_text(
        f"💳 Kutayotgan to'lovlar: <b>{len(pending)} ta</b>",
        reply_markup=InlineKeyboardBuilder().button(
            text="◀️ Orqaga", callback_data="adm_main"
        ).as_markup()
    )

    for payment in pending:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Tasdiqlash", callback_data=f"approve_{payment['id']}")
        builder.button(text="❌ Rad etish", callback_data=f"reject_{payment['id']}")
        builder.adjust(2)

        text = (
            f"💳 <b>To'lov #{payment['id']}</b>\n\n"
            f"👤 {payment['full_name']} (@{payment['username']})\n"
            f"🆔 <code>{payment['user_id']}</code>\n"
            f"💰 {payment['amount']}\n"
            f"📱 {payment['payment_type']}\n"
            f"📅 {payment['created_at'][:16]}"
        )

        if payment["screenshot_file_id"]:
            await callback.bot.send_photo(
                callback.from_user.id,
                photo=payment["screenshot_file_id"],
                caption=text,
                reply_markup=builder.as_markup()
            )
        else:
            await callback.bot.send_message(
                callback.from_user.id, text, reply_markup=builder.as_markup()
            )

    await callback.answer()


@router.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery, lang: str = "uz"):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return

    payment_id = int(callback.data.replace("approve_", ""))
    user_id = await approve_payment(payment_id, callback.from_user.id)

    if user_id:
        caption = (callback.message.caption or "") + "\n\n✅ <b>TASDIQLANDI</b>"
        try:
            await callback.message.edit_caption(caption=caption)
        except Exception:
            await callback.message.edit_text(callback.message.text + "\n\n✅ <b>TASDIQLANDI</b>")

        user_lang = await get_user_language(user_id)
        user = await get_user(user_id)
        until = user["premium_until"][:10] if user and user["premium_until"] else ""
        try:
            await callback.bot.send_message(
                user_id, t(user_lang, "premium_activated", until=until)
            )
        except Exception:
            pass
        await callback.answer("✅ Premium faollashtirildi!")
    else:
        await callback.answer("❌ Xatolik")


@router.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return

    payment_id = int(callback.data.replace("reject_", ""))
    await reject_payment(payment_id, callback.from_user.id)

    import aiosqlite, os
    async with aiosqlite.connect(os.getenv("DB_PATH", "trading_bot.db")) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)) as cursor:
            payment = await cursor.fetchone()

    if payment:
        user_lang = await get_user_language(payment["user_id"])
        try:
            await callback.bot.send_message(
                payment["user_id"], t(user_lang, "payment_rejected")
            )
        except Exception:
            pass

    try:
        caption = (callback.message.caption or "") + "\n\n❌ <b>RAD ETILDI</b>"
        await callback.message.edit_caption(caption=caption)
    except Exception:
        await callback.message.edit_text(callback.message.text + "\n\n❌ <b>RAD ETILDI</b>")

    await callback.answer("❌ Rad etildi")


# ─── Give Premium ─────────────────────────────────────────
@router.callback_query(F.data == "adm_give_premium")
async def cb_give_premium(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text(
        "👑 Premium bermoqchi bo'lgan foydalanuvchi <b>Telegram ID</b> sini yuboring:\n\n"
        "<i>ID olish uchun foydalanuvchi @userinfobot ga yozsin</i>"
    )
    await state.set_state(AdminState.give_premium_id)
    await callback.answer()


@router.message(AdminState.give_premium_id)
async def process_give_premium(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Faqat raqam (Telegram ID) kiriting!")
        return

    user_id = int(text)
    await activate_premium(user_id, days=30)
    await state.clear()

    user_lang = await get_user_language(user_id)
    user = await get_user(user_id)
    until = user["premium_until"][:10] if user and user["premium_until"] else ""
    try:
        await message.bot.send_message(
            user_id, t(user_lang, "premium_activated", until=until)
        )
    except Exception:
        pass

    await message.answer(
        f"✅ User <code>{user_id}</code> ga 30 kunlik Premium berildi!",
        reply_markup=InlineKeyboardBuilder().button(
            text="◀️ Admin panel", callback_data="adm_main"
        ).as_markup()
    )


# ─── Broadcast ────────────────────────────────────────────
@router.callback_query(F.data == "adm_broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌")
        return
    await callback.message.edit_text(
        "📣 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n\n"
        "<i>HTML format ishlaydi: &lt;b&gt;bold&lt;/b&gt;, &lt;i&gt;italic&lt;/i&gt;</i>"
    )
    await state.set_state(AdminState.broadcast)
    await callback.answer()


@router.message(AdminState.broadcast)
async def process_broadcast(message: Message, state: FSMContext, lang: str = "uz"):
    if not is_admin(message.from_user.id):
        return

    users = await get_all_users()
    count = 0
    for user in users:
        try:
            await message.bot.send_message(user["user_id"], message.text)
            count += 1
        except Exception:
            pass

    await state.clear()
    await message.answer(
        t(lang, "broadcast_done", count=count),
        reply_markup=InlineKeyboardBuilder().button(
            text="◀️ Admin panel", callback_data="adm_main"
        ).as_markup()
    )
