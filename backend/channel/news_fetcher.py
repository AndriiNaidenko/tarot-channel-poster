import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetches fresh news from various topics for channel posts"""
    
    TOPICS = {
        "space": [
            "космические открытия последние 24 часа",
            "астрономические явления сегодня",
            "новости космоса NASA SpaceX",
            "планеты звезды кометы сегодня",
            "солнечная активность магнитные бури",
            "космические феномены последние сутки",
            "астрономические открытия новости",
            "луна полнолуние новолуние сегодня",
        ],
        "science": [
            "научные открытия последние сутки",
            "прорывы в биологии медицине",
            "новые исследования наука",
            "открытия в физике химии",
            "биологические открытия сегодня",
            "прорыв в науке исследования",
            "научные достижения новости",
        ],
        "technology": [
            "новые технологии AI искусственный интеллект",
            "технологические прорывы сегодня",
            "инновации изобретения последние",
            "цифровые тренды технологии",
            "новинки в мире технологий",
            "технологический прорыв новости",
        ],
        "nature": [
            "природные явления сегодня",
            "климатические аномалии последние сутки",
            "магнитные бури солнце влияние",
            "редкие природные феномены",
            "природные знаки приметы",
            "необычные природные события",
            "экологические новости природа",
            "циклы природы сезоны",
        ],
        "energy": [
            "энергетика дня астрология",
            "луна фазы влияние на людей сегодня",
            "астрологический прогноз сегодня",
            "магнитные бури влияние на здоровье",
            "энергия недели астрология",
            "ретроградный меркурий влияние",
            "аспекты планет сегодня",
        ],
        "culture": [
            "неожиданные культурные события сегодня",
            "социальные тенденции мира последние",
            "настроение человечества тренды",
            "мировые процессы новости",
            "культурные феномены события",
            "вирусные тренды социальные сети",
        ],
        "mystical": [
            "редкие происшествия мистика",
            "циклы природы луна солнце",
            "знаки вселенной синхронности",
            "мистические события необъяснимое",
            "странные совпадения феномены",
            "энергетические сдвиги мир",
        ]
    }
    
    def __init__(self, web_search_func):
        """
        Initialize news fetcher
        
        Args:
            web_search_func: Function to perform web searches
        """
        self.web_search = web_search_func
        self.last_topics = []  # Track to avoid repetition
    
    def get_random_topic(self) -> str:
        """Get random topic, avoiding recent ones"""
        available_topics = [t for t in self.TOPICS.keys() if t not in self.last_topics[-2:]]
        
        if not available_topics:
            available_topics = list(self.TOPICS.keys())
            self.last_topics = []
        
        topic = random.choice(available_topics)
        self.last_topics.append(topic)
        
        return topic
    
    async def fetch_news(self, topic: str = None) -> dict:
        """
        Fetch fresh news for a specific topic or random
        
        Args:
            topic: Optional topic name (space, science, technology, nature, energy)
            
        Returns:
            dict with 'topic', 'query', 'results'
        """
        if topic is None or topic not in self.TOPICS:
            topic = self.get_random_topic()
        
        # Get random query for this topic
        query = random.choice(self.TOPICS[topic])
        
        logger.info(f"Fetching news for topic '{topic}' with query: {query}")
        
        try:
            # Perform web search
            results = await self.web_search(query, search_context_size="medium")
            
            return {
                "topic": topic,
                "query": query,
                "results": results,
                "timestamp": datetime.now()
            }
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return {
                "topic": topic,
                "query": query,
                "results": None,
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def get_topic_emoji(self, topic: str) -> str:
        """Get emoji for topic"""
        emoji_map = {
            "space": "🌌",
            "science": "🔬",
            "technology": "🤖",
            "nature": "🌿",
            "energy": "✨"
        }
        return emoji_map.get(topic, "📰")
