import asyncio
import logging
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config import config
from backend.channel.news_fetcher import NewsFetcher
from backend.channel.post_generator import PostGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/channel_poster.log')
    ]
)

logger = logging.getLogger(__name__)

# Channel configuration
CHANNEL_USERNAME = "@taro209"  # Your channel

# Bot instance
bot = None

# State file for topic rotation
STATE_FILE = Path("/tmp/channel_poster_state.json")


def load_state() -> dict:
    """Load rotation state from file"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    return {
        "day_rotation_index": 0,  # for 14:00 (space/science)
        "evening_rotation_index": 0  # for 19:00 (technology/nature)
    }


def save_state(state: dict):
    """Save rotation state to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
        logger.info(f"State saved: {state}")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def get_topic_for_time(hour: int) -> str:
    """
    Determine topic based on time of day with fixed rotation
    
    Schedule:
    - 09:00 (morning): ✨ Energy of the Day (astrology, moon)
    - 14:00 (day): 🌌 Space OR 🔬 Science (alternating)
    - 19:00 (evening): 🤖 Technology OR 🌿 Nature (alternating)
    - 22:30 (night): 🌌 Space (mysticism of the night)
    """
    state = load_state()
    
    if hour == 9:
        # Morning: always energy
        return "energy"
    
    elif hour == 14:
        # Day: alternate between space and science
        topics = ["space", "science"]
        index = state["day_rotation_index"]
        topic = topics[index % 2]
        
        # Update rotation for next time
        state["day_rotation_index"] = (index + 1) % 2
        save_state(state)
        
        logger.info(f"14:00 rotation: selected '{topic}' (next: {topics[(index + 1) % 2]})")
        return topic
    
    elif hour == 19:
        # Evening: alternate between technology and nature
        topics = ["technology", "nature"]
        index = state["evening_rotation_index"]
        topic = topics[index % 2]
        
        # Update rotation for next time
        state["evening_rotation_index"] = (index + 1) % 2
        save_state(state)
        
        logger.info(f"19:00 rotation: selected '{topic}' (next: {topics[(index + 1) % 2]})")
        return topic
    
    elif hour == 22:
        # Night: always space (mystical)
        return "space"
    
    else:
        # Fallback for any other time
        logger.warning(f"Unexpected hour {hour}, using default 'energy'")
        return "energy"


async def create_and_post(fixed_topic: str = None):
    """Main function to create and post to channel"""
    try:
        logger.info("=" * 50)
        logger.info("Starting post generation cycle")
        
        # Initialize components  
        post_generator = PostGenerator()
        
        # Use topic directly without news fetcher for now
        logger.info(f"Generating post for topic: {fixed_topic}")
        
        # Create simple news_data structure
        news_data = {
            "topic": fixed_topic or "energy",
            "query": "",
            "results": f"Сегодняшняя тема: {fixed_topic or 'энергия дня'}",
            "timestamp": datetime.now()
        }
        
        logger.info(f"Topic selected: {news_data['topic']}")
        
        # Generate post
        logger.info("Generating post...")
        post_text = await post_generator.generate_post(news_data)
        
        # Validate post
        if not post_generator.validate_post(post_text):
            logger.error("Generated post failed validation")
            return
        
        logger.info(f"Post generated ({len(post_text)} chars)")
        logger.info(f"Post preview: {post_text[:100]}...")
        
        # Publish to channel
        logger.info(f"Publishing to channel: {CHANNEL_USERNAME}")
        
        try:
            message = await bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=post_text,
                parse_mode=None  # Plain text for now
            )
            logger.info(f"✅ Post published successfully! Message ID: {message.message_id}")
        except Exception as e:
            logger.error(f"❌ Failed to publish post: {e}")
            # Log full post for debugging
            logger.error(f"Post text: {post_text}")
            raise
        
    except Exception as e:
        logger.error(f"Error in create_and_post: {e}", exc_info=True)


async def morning_post_job():
    """Morning post job wrapper"""
    await create_and_post(fixed_topic=get_topic_for_time(9))


async def day_post_job():
    """Day post job wrapper"""
    await create_and_post(fixed_topic=get_topic_for_time(14))


async def evening_post_job():
    """Evening post job wrapper"""
    await create_and_post(fixed_topic=get_topic_for_time(19))


async def night_post_job():
    """Night post job wrapper"""
    await create_and_post(fixed_topic=get_topic_for_time(22))


async def main():
    """Main entry point"""
    global bot
    
    # Initialize bot
    bot = Bot(
        token=config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    logger.info("🌟 Channel Poster Bot starting...")
    logger.info(f"Channel: {CHANNEL_USERNAME}")
    
    # Create scheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule posts 4 times a day with fixed topics
    # Morning: 9:00 - Energy of the Day
    scheduler.add_job(
        morning_post_job,
        CronTrigger(hour=9, minute=0),
        id='morning_post',
        name='Morning Post (Energy)'
    )
    
    # Day: 14:00 - Space OR Science (alternating)
    scheduler.add_job(
        day_post_job,
        CronTrigger(hour=14, minute=0),
        id='day_post',
        name='Day Post (Space/Science)'
    )
    
    # Evening: 19:00 - Technology OR Nature (alternating)
    scheduler.add_job(
        evening_post_job,
        CronTrigger(hour=19, minute=0),
        id='evening_post',
        name='Evening Post (Tech/Nature)'
    )
    
    # Night: 22:30 - Space (mysticism)
    scheduler.add_job(
        night_post_job,
        CronTrigger(hour=22, minute=30),
        id='night_post',
        name='Night Post (Space)'
    )
    
    logger.info("📅 Fixed-time topic rotation configured:")
    logger.info("  - 09:00 ✨ Energy of the Day (astrology, moon)")
    logger.info("  - 14:00 🌌 Space ↔️ 🔬 Science (alternating)")
    logger.info("  - 19:00 🤖 Technology ↔️ 🌿 Nature (alternating)")
    logger.info("  - 22:30 🌌 Space (mysticism of the night)")
    
    # Check bot permissions in channel
    logger.info(f"🔍 Checking bot permissions in channel {CHANNEL_USERNAME}...")
    try:
        chat = await bot.get_chat(CHANNEL_USERNAME)
        logger.info(f"✅ Channel found: {chat.title}")
        
        bot_member = await bot.get_chat_member(CHANNEL_USERNAME, bot.id)
        logger.info(f"✅ Bot status in channel: {bot_member.status}")
        
        if bot_member.status not in ['administrator', 'creator']:
            logger.warning(f"⚠️ Bot is not admin in channel! Status: {bot_member.status}")
            logger.warning(f"⚠️ Bot needs to be ADMIN with 'Post messages' permission!")
    except Exception as e:
        logger.error(f"❌ Cannot access channel {CHANNEL_USERNAME}: {e}")
        logger.error(f"❌ Make sure bot is added to channel as ADMIN!")
    
    # Start scheduler
    scheduler.start()
    logger.info("✅ Scheduler started!")
    logger.info("⏰ Next scheduled posts:")
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        logger.info(f"   - {job.name}: {next_run}")
    
    # Test post immediately (uses current time to determine topic)
    logger.info("🧪 Creating test post immediately...")
    current_hour = datetime.now().hour
    test_topic = get_topic_for_time(current_hour)
    logger.info(f"Test post will use topic for hour {current_hour}: {test_topic}")
    try:
        await create_and_post(fixed_topic=test_topic)
        logger.info("✅ Test post sent successfully!")
    except Exception as e:
        logger.error(f"❌ Test post failed: {e}", exc_info=True)
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
