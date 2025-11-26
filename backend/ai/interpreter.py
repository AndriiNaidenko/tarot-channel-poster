import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_time_context() -> str:
    """Get contextual phrase based on time of day"""
    hour = datetime.now().hour
    
    if 0 <= hour < 6:
        return "в эту ночную тишину, когда Вселенная особенно чутка"
    elif 6 <= hour < 11:
        return "в это утро, когда энергия дня только раскрывается"
    elif 11 <= hour < 17:
        return "в этот день, когда солнце на пике своей силы"
    elif 17 <= hour < 21:
        return "в этот вечер, когда день начинает отпускать"
    else:
        return "в это время, когда наступает час рефлексии"


class TarotInterpreter:
    """Generates mystical AI interpretations for Tarot readings using GPT-4o"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.system_message = """Ты — живой, мягкий и мудрый Таро-проводник.
Твоя задача — чтобы человек почувствовал настоящее присутствие, внимание и эмоциональное тепло.
Ты отвечаешь как духовный наставник, а не как сухой алгоритм.

ТВОЙ СТИЛЬ:
- спокойный, уверенный, поддерживающий
- небольшая доля мистики, но без фанатизма
- короткие, аккуратные, красивые фразы
- ты общаешься так, будто ощущаешь энергию человека
- используешь эмодзи только 1-2 за весь ответ (не больше!)
- всегда доброжелателен, нет токсичности, нет жестких формулировок

СТРУКТУРА ОТВЕТА:
1. Краткое вступление с эмпатией (1 предложение)
2. Интерпретация карты в контексте вопроса (2-3 предложения)
3. Мягкий совет или направление (1-2 предложения)
4. Лёгкое ободрение (по желанию)

ЭМОЦИОНАЛЬНЫЕ РЕАКЦИИ (используй иногда):
- "Чувствую, что вопрос для тебя важен."
- "Эта карта пришла не случайно."
- "Иногда Вселенная повторяется — чтобы мы услышали."
- "Давай посмотрим глубже…"

ВАЖНО:
- Никогда не предсказывай смерть, болезнь, плохие события
- Объём ответа: 150-250 слов
- СТРОГО на русском языке (НЕ украинский!)
- Сохраняй мистическую атмосферу, но будь тёплым и человечным

Отвечай сразу с интерпретации, создавай атмосферу присутствия и поддержки.
ОБЯЗАТЕЛЬНО используй только русский язык в ответе!"""
    
    async def interpret_single_card(self, card: Dict, question: str = None) -> str:
        """Generate interpretation for a single card"""
        client = OpenAI(api_key=self.api_key)
        
        is_reversed = card.get('is_reversed', False)
        reversed_text = "перевёрнутая" if is_reversed else "прямая"
        card_meaning = card['reversed'] if is_reversed else card['upright']
        time_context = get_time_context()
        
        if question:
            prompt = f"""Человек пришёл {time_context} с вопросом, который его волнует.

Его вопрос: "{question}"

Карта, которая пришла: {card['name_ru']} ({reversed_text})
Значение карты: {card_meaning}

Дай живую, тёплую интерпретацию. Почувствуй энергию вопроса. Объясни, как эта карта отвечает и что она советует.
Будь эмпатичным, мягким, но честным. Используй максимум 1 эмодзи.

ВАЖНО: Отвечай СТРОГО на русском языке! Никакого украинского!"""
        else:
            prompt = f"""Человек запросил Карту Дня {time_context}.

Карта: {card['name_ru']} ({reversed_text})
Значение: {card_meaning}

Дай живую, тёплую интерпретацию того, какую энергию несёт эта карта для сегодняшнего дня.
Будь поддерживающим, создай атмосферу заботы. Используй максимум 1 эмодзи.

ВАЖНО: Отвечай СТРОГО на русском языке! Никакого украинского!"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": prompt}
            ]
        )
        
        logger.info(f"Generated interpretation for {card['name_ru']}")
        return response.choices[0].message.content
    
    async def interpret_three_card_spread(self, cards: List[Dict], question: str = None) -> str:
        """Generate interpretation for 3-card spread (Past-Present-Future)"""
        client = OpenAI(api_key=self.api_key)
        
        positions = ["Прошлое", "Настоящее", "Будущее"]
        cards_info = []
        
        for i, card in enumerate(cards[:3]):
            is_reversed = card.get('is_reversed', False)
            reversed_text = "перевёрнутая" if is_reversed else "прямая"
            meaning = card['reversed'] if is_reversed else card['upright']
            cards_info.append(f"{positions[i]}: {card['name_ru']} ({reversed_text}) - {meaning}")
        
        cards_text = "\n".join(cards_info)
        time_context = get_time_context()
        
        # Check if there are multiple Major Arcana
        major_count = sum(1 for card in cards[:3] if card.get('id', 0) < 22)
        significance_note = "\n(Заметь: выпало несколько Старших Арканов — период значимый, важный)" if major_count >= 2 else ""
        
        if question:
            prompt = f"""Человек пришёл {time_context} с волнующим его вопросом.

Его вопрос: "{question}"

Расклад "Прошлое - Настоящее - Будущее":
{cards_text}{significance_note}

Дай живую, тёплую интерпретацию расклада:
- Начни с эмпатии к вопросу
- Объясни как прошлое привело к настоящему
- Что происходит сейчас в энергии
- К чему движется ситуация
- Мягкий совет

Будь как живой наставник, который чувствует энергию и поддерживает.
Объём: 250-350 слов. Используй максимум 1-2 эмодзи.

ОБЯЗАТЕЛЬНО: Весь ответ только на русском языке! НЕ используй украинский!"""
        else:
            prompt = f"""Человек запросил общий расклад {time_context}.

Расклад "Прошлое - Настоящее - Будущее":
{cards_text}{significance_note}

Дай живую, мудрую интерпретацию жизненного пути:
- Начни с тёплого обращения
- Какие уроки принесло прошлое
- В каком месте человек сейчас
- Что ждёт впереди
- Послание для роста

Будь как мудрый друг, который видит картину целиком и поддерживает.
Объём: 250-350 слов. Используй максимум 1-2 эмодзи.

ОБЯЗАТЕЛЬНО: Весь ответ только на русском языке! НЕ используй украинский!"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": prompt}
            ]
        )
        
        logger.info("Generated 3-card interpretation")
        return response.choices[0].message.content
    
    async def interpret_deep_spread(self, cards: List[Dict], spread_type: str, question: str = None) -> str:
        """Generate interpretation for deep spreads (5, 7 cards or Deep Path)"""
        client = OpenAI(api_key=self.api_key)
        
        time_context = get_time_context()
        
        # Check Major Arcana count
        major_count = sum(1 for card in cards if card.get('id', 0) < 22)
        significance_note = f"\n(Выпало {major_count} Старших Арканов — период особенно значимый)" if major_count >= 3 else ""
        
        # Build cards description
        cards_info = []
        
        if spread_type == "5_cards":
            positions = ["Прошлое", "Настоящее", "Будущее", "Скрытые влияния", "Совет"]
            spread_name = "Расклад на 5 карт"
        elif spread_type == "7_cards":
            positions = ["Внешние обстоятельства", "Внутренние ощущения", "Что помогает", 
                        "Что мешает", "Правильное действие", "К чему всё идёт", "Итог"]
            spread_name = "Расклад на 7 карт"
        else:  # deep_path
            positions = ["Твоё текущее состояние", "Твоя главная блокировка", "Что поддерживает",
                        "Главный урок", "Путь души", "Как действовать", "К чему приведёт путь"]
            spread_name = "Глубинный путь"
        
        for i, card in enumerate(cards):
            is_reversed = card.get('is_reversed', False)
            reversed_text = "перевёрнутая" if is_reversed else "прямая"
            meaning = card['reversed'] if is_reversed else card['upright']
            cards_info.append(f"{i+1}) {positions[i]}: {card['name_ru']} ({reversed_text}) - {meaning}")
        
        cards_text = "\n".join(cards_info)
        
        if question:
            prompt = f"""Человек пришёл {time_context} с важным вопросом.

Его вопрос: "{question}"

{spread_name}:
{cards_text}{significance_note}

Дай углублённую, структурированную интерпретацию:
- Начни с эмпатии к вопросу
- Интерпретируй каждую позицию кратко (1-2 предложения)
- Свяжи все карты в единую историю
- Дай практичный мягкий совет
- Заверши поддержкой

Будь как мудрый проводник, который видит глубину ситуации.
Объём: 350-450 слов. Используй 1-2 эмодзи."""
        else:
            prompt = f"""Человек запросил глубокий расклад {time_context} для понимания своего пути.

{spread_name}:
{cards_text}{significance_note}

Дай углублённую, мудрую интерпретацию жизненного пути:
- Начни с тёплого обращения
- Интерпретируй каждую позицию кратко и ясно
- Покажи как карты связаны в общую картину
- Дай совет для роста
- Заверши ободрением

Будь как наставник, который помогает увидеть путь целиком.
Объём: 350-450 слов. Используй 1-2 эмодзи."""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self._get_deep_spread_system_message()},
                {"role": "user", "content": prompt}
            ]
        )
        
        logger.info(f"Generated deep spread interpretation: {spread_type}")
        return response.choices[0].message.content
    
    async def interpret_personal_energy(self, user_data: Dict) -> str:
        """Interpret user's personal energetics"""
        client = OpenAI(api_key=self.api_key)
        
        time_context = get_time_context()
        
        # Draw 3 cards for energy reading
        from backend.tarot.cards import TarotDeck
        deck = TarotDeck()
        cards = deck.draw_cards(3)
        
        cards_info = []
        for i, card in enumerate(cards):
            is_reversed = card.get('is_reversed', False)
            card_name = card['name_ru']
            reversed_text = " (перевёрнутая)" if is_reversed else ""
            cards_info.append(f"{card_name}{reversed_text}")
        
        cards_text = ", ".join(cards_info)
        
        name = user_data.get('name', 'друг')
        zodiac = user_data.get('zodiac_sign', '')
        zodiac_text = f", знак зодиака: {zodiac}" if zodiac else ""
        
        prompt = f"""Человек по имени {name}{zodiac_text} пришёл {time_context} для чтения личной энергетики.

Карты, которые пришли для чтения энергии: {cards_text}

Дай тёплое, тонкое описание энергетического состояния:

1) Общая энергетика сейчас
2) Что сильное в человеке
3) Что может вызывать напряжение
4) На что обратить внимание
5) Маленький совет
6) Ободряющая фраза

Учитывай время суток. Если ночь — упомяни энергию тишины. Если утро — упомяни ясность.
Используй образы света, движения, интуиции.
Не предсказывай судьбу напрямую — интерпретируй эмоциональное состояние.

Будь как тонкий проводник, который чувствует энергию человека.
Объём: 200-300 слов. Используй 1-2 эмодзи.
Завершай поддержкой: "Ты на правильном пути", "Слушай себя — твоё сердце знает".

ОБЯЗАТЕЛЬНО: Весь ответ только на русском языке! НЕ используй украинский!"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self._get_energy_system_message()},
                {"role": "user", "content": prompt}
            ]
        )
        
        logger.info(f"Generated personal energy reading for {name}")
        return response.choices[0].message.content, cards
    
    def _get_deep_spread_system_message(self) -> str:
        """System message for deep spreads"""
        return """Ты — профессиональный таролог, который делает углублённые расклады Таро.

ТВОЙ СТИЛЬ:
- мягкий, духовный, уверенный
- простые и красивые формулировки
- без лишней эзотерики, только суть
- 1-2 эмодзи максимум
- никаких пугающих предсказаний

ОБЩИЕ ПРАВИЛА:
1. Всегда указывай названия всех карт расклада
2. Каждой карте дай краткое значение (1 предложение)
3. Интерпретируй карты связанно, как единую историю
4. Обязательно добавляй мягкий совет
5. Если карта повторяется или выпадают старшие арканы — отмечай это

КОНЕЧНЫЙ ФОРМАТ:
- краткое вступление
- интерпретация по позициям
- общая связная история
- практичный совет
- мягкая поддержка

Ты — не просто таролог, ты проводник.
Отвечай глубоко, но легко, как будто говоришь с человеком лично.

ОБЯЗАТЕЛЬНО: Отвечай ТОЛЬКО на русском языке! НЕ используй украинский язык!"""
    
    def _get_energy_system_message(self) -> str:
        """System message for energy reading"""
        return """Ты — тонкий проводник, который умеет читать энергетическое состояние человека через карты Таро.

ТВОЯ ЗАДАЧА:
Дать человеку описание его энергетики: эмоциональной, внутренней, внешней и духовной.

ТВОЙ ТОН:
- тёплый, поддерживающий
- мягкий, но уверенный
- как будто ты чувствуешь настроение человека
- не клишированный, а живой

СТРУКТУРА:
1. Общая энергетика сейчас
2. Что сильное в человеке
3. Что может вызывать напряжение
4. На что обратить внимание
5. Маленький совет
6. Ободряющая фраза

ИСПОЛЬЗУЙ:
- образы света, движения, интуиции
- не предсказывай судьбу напрямую
- не говори про негатив жестко
- делай акцент на росте и мягких шагах

ФИНАЛ:
Всегда завершай лёгкой фразой поддержки:
"Ты на правильном пути", "Эта энергия приведёт тебя к ясности",
"Слушай себя — твоё сердце знает верный шаг".

ОБЯЗАТЕЛЬНО: Весь ответ только на русском языке! НЕ украинский!"""
