from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from locales.texts import t

router = Router()


class CalcState(StatesGroup):
    account = State()
    risk = State()
    entry = State()
    stop_loss = State()


def parse_float(text: str):
    try:
        return float(text.replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


@router.message(Command("calculator"))
async def cmd_calculator(message: Message, state: FSMContext, lang: str = "uz"):
    await state.set_state(CalcState.account)
    await message.answer(t(lang, "calc_ask_account"))


@router.callback_query(F.data == "menu_calc")
async def cb_menu_calc(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await state.set_state(CalcState.account)
    await callback.message.answer(t(lang, "calc_ask_account"))
    await callback.answer()


@router.message(Command("cancel"), StateFilter(CalcState))
async def cmd_cancel_calc(message: Message, state: FSMContext, lang: str = "uz"):
    await state.clear()
    await message.answer(t(lang, "calc_cancel"))


@router.message(CalcState.account)
async def process_account(message: Message, state: FSMContext, lang: str = "uz"):
    val = parse_float(message.text)
    if not val or val <= 0:
        await message.answer(t(lang, "calc_invalid"))
        return
    await state.update_data(account=val, lang=lang)
    await state.set_state(CalcState.risk)
    await message.answer(t(lang, "calc_ask_risk"))


@router.message(CalcState.risk)
async def process_risk(message: Message, state: FSMContext, lang: str = "uz"):
    val = parse_float(message.text)
    if not val or val <= 0 or val > 100:
        await message.answer(t(lang, "calc_invalid"))
        return
    await state.update_data(risk=val)
    await state.set_state(CalcState.entry)
    await message.answer(t(lang, "calc_ask_entry"))


@router.message(CalcState.entry)
async def process_entry(message: Message, state: FSMContext, lang: str = "uz"):
    val = parse_float(message.text)
    if not val or val <= 0:
        await message.answer(t(lang, "calc_invalid"))
        return
    await state.update_data(entry=val)
    await state.set_state(CalcState.stop_loss)
    await message.answer(t(lang, "calc_ask_sl"))


@router.message(CalcState.stop_loss)
async def process_stop_loss(message: Message, state: FSMContext, lang: str = "uz"):
    val = parse_float(message.text)
    if not val or val <= 0:
        await message.answer(t(lang, "calc_invalid"))
        return

    data = await state.get_data()
    await state.clear()

    account: float = data["account"]
    risk_pct: float = data["risk"]
    entry: float = data["entry"]
    sl: float = val
    lang = data.get("lang", lang)

    if entry == sl:
        await message.answer(t(lang, "calc_invalid"))
        return

    risk_amount = account * risk_pct / 100
    distance = abs(entry - sl)
    distance_pct = distance / entry * 100
    position = risk_amount / distance

    is_long = entry > sl
    if is_long:
        tp1 = entry + distance
        tp2 = entry + 2 * distance
        tp3 = entry + 3 * distance
        direction = {"uz": "🟢 LONG (Buy)", "ru": "🟢 LONG (Покупка)", "en": "🟢 LONG (Buy)"}.get(lang, "🟢 LONG")
    else:
        tp1 = entry - distance
        tp2 = entry - 2 * distance
        tp3 = entry - 3 * distance
        direction = {"uz": "🔴 SHORT (Sell)", "ru": "🔴 SHORT (Продажа)", "en": "🔴 SHORT (Sell)"}.get(lang, "🔴 SHORT")

    await message.answer(
        t(lang, "calc_result",
          account=f"{account:,.2f}",
          risk=f"{risk_pct:.1f}",
          direction=direction,
          entry=f"{entry:,.4f}",
          sl=f"{sl:,.4f}",
          risk_amount=f"{risk_amount:.2f}",
          distance=f"{distance:.4f}",
          distance_pct=f"{distance_pct:.2f}",
          position=f"{position:.4f}",
          tp1=f"{tp1:,.4f}",
          tp2=f"{tp2:,.4f}",
          tp3=f"{tp3:,.4f}")
    )
