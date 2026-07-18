import asyncio
from app.infrastructure.database.mongodb import db, connect_to_mongo, close_mongo_connection
from bson import ObjectId

async def run():
    await connect_to_mongo()
    hospital_user_id = "6a5b09272a52895606002179"
    hospital_profile = await db.db.hospital_profiles.find_one({"user_id": ObjectId(hospital_user_id)})
    print("Hospital Profile in DB:")
    print(hospital_profile)
    
    request = await db.db.blood_requests.find_one({"hospital_id": ObjectId(hospital_user_id)})
    print("Request in DB:")
    print(request)
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run())
