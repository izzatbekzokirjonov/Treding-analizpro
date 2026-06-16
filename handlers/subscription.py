from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    PreCheckoutQuery, SuccessfulPayment
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from database.db import is_premium, save_payment, activate_premium, get_user, get_user_language
from database.db import get_setting, get_all_settings
from locales.texts import t

router = Router()


class PaymentState(StatesGroup):
    waiting_card_receipt = State()
    waiting_ton_receipt = State()


def premium_menu_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Telegram Stars", callback_data="pay_stars")
    builder.button(text="💎 TON", callback_data="pay_ton")
    builder.button(text="💳 Karta (Visa/Uzcard)", callback_data="pay_card")
    builder.button(text=t(lang, "back"), callback_data="main_menu")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def back_keyboard(lang: str, back_cb: str = "premium"):
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "back"), callback_data=back_cb)
    return builder.as_markup()


@router.callback_query(F.data == "premium")
async def cb_premium(callback: CallbackQuery, lang: str = "uz"):
    premium = await is_premium(callback.from_user.id)
    if premium:
        await callback.message.edit_text(
            t(lang, "already_premium"),
            reply_markup=back_keyboard(lang, "main_menu")
        )
        await callback.answer()
        return

    s = await get_all_settings()
    price_uzs = s.get("premium_price_uzs", "50000")
    price_stars = s.get("premium_price_stars", "299")
    price_ton = s.get("premium_price_ton", "5")

    texts = {
        "uz": (
            "💎 <b>Premium Obuna</b>\n\n"
            "✅ Cheksiz tahlil\n"
            "✅ Tez javob\n"
            "✅ Batafsil tahlil\n\n"
            f"💰 <b>Narxlar:</b>\n"
            f"• ⭐ Telegram Stars: {price_stars}\n"
            f"• 💎 TON: {price_ton} TON\n"
            f"• 💳 Karta: {price_uzs} so'm\n\n"
            "To'lov usulini tanlang:"
        ),
        "ru": (
            "💎 <b>Premium Подписка</b>\n\n"
            "✅ Безлимитный анализ\n"
            "✅ Быстрый ответ\n"
            "✅ Подробный анализ\n\n"
            f"💰 <b>Цены:</b>\n"
            f"• ⭐ Telegram Stars: {price_stars}\n"
            f"• 💎 TON: {price_ton} TON\n"
            f"• 💳 Карта: {price_uzs} сум\n\n"
            "Выберите способ оплаты:"
        ),
        "en": (
            "💎 <b>Premium Subscription</b>\n\n"
            "✅ Unlimited analysis\n"
            "✅ Fast response\n"
            "✅ Detailed analysis\n\n"
            f"💰 <b>Prices:</b>\n"
            f"• ⭐ Telegram Stars: {price_stars}\n"
            f"• 💎 TON: {price_ton} TON\n"
            f"• 💳 Card: {price_uzs} UZS\n\n"
            "Choose payment method:"
        ),
    }

    await callback.message.edit_text(
        texts.get(lang, texts["uz"]),
        reply_markup=premium_menu_keyboard(lang)
    )
    await callback.answer()


# ─── Telegram Stars ───────────────────────────────────────
@router.callback_query(F.data == "pay_stars")
async def cb_pay_stars(callback: CallbackQuery, lang: str = "uz"):
    price_stars = await get_setting("premium_price_stars")
    stars_amount = int(price_stars) if price_stars.isdigit() else 299

    titles = {"uz": "💎 Premium Obuna (1 oy)", "ru": "💎 Premium Подписка (1 мес)", "en": "💎 Premium Subscription (1 month)"}
    descs = {"uz": "Cheksiz grafik tahlil", "ru": "Безлимитный анализ графиков", "en": "Unlimited chart analysis"}

    await callback.message.answer_invoice(
        title=titles.get(lang, titles["uz"]),
        description=descs.get(lang, descs["en"]),
        payload="premium_stars",
        currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=stars_amount)]
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, lang: str = "uz"):
    payment: SuccessfulPayment = message.successful_payment
    if payment.invoice_payload == "premium_stars":
        await activate_premium(message.from_user.id, days=30)
        user = await get_user(message.from_user.id)
        until = user["premium_until"][:10] if user and user["premium_until"] else ""
        await message.answer(t(lang, "premium_activated", until=until))

        for admin_id in config.ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"⭐ <b>Stars to'lov!</b>\n"
                    f"👤 {message.from_user.full_name} (@{message.from_user.username})\n"
                    f"🆔 <code>{message.from_user.id}</code>\n"
                    f"💰 {payment.total_amount} Stars"
                )
            except Exception:
                pass


# ─── TON Payment ──────────────────────────────────────────
@router.callback_query(F.data == "pay_ton")
async def cb_pay_ton(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    ton_wallet = await get_setting("ton_wallet")
    price_ton = await get_setting("premium_price_ton")

    if not ton_wallet:
        no_wallet = {
            "uz": "❌ TON hamyon hali sozlanmagan. Admin bilan bog'laning.",
            "ru": "❌ TON кошелёк ещё не настроен. Свяжитесь с админом.",
            "en": "❌ TON wallet not configured yet. Contact admin."
        }
        await callback.message.edit_text(
            no_wallet.get(lang, no_wallet["uz"]),
            reply_markup=back_keyboard(lang, "premium")
        )
        await callback.answer()
        return

    texts = {
        "uz": (
            f"💎 <b>TON orqali to'lov</b>\n\n"
            f"TON hamyon: <code>{ton_wallet}</code>\n"
            f"Miqdor: <b>{price_ton} TON</b>\n\n"
            f"To'lovni amalga oshirgach, <b>tranzaksiya skrinshotini</b> yuboring.\n\n"
            f"<i>Izoh: tranzaksiyaga Telegram ID ingizni yozing: {callback.from_user.id}</i>"
        ),
        "ru": (
            f"💎 <b>Оплата через TON</b>\n\n"
            f"TON кошелёк: <code>{ton_wallet}</code>\n"
            f"Сумма: <b>{price_ton} TON</b>\n\n"
            f"После оплаты отправьте <b>скриншот транзакции</b>.\n\n"
            f"<i>Укажите в комментарии ваш Telegram ID: {callback.from_user.id}</i>"
        ),
        "en": (
            f"💎 <b>TON Payment</b>\n\n"
            f"TON wallet: <code>{ton_wallet}</code>\n"
            f"Amount: <b>{price_ton} TON</b>\n\n"
            f"After payment, send a <b>transaction screenshot</b>.\n\n"
            f"<i>Add your Telegram ID in comment: {callback.from_user.id}</i>"
        ),
    }

    await callback.message.edit_text(
        texts.get(lang, texts["uz"]),
        reply_markup=back_keyboard(lang, "premium")
    )
    await state.set_state(PaymentState.waiting_ton_receipt)
    await callback.answer()


# ─── Card Payment ─────────────────────────────────────────
@router.callback_query(F.data == "pay_card")
async def cb_pay_card(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    visa_card = await get_setting("visa_card")
    visa_owner = await get_setting("visa_owner")
    price_uzs = await get_setting("premium_price_uzs")

    if not visa_card:
        no_card = {
            "uz": "❌ Karta raqami hali sozlanmagan. Admin bilan bog'laning.",
            "ru": "❌ Номер карты ещё не настроен. Свяжитесь с админом.",
            "en": "❌ Card number not configured yet. Contact admin."
        }
        await callback.message.edit_text(
            no_card.get(lang, no_card["uz"]),
            reply_markup=back_keyboard(lang, "premium")
        )
        await callback.answer()
        return

    texts = {
        "uz": (
            f"💳 <b>Karta orqali to'lov</b>\n\n"
            f"Karta raqami: <code>{visa_card}</code>\n"
            f"Egasi: <b>{visa_owner}</b>\n"
            f"Summa: <b>{price_uzs} so'm</b>\n\n"
            f"To'lovni amalga oshirgach, <b>chek skrinshotini</b> yuboring."
        ),
        "ru": (
            f"💳 <b>Оплата картой</b>\n\n"
            f"Номер карты: <code>{visa_card}</code>\n"
            f"Владелец: <b>{visa_owner}</b>\n"
            f"Сумма: <b>{price_uzs} сум</b>\n\n"
            f"После оплаты отправьте <b>скриншот чека</b>."
        ),
        "en": (
            f"💳 <b>Card Payment</b>\n\n"
            f"Card number: <code>{visa_card}</code>\n"
            f"Owner: <b>{visa_owner}</b>\n"
            f"Amount: <b>{price_uzs} UZS</b>\n\n"
            f"After payment, send a <b>receipt screenshot</b>."
        ),
    }

    await callback.message.edit_text(
        texts.get(lang, texts["uz"]),
        reply_markup=back_keyboard(lang, "premium")
    )
    await state.set_state(PaymentState.waiting_card_receipt)
    await callback.answer()


# ─── Receipt handlers ─────────────────────────────────────
@router.message(PaymentState.waiting_card_receipt, F.photo)
async def handle_card_receipt(message: Message, state: FSMContext, lang: str = "uz"):
    price_uzs = await get_setting("premium_price_uzs")
    payment_id = await save_payment(
        user_id=message.from_user.id,
        amount=f"{price_uzs} UZS",
        payment_type="💳 Karta",
        screenshot_file_id=message.photo[-1].file_id
    )
    await state.clear()
    await message.answer(t(lang, "payment_sent"))
    await _notify_admins_payment(message, payment_id, f"{price_uzs} UZS", "💳 Karta")


@router.message(PaymentState.waiting_ton_receipt, F.photo)
async def handle_ton_receipt(message: Message, state: FSMContext, lang: str = "uz"):
    price_ton = await get_setting("premium_price_ton")
    payment_id = await save_payment(
        user_id=message.from_user.id,
        amount=f"{price_ton} TON",
        payment_type="💎 TON",
        screenshot_file_id=message.photo[-1].file_id
    )
    await state.clear()
    await message.answer(t(lang, "payment_sent"))
    await _notify_admins_payment(message, payment_id, f"{price_ton} TON", "💎 TON")


async def _notify_admins_payment(message: Message, payment_id: int, amount: str, payment_type: str):
    for admin_id in config.ADMIN_IDS:
        try:
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}")
            builder.button(text="❌ Rad etish", callback_data=f"reject_{payment_id}")
            builder.adjust(2)

            caption = (
                f"💳 <b>Yangi to'lov #{payment_id}</b>\n\n"
                f"👤 {message.from_user.full_name} (@{message.from_user.username or 'no_username'})\n"
                f"🆔 <code>{message.from_user.id}</code>\n"
                f"💰 {amount}\n"
                f"📱 {payment_type}"
            )

            await message.bot.send_photo(
                admin_id,
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_markup=builder.as_markup()
            )
        except Exception:
            pass


from aiogram.types import Message
from aiogram.filters import Filter
from aiogram import F

@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, lang: str = "uz"):
    import json
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")
        
        if action == "analyze":
            await message.answer(t(lang, "send_screenshot"))
        elif action == "pay_stars":
            from config import config
            from database.db import get_setting
            price_stars = await get_setting("premium_price_stars")
            stars_amount = int(price_stars) if price_stars and price_stars.isdigit() else 299
            await message.answer_invoice(
                title="💎 Premium Obuna",
                description="1 oylik cheksiz tahlil",
                payload="premium_stars",
                currency="XTR",
                prices=[{"label": "Premium", "amount": stars_amount}]
            )
        elif action == "pay_ton":
            await message.answer(t(lang, "card_payment"))
        elif action == "pay_card":
            await message.answer(t(lang, "card_payment"))
    except Exception as e:
        await message.answer(t(lang, "error"))
