"""Subscription check middleware and helper functions"""
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)

REQUIRED_CHANNEL = "@taro209"  # Channel username with @


async def check_user_subscribed(bot: Bot, user_id: int, channel: str = REQUIRED_CHANNEL) -> bool:
    """
    Check if user is subscribed to the required channel
    
    Args:
        bot: Bot instance
        user_id: User's Telegram ID
        channel: Channel username (e.g., @taro209)
    
    Returns:
        True if user is subscribed, False otherwise
    """
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        # Check if user is member, administrator or creator
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        # In case of error (e.g., bot not admin in channel), allow access
        return True


def get_subscription_keyboard(channel: str = REQUIRED_CHANNEL) -> InlineKeyboardMarkup:
    """
    Get inline keyboard with subscription button
    
    Args:
        channel: Channel username
    
    Returns:
        InlineKeyboardMarkup with subscription and check buttons
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Подписаться на канал",
                url=f"https://t.me/{channel.replace('@', '')}"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Я подписался",
                callback_data="check_subscription"
            )
        ]
    ])
    return keyboard


SUBSCRIPTION_MESSAGE = """🔮 Для продолжения работы с ботом необходимо подписаться на наш канал!

📢 В канале **{channel}** мы публикуем:
• ✨ Энергетику дня
• 🌌 Мистические новости
• 🔬 Связь науки и духовности
• 💫 Советы и предсказания

**Подпишись на канал и возвращайся!** 👇"""
