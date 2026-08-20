import os
import json
from dotenv import load_dotenv
import asyncio
import logging
import re
from typing import List, Dict, Optional, Set
import gspread
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime

load_dotenv()  # загружает переменные из .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
# ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_ID = {
    int(x.strip())
    for x in os.getenv("ADMIN_ID", "").split(",")
    if x.strip()
}

CHANNEL_URL = "https://t.me/danang_speed_dates"

SHEET_ID_RU = "1FWsgrOyBs_57EFnRTBDRiyFwSuBPSktMAB-WMdABd0g"
SHEET_ID_EN = "1QuZ2LocrhXyk99KixotqO1x8BZwRHtIH5BGLf75q3P0"

COLUMNS = {
    "ru": {
        "name": "Имя",
        "age": "Возраст",
        "gender": "Пол",
        "contact": "Ваш Telegram (например @username)",
        "languages": "Какими языками вы владеете?",
        "looking_for": "Что вы надеетесь найти на этом мероприятии?",
        "timestamp": "Время",
        "status": "Status",
        "user_id": "user_id",
        "tg_username": "tg_username",
    },
    "en": {
        "name": "Name",
        "age": "Age",
        "gender": "Gender",
        "contact": "Your Telegram/WhatsApp/Instagram",
        "languages": "What languages do you speak comfortably?",
        "looking_for": "What are you hoping to find at this event?",
        "timestamp": "Timestamp",
        "status": "Status",
        "user_id": "user_id",
        "tg_username": "tg_username",
    }
}
# =======================================================


class Form(StatesGroup):
    name = State()
    age = State()
    gender = State()
    languages = State()
    looking_for = State()


class MatchState(StatesGroup):
    choosing_first = State()
    choosing_second = State()


# ---------- вопросы ----------
TEXTS = {
    "ru": {
        "choose_lang": "Выбери язык / Choose language:",
        "start_form": "Отлично! Давай заполним анкету.\n\nКак тебя зовут?",
        "ask_age": "Сколько тебе лет?",
        "ask_gender": "Твой пол:",
        # "ask_nationality": "Твоя национальность:",
        # "ask_city": "Где ты живёшь?",
        # "ask_how_long": "Как давно ты в Дананге?",
        "ask_languages": "Какими языками владеешь?\n(можно несколько)",
        "ask_looking_for": "Что ты надеешься найти на мероприятии?",
        # "ask_pref_age": "Предпочтительный возрастной диапазон партнёра:",
        # "ask_values": "Что ты больше всего ценишь в других? (до 3)",
        # "ask_other_cultures": "Комфортно ли тебе знакомиться с людьми из других стран/культур?",
        # "ask_temporary": "Комфортно ли встречаться с человеком, который временно живёт в Дананге?",
        "form_done": "Анкета успешно сохранена!\n\nМы подберём тебе пару. Перейди в канал, чтобы узнать дату мероприятия.",
        "btn_channel": "→ Перейти в канал",
        "btn_back": "← Назад",
        "gender_m": "Мужской",
        "gender_f": "Женский",
        "city_dn": "Дананг",
        "city_ha": "Хой Ан",
        "city_other": "Другое",
        "done": "✅ Готово",
        "error_number": "Пожалуйста, введи число.",
        "error_age_range": "Возраст должен быть от 18 до 70 лет.",
        "error_name": "Имя должно содержать только буквы (2–30 символов).",
        "error_nationality": "Национальность должна содержать только буквы (2–30 символов).",
        "error_pref_age": "Введи только цифры (например: 25 или 25-32).",
        "error_text": "Слишком короткий ответ. Напиши подробнее.",
    },
    "en": {
        "choose_lang": "Выбери язык / Choose language:",
        "start_form": "Great! Let's fill the form.\n\nWhat's your name?",
        "ask_age": "How old are you?",
        "ask_gender": "Your gender:",
        # "ask_nationality": "Your nationality:",
        # "ask_city": "Where do you live?",
        # "ask_how_long": "How long have you been in Da Nang?",
        "ask_languages": "What languages do you speak comfortably?\n(multiple choice)",
        "ask_looking_for": "What are you hoping to find at this event?",
        # "ask_pref_age": "Preferred age range of partner:",
        # "ask_values": "What do you value most in another person? (up to 3)",
        # "ask_other_cultures": "Are you comfortable meeting someone from another country/culture?",
        # "ask_temporary": "Are you comfortable dating someone who lives in Da Nang temporarily?",
        "form_done": "Form saved successfully!\n\nWe will find a match for you. Go to the channel to find out the date of the event.",
        "btn_channel": "→ Go to the channel",
        "btn_back": "← Back",
        "gender_m": "Male",
        "gender_f": "Female",
        "city_dn": "Da Nang",
        "city_ha": "Hoi An",
        "city_other": "Other",
        "done": "✅ Done",
        "error_number": "Please enter a number.",
        "error_age_range": "Age must be between 18 and 70.",
        "error_name": "Name must contain only letters (2–30 characters).",
        "error_nationality": "Nationality must contain only letters (2–30 characters).",
        "error_pref_age": "Enter only digits (e.g. 25 or 25-32).",
        "error_text": "Answer is too short. Please write more.",
    }
}

# Варианты ответов
OPTIONS = {
    "ru": {
        "languages": ["Английский", "Вьетнамский", "Русский", "Другое"],
        "looking_for": ["Дружеские встречи", "Свидания"],
    },
    "en": {
        "languages": ["English", "Vietnamese", "Russian", "Other"],
        "looking_for": ["Just meeting interesting people", "Dating"],
    }
}


# ---------- Helpers ----------
def is_valid_name(text: str) -> bool:
    """Имя: только буквы, пробелы, дефисы. Длина 2-30."""
    text = text.strip()
    if not (2 <= len(text) <= 30):
        return False
    return bool(re.fullmatch(r"[A-Za-zА-Яа-яЁёІіЇїЄєҐґ\s\-']+", text))


def is_valid_pref_age(text: str) -> bool:
    """Предпочтительный возраст: только цифры или диапазон 25-32."""
    text = text.strip()
    return bool(re.fullmatch(r"\d{1,2}(-\d{1,2})?", text))


def get_back_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS[lang]["btn_back"])]],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def single_choice_kb_with_back(options: List[str], prefix: str, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"{prefix}:{i}")
    builder.button(text=TEXTS[lang]["btn_back"], callback_data=f"back:{prefix}")
    builder.adjust(1)
    return builder.as_markup()


# ---------- Google Sheets ----------
# def get_client():
#     return gspread.service_account(filename="service_account.json")

def get_client():
    creds_json = os.getenv("SERVICE_ACCOUNT_JSON")
    if not creds_json:
        # Fallback для локального развития
        return gspread.service_account(filename="service_account.json")
    try:
        creds_dict = json.loads(creds_json)
        return gspread.service_account_from_dict(creds_dict)
    except json.JSONDecodeError:
        raise ValueError("SERVICE_ACCOUNT_JSON is not valid JSON")

def save_to_sheet(lang: str, data: dict, user_id: int, username: str):
     logging.info("=== SAVE_TO_SHEET CALLED ===")
     logging.info(f"lang={lang}, user_id={user_id}")
     client = get_client()
     sheet_id = SHEET_ID_RU if lang == "ru" else SHEET_ID_EN
     logging.info(f"SHEET_ID: {sheet_id}")
 
     sheet = client.open_by_key(sheet_id).sheet1
     cols = COLUMNS[lang]
     logging.info(f"COLS: {cols}")
 
     headers = [h.strip() for h in sheet.row_values(1)]
     logging.info(f"HEADERS: {headers}")
    
     
     row = []
     for header in headers:
         if header == cols["name"]:
             row.append(data.get("name", ""))
         elif header == cols["age"]:
             row.append(data.get("age", ""))
         elif header == cols["gender"]:
             row.append(data.get("gender", ""))
         elif header == cols["contact"]:
             row.append(f"@{username}" if username else "")
         elif header == cols["languages"]:
             row.append(", ".join(data.get("languages", [])))
         elif header == cols["looking_for"]:
             row.append(data.get("looking_for", ""))
         elif header == cols.get("timestamp"):
             date_str = datetime.now().strftime(""%d.%m.%Y" %H:%M:%S")
             row.append(date_str)
             logging.info(f"✅ TIMESTAMP WRITTEN: {date_str}")
         elif header == cols["status"]:
             row.append("")
         elif header == cols["user_id"]:
             row.append(str(user_id))
         elif header == cols["tg_username"]:
             row.append(username or "")
         else:
             row.append("")
     
     all_values = sheet.get_all_values()
     next_row = len(all_values) + 1 if all_values else 1
     
     logging.info(f"ROWS IN SHEET: {len(all_values)}")
     logging.info(f"NEXT ROW: {next_row}")
     logging.info(f"ROW DATA: {row}")
     
     sheet.update(
     values=[row],
     range_name=f"A{next_row}",
     value_input_option="USER_ENTERED"
     )


def get_all_participants() -> List[Dict]:
    client = get_client()
    result = []

    for source, sheet_id in [("ru", SHEET_ID_RU), ("en", SHEET_ID_EN)]:
        try:
            sheet = client.open_by_key(sheet_id).sheet1
            records = sheet.get_all_records()
            cols = COLUMNS[source]

            for idx, row in enumerate(records, start=2):
                status = str(row.get(cols["status"], "")).strip().lower()
                if status.startswith("matched"):
                    continue

                name = str(row.get(cols["name"], "")).strip()
                if not name:
                    continue

                user_id = row.get(cols.get("user_id"))
                try:
                    user_id = int(user_id) if user_id else None
                except:
                    user_id = None

                result.append({
                    "source": source,
                    "row": idx,
                    "name": name,
                    "age": str(row.get(cols["age"], "")).strip(),
                    "gender": "male" if str(row.get(cols["gender"], "")).lower() in ["мужской", "male"] else "female",
                    "contact": str(row.get(cols["contact"], "")).strip(),
                    "user_id": user_id,
                    "username": str(row.get(cols.get("tg_username", ""), "")).strip().lstrip("@"),
                })
        except Exception as e:
            logging.error(f"Ошибка чтения {source}: {e}")

    return result


def mark_as_matched(source: str, row: int, partner_name: str):
    client = get_client()
    sheet_id = SHEET_ID_RU if source == "ru" else SHEET_ID_EN
    sheet = client.open_by_key(sheet_id).sheet1
    headers = sheet.row_values(1)
    try:
        status_col = headers.index("Status") + 1
    except ValueError:
        status_col = len(headers) + 1
        sheet.update_cell(1, status_col, "Status")
    sheet.update_cell(row, status_col, f"matched | {partner_name}")


# ---------- Клавиатуры ----------
def get_language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.adjust(2)
    return builder.as_markup()


def single_choice_kb(options: List[str], prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for i, opt in enumerate(options):
        builder.button(
            text=opt,
            callback_data=f"{prefix}:{i}"
        )

    builder.adjust(1)
    return builder.as_markup()


def multi_choice_kb(options: List[str], selected: Set[str], prefix: str, done_text: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for opt in options:
        mark = "✅ " if opt in selected else ""
        builder.button(text=f"{mark}{opt}", callback_data=f"{prefix}:{opt}")
    builder.button(text=done_text, callback_data=f"{prefix}:done")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👨 Несмэтченные мужчины", callback_data="admin_men")
    builder.button(text="👩 Несмэтченные женщины", callback_data="admin_women")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.adjust(1)
    return builder.as_markup()


def after_form_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=TEXTS[lang]["btn_channel"], url=CHANNEL_URL)
    builder.adjust(1)
    return builder.as_markup()


# ---------- Роутер ----------
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS["ru"]["choose_lang"], reply_markup=get_language_keyboard())


@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    await state.set_state(Form.name)
    await callback.message.edit_text(TEXTS[lang]["start_form"])
    await callback.answer()


# ===== Анкета =====
@router.message(Form.name)
async def form_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    name = message.text.strip()

    if name == TEXTS[lang]["btn_back"]:
        await state.clear()
        await message.answer(TEXTS[lang]["choose_lang"], reply_markup=get_language_keyboard())
        return

    if not is_valid_name(name):
        await message.answer(TEXTS[lang]["error_name"], reply_markup=get_back_kb(lang))
        return

    await state.update_data(name=name)
    await state.set_state(Form.age)
    await message.answer(TEXTS[lang]["ask_age"], reply_markup=get_back_kb(lang))


@router.message(Form.age)
async def form_age(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = message.text.strip()

    if text == TEXTS[lang]["btn_back"]:
        await state.set_state(Form.name)
        await message.answer(TEXTS[lang]["start_form"], reply_markup=get_back_kb(lang))
        return

    if not text.isdigit():
        await message.answer(TEXTS[lang]["error_number"], reply_markup=get_back_kb(lang))
        return

    age = int(text)
    if age < 18 or age > 70:
        await message.answer(TEXTS[lang]["error_age_range"], reply_markup=get_back_kb(lang))
        return

    await state.update_data(age=str(age))
    await state.set_state(Form.gender)

    kb = InlineKeyboardBuilder()
    kb.button(text=TEXTS[lang]["gender_m"], callback_data="gender:male")
    kb.button(text=TEXTS[lang]["gender_f"], callback_data="gender:female")
    kb.button(text=TEXTS[lang]["btn_back"], callback_data="back:gender")
    kb.adjust(2)
    await message.answer(TEXTS[lang]["ask_gender"], reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("gender:"))
async def form_gender(callback: CallbackQuery, state: FSMContext):
    gender_code = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data["lang"]

    if lang == "en":
        gender_value = "Male" if gender_code == "male" else "Female"
    else:
        gender_value = "Мужской" if gender_code == "male" else "Женский"

    await state.update_data(gender=gender_value)
    await state.set_state(Form.languages)
    await state.update_data(languages=set())
    await callback.message.edit_text(
        TEXTS[lang]["ask_languages"],
        reply_markup=multi_choice_kb(
            OPTIONS[lang]["languages"],
            set(),
            "lang",
            TEXTS[lang]["done"]
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def form_languages(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]
    selected: Set[str] = data.get("languages", set())
    value = callback.data.split(":", 1)[1]

    if value == "done":
        if not selected:
            msg = "Выбери хотя бы один язык" if lang == "ru" else "Select at least one language"
            await callback.answer(msg, show_alert=True)
            return
        await state.update_data(languages=list(selected))
        await state.set_state(Form.looking_for)
        await callback.message.edit_text(
            TEXTS[lang]["ask_looking_for"],
            reply_markup=single_choice_kb_with_back(OPTIONS[lang]["looking_for"], "looking", lang)
        )
    else:
        if value in selected:
            selected.remove(value)
        else:
            selected.add(value)
        await state.update_data(languages=selected)
        await callback.message.edit_reply_markup(
            reply_markup=multi_choice_kb(OPTIONS[lang]["languages"], selected, "lang", TEXTS[lang]["done"])
        )
    await callback.answer()


@router.callback_query(F.data.startswith("looking:"))
async def form_looking(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    lang = data["lang"]

    value = OPTIONS[lang]["looking_for"][index]
    await state.update_data(looking_for=value)

    data = await state.get_data()
    user = callback.from_user

    save_to_sheet(
        lang=lang,
        data=data,
        user_id=user.id,
        username=user.username or ""
    )

    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        TEXTS[lang]["form_done"],
        reply_markup=after_form_kb(lang)
    )
    await callback.answer()


# ===== Кнопка «Назад» =====
@router.callback_query(F.data.startswith("back:"))
async def form_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    step = callback.data.split(":")[1]

    if step == "gender":
        await state.set_state(Form.age)
        await callback.message.delete()
        await callback.message.answer(TEXTS[lang]["ask_age"], reply_markup=get_back_kb(lang))
    elif step == "looking":
        await state.set_state(Form.languages)
        await state.update_data(languages=set())
        await callback.message.edit_text(
            TEXTS[lang]["ask_languages"],
            reply_markup=multi_choice_kb(OPTIONS[lang]["languages"], set(), "lang", TEXTS[lang]["done"])
        )
    await callback.answer()




# ===== Админка  =====
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer("Админ-панель:", reply_markup=get_admin_keyboard())


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_ID:
        return
    participants = get_all_participants()
    men = [p for p in participants if p["gender"] == "male"]
    women = [p for p in participants if p["gender"] == "female"]
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"Мужчины: <b>{len(men)}</b>\n"
        f"Женщины: <b>{len(women)}</b>\n"
        f"Всего: <b>{len(participants)}</b>"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({"admin_men", "admin_women"}))
async def admin_list(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        return
    gender = "male" if callback.data == "admin_men" else "female"
    participants = [p for p in get_all_participants() if p["gender"] == gender]
    if not participants:
        await callback.answer("Нет кандидатов", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for p in participants[:40]:
        builder.button(text=f"{p['name']} ({p['age']})", callback_data=f"sel1:{p['source']}:{p['row']}")
    builder.button(text="« Назад", callback_data="admin_back")
    builder.adjust(1)
    await callback.message.edit_text("Выбери человека:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        return

    await state.clear()
    await callback.message.edit_text("Админ-панель:", reply_markup=get_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("sel1:"))
async def select_first(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        return
    _, source, row = callback.data.split(":")
    participants = get_all_participants()
    first = next((p for p in participants if p["source"] == source and p["row"] == int(row)), None)
    if not first:
        await callback.answer("Не найден", show_alert=True)
        return

    await state.update_data(first=first)
    opposite = "female" if first["gender"] == "male" else "male"
    candidates = [p for p in participants if p["gender"] == opposite]

    builder = InlineKeyboardBuilder()
    for p in candidates[:40]:
        builder.button(text=f"{p['name']} ({p['age']})", callback_data=f"sel2:{p['source']}:{p['row']}")
    builder.button(text="« Назад", callback_data="admin_back")
    builder.adjust(1)

    await callback.message.edit_text(
        f"Выбран: <b>{first['name']}</b>\nВыбери пару:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sel2:"))
async def select_second(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        return
    _, source, row = callback.data.split(":")
    data = await state.get_data()
    first = data["first"]
    participants = get_all_participants()
    second = next((p for p in participants if p["source"] == source and p["row"] == int(row)), None)
    if not second:
        await callback.answer("Не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm:{first['source']}:{first['row']}:{second['source']}:{second['row']}")
    builder.button(text="« Отмена", callback_data="admin_back")
    builder.adjust(1)

    await callback.message.edit_text(
        f"<b>Пара:</b>\n{first['name']} ({first['age']}) — {second['name']} ({second['age']})",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_match(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if callback.from_user.id not in ADMIN_ID:
        return

    parts = callback.data.split(":")
    source1, row1, source2, row2 = parts[1], int(parts[2]), parts[3], int(parts[4])

    participants = get_all_participants()
    p1 = next((p for p in participants if p["source"] == source1 and p["row"] == row1), None)
    p2 = next((p for p in participants if p["source"] == source2 and p["row"] == row2), None)

    if not p1 or not p2:
        await callback.answer("Уже сматчены", show_alert=True)
        return

    mark_as_matched(p1["source"], p1["row"], p2["name"])
    mark_as_matched(p2["source"], p2["row"], p1["name"])

    async def send(to_person, about_person):
        if not to_person.get("user_id"):
            return False, "нет user_id"
        text = (
            f"У вас пара!\n\n"
            f"Имя: <b>{about_person['name']}</b>\n"
            f"Возраст: {about_person['age']}\n"
            f"Контакт: @{about_person.get('username') or about_person.get('contact', '')}\n\n"
            f"Хорошего вечера 💫"
        )
        try:
            await bot.send_message(to_person["user_id"], text)
            return True, "отправлено"
        except Exception as e:
            return False, str(e)

    ok1, msg1 = await send(p1, p2)
    ok2, msg2 = await send(p2, p1)

    text = (
        f"✅ Пара создана\n\n"
        f"{p1['name']} → {p2['name']}\n\n"
        f"Сообщение 1: {'✅' if ok1 else '❌'} {msg1}\n"
        f"Сообщение 2: {'✅' if ok2 else '❌'} {msg2}"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await state.clear()
    await callback.answer()


# ---------- Запуск ----------
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

