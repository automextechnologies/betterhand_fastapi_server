import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db = MongoDB()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    db.client = AsyncIOMotorClient(settings.MONGODB_URL, tlsAllowInvalidCertificates=True)
    db.db = db.client[settings.DB_NAME]
    logger.info(f"Connected to MongoDB database: {settings.DB_NAME}")
    
    # Initialize indexes
    await init_indexes()

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
        logger.info("MongoDB connection closed.")

async def init_indexes():
    """Create indexes (unique and 2dsphere) on startup."""
    try:
        # Users
        await db.db.users.create_index("email", unique=True)
        
        # Hospital Profiles
        await db.db.hospital_profiles.create_index("user_id", unique=True)
        await db.db.hospital_profiles.create_index("registration_number", unique=True)
        await db.db.hospital_profiles.create_index([("location", "2dsphere")])
        
        # Donor Profiles
        await db.db.donor_profiles.create_index("user_id", unique=True)
        await db.db.donor_profiles.create_index([("location", "2dsphere")])
        
        # Wards
        await db.db.wards.create_index([("ward_number", 1), ("local_body_name", 1), ("state", 1)], unique=True)
        await db.db.wards.create_index([("location", "2dsphere")])
        
        # Ward Members
        await db.db.ward_members.create_index("user_id", unique=True)
        
        # Ward Blood Alerts
        await db.db.ward_blood_alerts.create_index("ward_member_id")
        
        # Ward Donor Notifications
        await db.db.ward_donor_notifications.create_index([("alert_id", 1), ("donor_id", 1)], unique=True)
        
        # Blood Requests
        await db.db.blood_requests.create_index("hospital_id")
        
        # Donation Responses
        await db.db.donation_responses.create_index([("request_id", 1), ("donor_id", 1)], unique=True)
        
        # Donation Records
        await db.db.donation_records.create_index("donor_id")
        
        # Chat Messages
        await db.db.chat_messages.create_index("response_id")
        await db.db.chat_messages.create_index("created_at")
        
        # Donor Ratings
        await db.db.donor_ratings.create_index("record_id", unique=True)
        
        # Donor Badges
        await db.db.donor_badges.create_index([("donor_id", 1), ("badge", 1)], unique=True)
        
        # Blood Camps
        await db.db.blood_camps.create_index("hospital_id")
        await db.db.blood_camps.create_index([("location", "2dsphere")])
        
        # Camp Registrations
        await db.db.camp_registrations.create_index([("camp_id", 1), ("donor_id", 1)], unique=True)
        
        # Notifications
        await db.db.notifications.create_index("recipient_id")
        
        # Token Blacklist
        await db.db.token_blacklist.create_index("token", unique=True)
        await db.db.token_blacklist.create_index("expires_at", expireAfterSeconds=0) # MongoDB TTL auto-expiring index
        
        logger.info("MongoDB indexes initialized successfully.")
    except Exception as e:
        logger.warning(f"Error initializing MongoDB indexes (database may be unreachable or IP not whitelisted): {e}")

