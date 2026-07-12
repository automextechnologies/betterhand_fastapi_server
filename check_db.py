import asyncio
from app.infrastructure.database.mongodb import db, connect_to_mongo
from app.infrastructure.repositories.mongo_user_repo import MongoDonorProfileRepository
from datetime import datetime, timedelta

async def main():
    await connect_to_mongo()
    repo = MongoDonorProfileRepository()
    
    # 1. Print Donation Records
    try:
        records = await db.db.donation_records.find({}).to_list(length=100)
        print('--- Donation Records ---')
        print(f'Total records: {len(records)}')
        for r in records:
            print(f"Donor ID: {r.get('donor_id')}, Cooldown Until: {r.get('cooldown_until')}")
    except Exception as e:
        print('Error reading donation records:', e)

    # 2. Test Geospatial search for O+ (Kochi)
    try:
        print('\n--- Test Search O+ (Kochi coordinates) ---')
        # Kochi hospital: 76.2673, 9.9312
        donors = await repo.search_donors(
            blood_group="O+",
            longitude=76.2673,
            latitude=9.9312,
            radius_km=50.0
        )
        print(f"Matched {len(donors)} O+ donors:")
        for d in donors:
            print(f"- {d.full_name} ({d.blood_group})")
    except Exception as e:
        print('Error searching O+:', e)

    # 3. Test Geospatial search for B- (Malappuram)
    try:
        print('\n--- Test Search B- (Malappuram coordinates) ---')
        # Hospital: 75.9811564, 11.0467518
        donors = await repo.search_donors(
            blood_group="B-",
            longitude=75.9811564,
            latitude=11.0467518,
            radius_km=50.0
        )
        print(f"Matched {len(donors)} B- donors:")
        for d in donors:
            print(f"- {d.full_name} ({d.blood_group})")
    except Exception as e:
        print('Error searching B-:', e)

asyncio.run(main())
