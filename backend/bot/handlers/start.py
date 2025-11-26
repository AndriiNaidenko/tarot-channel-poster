from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from backend.bot.subscription_check import (
    check_user_subscribed, 
    get_subscription_keyboard,
    SUBSCRIPTION_MESSAGE,
    REQUIRED_CHANNEL
)

logger = logging.getLogger(__name__)

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_birthdate = State()
    waiting_for_zodiac = State()


def get_main_menu_keyboard():
    """Main menu keyboard with all bot features"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✨ Карта дня"),
                KeyboardButton(text="🔮 Один вопрос")
            ],
            [
                KeyboardButton(text="🌙 Расклад 3 карты"),
                KeyboardButton(text="🔥 Глубокий расклад")
            ],
            [
                KeyboardButton(text="💫 Моя энергетика"),
                KeyboardButton(text="⭐ Совет Таро")
            ],
            [
                KeyboardButton(text="📖 История чтений"),
                KeyboardButton(text="ℹ️ О боте")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


def get_zodiac_keyboard():
    """Keyboard for selecting zodiac sign"""
    signs = [
        "♈️ Овен", "♉️ Телец", "♊️ Близнецы",
        "♋️ Рак", "♌️ Лев", "♍️ Дева",
        "♎️ Весы", "♏️ Скорпион", "♐️ Стрелец",
        "♑️ Козерог", "♒️ Водолей", "♓️ Рыбы"
    ]
    
    keyboard = []
    for i in range(0, len(signs), 3):
        row = [KeyboardButton(text=sign) for sign in signs[i:i+3]]
        keyboard.append(row)
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db, bot: Bot):
    """Handle /start command - check subscription first, then registration or welcome back"""
    user_id = message.from_user.id
    
    # Check if user is subscribed to required channel
    is_subscribed = await check_user_subscribed(bot, user_id)
    
    if not is_subscribed:
        # User not subscribed - show subscription requirement
        await message.answer(
            SUBSCRIPTION_MESSAGE.format(channel=REQUIRED_CHANNEL),
            reply_markup=get_subscription_keyboard(),
            parse_mode="Markdown"
        )
        logger.info(f"User {user_id} not subscribed to {REQUIRED_CHANNEL}")
        return
    
    # User is subscribed - continue with normal flow
    user = await db.get_user(user_id)
    
    if user:
        # User already registered
        await message.answer(
            f"Приветствую тебя снова, {user['name']}… ✨\n\n"
            f"Я — твой мистический проводник в мире Таро.\n"
            f"Каждая карта — это подсказка, которая помогает увидеть путь, успокоиться и принять верное решение.\n\n"
            f"Спроси то, что тебя волнует — и я дам тебе ясность.\n"
            f"Что хочешь узнать сегодня?",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # New user - start registration
        await message.answer(
            "Приветствую тебя… ✨\n\n"
            "Я — твой мистический проводник в мире Таро.\n"
            "Каждая карта — это подсказка, которая помогает увидеть путь, успокоиться и принять верное решение.\n\n"
            "Спроси то, что тебя волнует — и я дам тебе ясность.\n\n"
            "Для начала, как мне тебя называть?"
        )
        await state.set_state(RegistrationStates.waiting_for_name)
        logger.info(f"New user started registration: {user_id}")


@router.message(RegistrationStates.waiting_for_name, Command("start"))
async def restart_during_name(message: Message, state: FSMContext, db):
    """Allow restarting registration"""
    await state.clear()
    await cmd_start(message, state, db)


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext, db):
    """Process user's name during registration"""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 50:
        await message.answer("Пожалуйста, введи корректное имя (2-50 символов)")
        return
    
    # Save name to state
    await state.update_data(name=name)
    
    await message.answer(
        f"Приятно познакомиться, {name}! 🌟\n\n"
        f"Укажи свою дату рождения в формате ДД.ММ.ГГГГ\n"
        f"(например: 15.03.1990)"
    )
    await state.set_state(RegistrationStates.waiting_for_birthdate)


@router.message(RegistrationStates.waiting_for_birthdate, Command("start"))
async def restart_during_birthdate(message: Message, state: FSMContext, db):
    """Allow restarting registration"""
    await state.clear()
    await cmd_start(message, state, db)


@router.message(RegistrationStates.waiting_for_birthdate)
async def process_birthdate(message: Message, state: FSMContext, db):
    """Process user's birthdate during registration"""
    from datetime import datetime
    
    birthdate_text = message.text.strip()
    
    try:
        # Parse date in format DD.MM.YYYY
        birthdate = datetime.strptime(birthdate_text, "%d.%m.%Y")
        
        # Validate reasonable date range
        if birthdate.year < 1900 or birthdate > datetime.now():
            await message.answer("Пожалуйста, укажи корректную дату рождения")
            return
        
        # Save birthdate to state
        await state.update_data(birthdate=birthdate_text)
        
        await message.answer(
            f"Отлично! ✨\n\n"
            f"Теперь выбери свой знак зодиака:",
            reply_markup=get_zodiac_keyboard()
        )
        await state.set_state(RegistrationStates.waiting_for_zodiac)
        
    except ValueError:
        await message.answer(
            "Неверный формат даты. Пожалуйста, используй формат ДД.ММ.ГГГГ\n"
            "Например: 15.03.1990"
        )


@router.message(RegistrationStates.waiting_for_zodiac, Command("start"))
async def restart_during_zodiac(message: Message, state: FSMContext, db):
    """Allow restarting registration"""
    await state.clear()
    await cmd_start(message, state, db)


@router.message(RegistrationStates.waiting_for_zodiac)
async def process_zodiac(message: Message, state: FSMContext, db):
    """Process zodiac sign and complete registration"""
    zodiac_map = {
        "♈️ Овен": "Овен", "♉️ Телец": "Телец", "♊️ Близнецы": "Близнецы",
        "♋️ Рак": "Рак", "♌️ Лев": "Лев", "♍️ Дева": "Дева",
        "♎️ Весы": "Весы", "♏️ Скорпион": "Скорпион", "♐️ Стрелец": "Стрелец",
        "♑️ Козерог": "Козерог", "♒️ Водолей": "Водолей", "♓️ Рыбы": "Рыбы"
    }
    
    zodiac_text = message.text.strip()
    zodiac = zodiac_map.get(zodiac_text)
    
    if not zodiac:
        await message.answer(
            "Пожалуйста, выбери знак зодиака с клавиатуры 👇",
            reply_markup=get_zodiac_keyboard()
        )
        return
    
    # Get name and birthdate from state
    user_data = await state.get_data()
    name = user_data.get('name')
    birthdate = user_data.get('birthdate')
    
    # Create user in database
    user_id = message.from_user.id
    username = message.from_user.username or ""
    await db.create_user(user_id, name, username, birthdate)
    await db.update_zodiac(user_id, zodiac)
    
    await message.answer(
        f"✨ Спасибо, {name}! Регистрация завершена.\n\n"
        f"🔮 Твой знак: {zodiac}\n"
        f"📅 Дата рождения: {birthdate}\n\n"
        f"Теперь карты готовы дать тебе ясность.\n"
        f"Что хочешь узнать сегодня?",
        reply_markup=get_main_menu_keyboard()
    )
    
    await state.clear()
    logger.info(f"User registered: {user_id} - {name} - {zodiac}")


@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery, state: FSMContext, db, bot: Bot):
    """Handle 'I subscribed' button click"""
    user_id = callback.from_user.id
    
    # Check subscription again
    is_subscribed = await check_user_subscribed(bot, user_id)
    
    if is_subscribed:
        # User subscribed - allow access
        await callback.message.edit_text(
            "✅ Отлично! Ты подписался на канал!\n\n"
            "Теперь можешь пользоваться всеми функциями бота. 🔮\n\n"
            "Отправь /start для начала работы."
        )
        await callback.answer("✅ Подписка подтверждена!")
        logger.info(f"User {user_id} subscription confirmed")
    else:
        # Still not subscribed
        await callback.answer(
            "❌ Ты ещё не подписался на канал! Подпишись и нажми кнопку снова.",
            show_alert=True
        )
        logger.info(f"User {user_id} still not subscribed")


@router.message(Command("help"))
@router.message(F.text == "ℹ️ О боте")
async def cmd_help(message: Message):
    """Show help information"""
    help_text = """ℹ️ **О боте**

Этот бот — цифровой таролог, созданный, чтобы давать ясность в важных ситуациях.
Он помогает увидеть энергию дня, понять направление событий и мягко подсказать, как действовать.

**Доступные функции:**

✨ **Карта дня** — узнай энергию сегодняшнего дня

🔮 **Один вопрос** — получи ответ на конкретный вопрос (1 карта)

🌙 **Расклад 3 карты** — прошлое, настоящее, будущее

🔥 **Глубокий расклад** — расклады на 5, 7 карт или Глубинный путь

💫 **Моя энергетика** — чтение личной энергии и состояния

⭐ **Совет Таро** — мгновенная подсказка от карт

📖 **История чтений** — просмотр предыдущих раскладов

**Команды:**
/start - начать работу с ботом
/help - эта справка

Задай свой вопрос — и карты подскажут путь."""
    
    await message.answer(help_text, parse_mode="Markdown")
