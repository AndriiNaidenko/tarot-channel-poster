from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.users = self.db.users
        self.readings = self.db.readings
        logger.info(f"MongoDB connected: {db_name}")
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        return await self.users.find_one({"_id": user_id})
    
    async def create_user(self, user_id: int, name: str, username: str = "", birthdate: str = None):
        user = {
            "_id": user_id,
            "name": name,
            "username": username,
            "birthdate": birthdate,
            "zodiac_sign": None,
            "created_at": datetime.now(timezone.utc),
            "premium": False,
            "limits": {
                "daily_cards_used": 0,
                "simple_spreads_used": 0,
                "last_reset": datetime.now(timezone.utc)
            },
            "stats": {"total_readings": 0}
        }
        await self.users.insert_one(user)
        logger.info(f"User created: {user_id} - {name} - {birthdate}")
        return user
    
    async def update_zodiac(self, user_id: int, zodiac: str):
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"zodiac_sign": zodiac}}
        )
    
    async def check_and_update_limits(self, user_id: int, reading_type: str) -> tuple[bool, str]:
        """
        Check if user can make a reading and update limits
        Returns: (can_proceed, message)
        """
        user = await self.get_user(user_id)
        
        # Premium users have no limits
        if user.get("premium", False):
            return True, ""
        
        limits = user.get("limits", {})
        last_reset = limits.get("last_reset", datetime.now(timezone.utc))
        now = datetime.now(timezone.utc)
        
        # Make sure last_reset is timezone-aware (for old database records)
        if last_reset.tzinfo is None:
            last_reset = last_reset.replace(tzinfo=timezone.utc)
        
        # Reset daily limits if it's a new day
        if (now - last_reset).days >= 1:
            await self.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "limits.daily_cards_used": 0,
                    "limits.simple_spreads_used": 0,
                    "limits.last_reset": now
                }}
            )
            limits = {"daily_cards_used": 0, "simple_spreads_used": 0}
        
        # Check limits based on reading type
        if reading_type == "card_of_day":
            if limits.get("daily_cards_used", 0) >= 2:
                return False, "card_of_day"
        elif reading_type in ["one_question", "three_card_spread", "advice", "tarot_advice"]:
            # Simple spreads: limited to 2 per day for free users
            if limits.get("simple_spreads_used", 0) >= 2:
                return False, "simple_spread"
        elif reading_type in ["deep_spread", "personal_energy"]:
            # Premium only features
            return False, "premium_only"
        
        # Update limits
        if reading_type == "card_of_day":
            await self.users.update_one(
                {"_id": user_id},
                {"$inc": {"limits.daily_cards_used": 1}}
            )
        elif reading_type in ["one_question", "three_card_spread", "advice", "tarot_advice"]:
            await self.users.update_one(
                {"_id": user_id},
                {"$inc": {"limits.simple_spreads_used": 1}}
            )
        
        return True, ""
    
    async def set_premium(self, user_id: int, is_premium: bool = True):
        """Set user premium status"""
        await self.users.update_one(
            {"_id": user_id},
            {"$set": {"premium": is_premium}}
        )
        logger.info(f"User {user_id} premium status set to: {is_premium}")
    
    async def save_reading(self, user_id: int, reading_type: str, cards: List[Dict], interpretation: str, question: str = None):
        reading = {
            "user_id": user_id,
            "type": reading_type,
            "question": question,
            "cards": cards,
            "interpretation": interpretation,
            "created_at": datetime.now(timezone.utc)
        }
        await self.readings.insert_one(reading)
        await self.users.update_one(
            {"_id": user_id},
            {"$inc": {"stats.total_readings": 1}}
        )
        logger.info(f"Reading saved: {user_id} - {reading_type}")
    
    async def increment_limit(self, user_id: int, limit_type: str):
        field = f"limits.{limit_type}"
        await self.users.update_one(
            {"_id": user_id},
            {"$inc": {field: 1}}
        )
    
    async def reset_limits_if_needed(self, user_id: int):
        user = await self.get_user(user_id)
        if not user:
            return
        
        last_reset = user['limits']['last_reset']
        now = datetime.now(timezone.utc)
        
        # Reset if it's a new day
        if now.date() > last_reset.date():
            await self.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "limits.daily_cards_used": 0,
                    "limits.simple_spreads_used": 0,
                    "limits.last_reset": now
                }}
            )
            logger.info(f"Limits reset for user {user_id}")
    
    async def get_user_readings(self, user_id: int, limit: int = 10) -> List[Dict]:
        cursor = self.readings.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
