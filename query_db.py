import asyncio
from app.infrastructure.database.mongodb import db, connect_to_mongo, close_mongo_connection

async def main():
    await connect_to_mongo()
    print("Connected to Mongo.")
    
    # List all users
    users = await db.db.users.find().to_list(length=100)
    print(f"\nTotal users: {len(users)}")
    for u in users:
        print(f"User: id={u.get('_id')}, email={u.get('email')}, role={u.get('role')}")
        
    # List all blood requests
    reqs = await db.db.blood_requests.find().to_list(length=100)
    print(f"\nTotal blood requests: {len(reqs)}")
    for r in reqs:
        print(f"Request: id={r.get('_id')}, hospital_id={r.get('hospital_id')}, blood_group={r.get('blood_group')}, status={r.get('status')}, patient_name={r.get('patient_name')}")
        
    await close_mongo_connection()

if __name__ == '__main__':
    asyncio.run(main())
