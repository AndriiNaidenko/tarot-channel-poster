from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from backend.tarot.cards import TarotDeck
from backend.ai.interpreter import TarotInterpreter
import logging

logger = logging.getLogger(__name__)

router = Router()


class ReadingStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_deep_spread_type = State()


def get_back_to_menu_keyboard():
    """Simple keyboard to go back to menu"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Головне меню")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_premium_keyboard():
    """Keyboard with link to premium"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💎 Купить Premium",
                url="https://t.me/taro209"
            )
        ]
    ])
    return keyboard


async def check_limits(message: Message, db, reading_type: str) -> bool:
    """
    Check if user can proceed with reading
    Returns True if can proceed, False if limit reached
    """
    user_id = message.from_user.id
    can_proceed, limit_type = await db.check_and_update_limits(user_id, reading_type)
    
    if not can_proceed:
        if limit_type == "premium_only":
            await message.answer(
                "💎 **Эта функция доступна только в Premium!**\n\n"
                "**Premium включает:**\n"
                "✨ Расклад 5 карт - глубокий анализ\n"
                "✨ Расклад 7 карт - детальное понимание\n"
                "✨ Глубокий путь - твоя судьба\n"
                "✨ Личная энергия - анализ состояния\n"
                "✨ Безлимитные простые расклады\n\n"
                "💬 Для покупки Premium напиши в канал @taro209\n"
                "(Открыты личные сообщения)",
                reply_markup=get_premium_keyboard(),
                parse_mode="Markdown"
            )
        elif limit_type == "card_of_day":
            await message.answer(
                "⏳ **Лимит исчерпан!**\n\n"
                "Карта дня доступна **2 раза в сутки** для бесплатного доступа.\n\n"
                "💎 **Premium:** безлимитный доступ!\n"
                "💬 Напиши в @taro209 для покупки Premium",
                reply_markup=get_premium_keyboard(),
                parse_mode="Markdown"
            )
        elif limit_type == "simple_spread":
            await message.answer(
                "⏳ **Лимит исчерпан!**\n\n"
                "Простые расклады доступны **2 раза в сутки** для бесплатного доступа.\n\n"
                "💎 **Premium:** безлимитный доступ к всем раскладам!\n"
                "💬 Напиши в @taro209 для покупки Premium",
                reply_markup=get_premium_keyboard(),
                parse_mode="Markdown"
            )
        return False
    
    return True


@router.message(F.text == "✨ Карта дня")
async def card_of_day(message: Message, db):
    """Handle "Card of the Day" request"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажми /start")
        return
    
    # Check limits
    if not await check_limits(message, db, "card_of_day"):
        return
    
    # Show "thinking" status with name
    name = user.get('name', 'друг мой')
    
    from datetime import datetime
    hour = datetime.now().hour
    if 0 <= hour < 6:
        greeting = f"Вижу, {name}, ты не спишь... Давай посмотрим, что карты скажут тебе в эту тихую ночь."
    elif 6 <= hour < 11:
        greeting = f"Доброе утро, {name} ✨ Вытягиваю карту дня для тебя..."
    elif 11 <= hour < 17:
        greeting = f"{name}, чувствую твою энергию... Сейчас вытяну карту для тебя."
    elif 17 <= hour < 21:
        greeting = f"Добрый вечер, {name}... Перемешиваю колоду."
    else:
        greeting = f"{name}, давай посмотрим, что карты хотят сказать тебе сегодня..."
    
    await message.answer(greeting)
    
    try:
        # Draw card
        deck = TarotDeck()
        card = deck.draw_card()
        
        # Generate interpretation
        interpreter = TarotInterpreter()
        interpretation = await interpreter.interpret_single_card(card)
        
        # Format response - new beautiful format
        is_reversed = card.get('is_reversed', False)
        reversed_text = " (перевёрнутая)" if is_reversed else ""
        card_name = f"{card['name_ru']}{reversed_text}"
        card_meaning = card['reversed'] if is_reversed else card['upright']
        
        response = f"🌞 **Твоя Карта Дня**\n\n"
        response += f"**Аркан:** {card_name}\n"
        response += f"**Значение:** {card_meaning}\n\n"
        response += f"**Что это значит для тебя:**\n{interpretation}\n\n"
        response += f"✨ Пусть энергия этого дня будет мягкой и благоприятной"
        
        await message.answer(response, parse_mode="Markdown")
        
        # Save to database
        await db.save_reading(
            user_id=user_id,
            reading_type="card_of_day",
            cards=[card],
            interpretation=interpretation
        )
        
        logger.info(f"Card of day generated for user {user_id}: {card['name_ru']}")
        
    except Exception as e:
        logger.error(f"Error generating card of day: {e}")
        await message.answer(
            "😔 Прости, возникла ошибка при чтении карт. Попробуй еще раз позже."
        )


@router.message(F.text == "🔮 Один вопрос")
async def one_question_start(message: Message, state: FSMContext, db):
    """Start one-card reading - ask for question"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажми /start")
        return
    
    # Check limits
    if not await check_limits(message, db, "one_question"):
        return
    
    name = user.get('name', 'друг')
    
    # Ask for question
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"{name}, я слушаю тебя.\n\n"
        f"Сформулируй свой вопрос так, как он звучит внутри.\n"
        f"Карта придёт именно та, которая нужна сейчас.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(ReadingStates.waiting_for_question)
    await state.update_data(reading_type="one_question")


@router.message(F.text == "🌙 Расклад 3 карты")
async def three_card_spread_start(message: Message, state: FSMContext, db):
    """Start 3-card spread - ask for question"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажми /start")
        return
    
    # Check limits
    if not await check_limits(message, db, "three_card_spread"):
        return
    
    name = user.get('name', 'друг')
    
    # Ask for question
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"{name}, расклад из трёх карт — это взгляд на твой путь.\n\n"
        f"Прошлое, Настоящее, Будущее раскроются перед тобой.\n\n"
        f"Задай вопрос — или напиши 'общий' для общего чтения:",
        reply_markup=cancel_keyboard
    )
    await state.set_state(ReadingStates.waiting_for_question)
    await state.update_data(reading_type="three_card_spread")


@router.message(ReadingStates.waiting_for_question, F.text == "❌ Отменить")
@router.message(ReadingStates.waiting_for_deep_spread_type, F.text == "❌ Отменить")
async def cancel_reading(message: Message, state: FSMContext):
    """Cancel reading"""
    from .start import get_main_menu_keyboard
    await state.clear()
    await message.answer(
        "Хорошо, возвращаемся в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(ReadingStates.waiting_for_question)
async def execute_reading(message: Message, state: FSMContext, db):
    """Execute reading based on type (one question or 3-card spread)"""
    user_id = message.from_user.id
    question = message.text.strip()
    
    # Get reading type from state
    user_data = await state.get_data()
    reading_type = user_data.get('reading_type', 'three_card_spread')
    
    if question.lower() == "общий" or question.lower() == "общее":
        question = None
        question_display = "Общее чтение"
    else:
        question_display = question
    
    await state.clear()
    
    # Show "thinking" status
    from .start import get_main_menu_keyboard
    
    thinking_phrases = [
        "Чувствую энергию твоего вопроса... Вытягиваю карты.",
        "Перемешиваю колоду, настраиваюсь на твою ситуацию...",
        "Карты уже знают ответ... Сейчас я его увижу.",
        "Давай посмотрим, что карты хотят сказать тебе..."
    ]
    
    import random
    await message.answer(
        random.choice(thinking_phrases),
        reply_markup=get_main_menu_keyboard()
    )
    
    try:
        deck = TarotDeck()
        interpreter = TarotInterpreter()
        
        if reading_type == "deep_spread":
            # DEEP SPREAD (5, 7 cards or Deep Path)
            spread_type = user_data.get('spread_type', '5_cards')
            
            # Determine number of cards
            cards_count = 5 if spread_type == "5_cards" else 7
            
            cards = deck.draw_cards(cards_count)
            interpretation = await interpreter.interpret_deep_spread(cards, spread_type, question)
            
            # Spread names
            spread_names = {
                "5_cards": "Расклад на 5 карт",
                "7_cards": "Расклад на 7 карт",
                "deep_path": "Глубинный путь"
            }
            
            spread_emojis = {
                "5_cards": "🔮",
                "7_cards": "✨",
                "deep_path": "🌟"
            }
            
            spread_name = spread_names.get(spread_type, "Глубокий расклад")
            spread_emoji = spread_emojis.get(spread_type, "🔥")
            
            # Format cards list
            cards_names = []
            for i, card in enumerate(cards, 1):
                is_reversed = card.get('is_reversed', False)
                reversed_text = " 🔄" if is_reversed else ""
                cards_names.append(f"{i}. {card['name_ru']}{reversed_text}")
            
            cards_list_text = "\n".join(cards_names)
            
            response = f"{spread_emoji} **{spread_name}**\n\n"
            if question_display != "Общее чтение":
                response += f"📝 Вопрос: _{question_display}_\n\n"
            response += f"**Карты расклада:**\n{cards_list_text}\n\n"
            response += f"**Интерпретация:**\n\n{interpretation}"
            
            await message.answer(response, parse_mode="Markdown")
            
            # Save to database
            await db.save_reading(
                user_id=user_id,
                reading_type=f"deep_spread_{spread_type}",
                cards=cards,
                interpretation=interpretation,
                question=question
            )
            
            logger.info(f"Deep spread generated for user {user_id}: {spread_type}")
            
        elif reading_type == "one_question":
            # ONE CARD READING
            card = deck.draw_card()
            interpretation = await interpreter.interpret_single_card(card, question)
            
            # Format response - new beautiful format
            is_reversed = card.get('is_reversed', False)
            reversed_text = " (перевёрнутая)" if is_reversed else ""
            card_name = f"{card['name_ru']}{reversed_text}"
            card_meaning = card['reversed'] if is_reversed else card['upright']
            
            response = f"🔮 **Ответ на твой вопрос**\n\n"
            response += f"📝 Вопрос: _{question_display}_\n\n"
            response += f"**Аркан:** {card_name}\n"
            response += f"**Смысл карты:** {card_meaning}\n\n"
            response += f"**В контексте твоего вопроса карта говорит:**\n{interpretation}\n\n"
            response += f"✨ Пусть ясность придёт легко и вовремя"
            
            await message.answer(response, parse_mode="Markdown")
            
            # Save to database
            await db.save_reading(
                user_id=user_id,
                reading_type="one_question",
                cards=[card],
                interpretation=interpretation,
                question=question
            )
            
            logger.info(f"One-card reading generated for user {user_id}")
            
        else:
            # THREE CARD SPREAD
            cards = deck.draw_cards(3)
            interpretation = await interpreter.interpret_three_card_spread(cards, question)
            
            # Format response - new beautiful format
            positions = ["Прошлое", "Настоящее", "Будущее"]
            cards_list = []
            
            for i, card in enumerate(cards):
                is_reversed = card.get('is_reversed', False)
                reversed_text = " (перевёрнутая)" if is_reversed else ""
                card_name = f"{card['name_ru']}{reversed_text}"
                card_meaning = card['reversed'] if is_reversed else card['upright']
                cards_list.append(f"**{i+1}) Карта {positions[i].lower()}** — {card_name}\n   Значение: {card_meaning}")
            
            cards_text = "\n\n".join(cards_list)
            
            response = f"🌙 **Твой расклад из 3 карт**\n\n"
            response += f"📝 Вопрос: _{question_display}_\n\n"
            response += f"{cards_text}\n\n"
            response += f"**Что это значит для тебя:**\n{interpretation}\n\n"
            response += f"✨ Пусть твой путь будет ясным и защищённым"
            
            await message.answer(response, parse_mode="Markdown")
            
            # Save to database
            await db.save_reading(
                user_id=user_id,
                reading_type="three_card_spread",
                cards=cards,
                interpretation=interpretation,
                question=question
            )
            
            logger.info(f"3-card spread generated for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating reading: {e}", exc_info=True)
        await message.answer(
            "😔 Прости, возникла ошибка при чтении карт. Попробуй еще раз позже.",
            reply_markup=get_main_menu_keyboard()
        )


@router.message(F.text == "⭐ Совет Таро")
async def tarot_advice(message: Message, db):
    """Give instant tarot advice"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажми /start")
        return
    
    # Check limits
    if not await check_limits(message, db, "tarot_advice"):
        return
    
    name = user.get('name', 'друг')
    
    # Show "thinking" status
    await message.answer(f"{name}, сейчас вытяну карту-совет для тебя...")
    
    try:
        # Draw card
        deck = TarotDeck()
        card = deck.draw_card()
        
        # Generate interpretation as advice
        interpreter = TarotInterpreter()
        interpretation = await interpreter.interpret_single_card(card, question="Какой совет карты могут дать мне прямо сейчас?")
        
        # Format response
        is_reversed = card.get('is_reversed', False)
        reversed_text = " (перевёрнутая)" if is_reversed else ""
        card_name = f"{card['name_ru']}{reversed_text}"
        
        response = f"⭐ **Совет Таро на сейчас**\n\n"
        response += f"**Карта:** {card_name}\n\n"
        response += f"**Послание карты:**\n{interpretation}\n\n"
        response += f"🌙 Пусть этот совет поддержит тебя в нужный момент"
        
        await message.answer(response, parse_mode="Markdown")
        
        # Save to database
        await db.save_reading(
            user_id=user_id,
            reading_type="tarot_advice",
            cards=[card],
            interpretation=interpretation,
            question="Совет Таро"
        )
        
        logger.info(f"Tarot advice generated for user {user_id}: {card['name_ru']}")
        
    except Exception as e:
        logger.error(f"Error generating tarot advice: {e}")
        await message.answer(
            "😔 Прости, возникла ошибка при чтении карт. Попробуй еще раз позже."
        )


@router.message(F.text == "📖 История чтений")
async def my_history(message: Message, db):
    """Show user's reading history"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажми /start")
        return
    
    readings = await db.get_user_readings(user_id, limit=5)
    
    if not readings:
        await message.answer(
            "📖 У тебя пока нет чтений.\n\n"
            "Попробуй получить Карту Дня или сделать Расклад из 3 карт! 🔮"
        )
        return
    
    response = f"📖 **Твоя История Чтений**\n\n"
    response += f"Последние расклады:\n\n"
    
    type_names = {
        "card_of_day": "✨ Карта дня",
        "one_question": "🔮 Один вопрос", 
        "three_card_spread": "🌙 Расклад 3 карты",
        "tarot_advice": "⭐ Совет Таро",
        "deep_spread_5_cards": "🔮 Расклад 5 карт",
        "deep_spread_7_cards": "✨ Расклад 7 карт",
        "deep_spread_deep_path": "🌟 Глубинный путь",
        "personal_energy": "💫 Моя энергетика"
    }
    
    for i, reading in enumerate(readings, 1):
        date = reading['created_at'].strftime("%d.%m.%Y")
        reading_type = type_names.get(reading['type'], reading['type'])
        
        cards_names = []
        for card in reading['cards']:
            name = card.get('name_ru', card.get('name_uk', 'Unknown'))
            if card.get('is_reversed'):
                name += " 🔄"
            cards_names.append(name)
        
        cards_text = ", ".join(cards_names)
        
        response += f"**{i})** {reading_type} — {cards_text} _{date}_\n"
    
    response += "\n✨ Храни в памяти только то, что приносит пользу"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(F.text == "🔥 Глубокий расклад")
async def deep_spread_start(message: Message, state: FSMContext, db):
    """Start deep spread - choose type"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажми /start")
        return
    
    # Check limits - PREMIUM ONLY
    if not await check_limits(message, db, "deep_spread"):
        return
    
    name = user.get('name', 'друг')
    
    # Show spread type selection
    spread_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔮 Расклад 5 карт")],
            [KeyboardButton(text="✨ Расклад 7 карт")],
            [KeyboardButton(text="🌟 Глубинный путь")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        f"{name}, выбери глубину расклада:\n\n"
        f"🔮 **5 карт** — классический углублённый расклад\n"
        f"✨ **7 карт** — детальный взгляд на ситуацию\n"
        f"🌟 **Глубинный путь** — максимальная глубина, путь души\n\n"
        f"Какой расклад резонирует с тобой?",
        reply_markup=spread_keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(ReadingStates.waiting_for_deep_spread_type)


@router.message(ReadingStates.waiting_for_deep_spread_type, F.text.in_(["🔮 Расклад 5 карт", "✨ Расклад 7 карт", "🌟 Глубинный путь"]))
async def deep_spread_ask_question(message: Message, state: FSMContext, db):
    """Ask for question for deep spread"""
    spread_map = {
        "🔮 Расклад 5 карт": "5_cards",
        "✨ Расклад 7 карт": "7_cards",
        "🌟 Глубинный путь": "deep_path"
    }
    
    spread_type = spread_map.get(message.text)
    await state.update_data(reading_type="deep_spread", spread_type=spread_type)
    
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Сформулируй свой вопрос или напиши 'общий' для общего чтения.\n\n"
        "Чем глубже вопрос — тем точнее карты откроют путь.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(ReadingStates.waiting_for_question)


@router.message(ReadingStates.waiting_for_deep_spread_type)
async def deep_spread_invalid_choice(message: Message, state: FSMContext):
    """Handle invalid spread type choice"""
    await message.answer(
        "Пожалуйста, выбери один из вариантов расклада с помощью кнопок 👇"
    )


@router.message(F.text == "💫 Моя энергетика")
async def personal_energy(message: Message, db):
    """Read user's personal energy"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажми /start")
        return
    
    # Check limits - PREMIUM ONLY
    if not await check_limits(message, db, "personal_energy"):
        return
    
    name = user.get('name', 'друг')
    
    await message.answer(f"{name}, настраиваюсь на твою энергию... Сейчас увижу.")
    
    try:
        # Generate energy reading
        interpreter = TarotInterpreter()
        interpretation, cards = await interpreter.interpret_personal_energy(user)
        
        # Format cards
        cards_names = []
        for card in cards:
            is_reversed = card.get('is_reversed', False)
            reversed_text = " 🔄" if is_reversed else ""
            cards_names.append(f"{card['name_ru']}{reversed_text}")
        
        cards_text = ", ".join(cards_names)
        
        response = f"💫 **Твоя Энергетика Сейчас**\n\n"
        response += f"**Карты энергии:** {cards_text}\n\n"
        response += f"{interpretation}"
        
        await message.answer(response, parse_mode="Markdown")
        
        # Save to database
        await db.save_reading(
            user_id=user_id,
            reading_type="personal_energy",
            cards=cards,
            interpretation=interpretation
        )
        
        logger.info(f"Personal energy reading for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating energy reading: {e}", exc_info=True)
        await message.answer(
            "😔 Прости, возникла ошибка при чтении энергии. Попробуй позже."
        )


@router.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: Message, state: FSMContext):
    """Return to main menu"""
    from .start import get_main_menu_keyboard
    await state.clear()
    await message.answer(
        "🏠 Главное меню\n\nВыбирай нужное действие:",
        reply_markup=get_main_menu_keyboard()
    )
