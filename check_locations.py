import asyncio
from app.infrastructure.database.mongodb import db, connect_to_mongo, close_mongo_connection
from app.domain.services.location import haversine_distance

async def check():
    await connect_to_mongo()
    print("--- Checking Blood Requests ---")
    requests = await db.db.blood_requests.find().to_list(length=100)
    for r in requests:
        print(f"Request ID: {r['_id']}, Blood Group: {r.get('blood_group')}, Hospital ID: {r.get('hospital_id')}")
        print(f"  Hospital Coordinates: Lat={r.get('hospital_latitude')}, Lng={r.get('hospital_longitude')}")
    
    print("\n--- Checking Donation Responses ---")
    responses = await db.db.donation_responses.find().to_list(length=100)
    for res in responses:
        print(f"Response ID: {res['_id']}, Request ID: {res.get('request_id')}, Donor ID: {res.get('donor_id')}, Status: {res.get('status')}")
        print(f"  Donor Coordinates (stored in Response): Lat={res.get('donor_latitude')}, Lng={res.get('donor_longitude')}")
        print(f"  Distance (stored in Response): {res.get('distance_km')} km")
        
        # Load donor profile
        dp = await db.db.donor_profiles.find_one({"user_id": res.get("donor_id")})
        if dp:
            print(f"  Donor Profile: {dp.get('full_name')}")
            loc = dp.get('location')
            if loc and loc.get('type') == 'Point':
                coords = loc.get('coordinates')
                print(f"    Profile Coordinates: Lat={coords[1]}, Lng={coords[0]}")
            else:
                print(f"    Profile Coordinates: None")
        
        # Load request
        req = await db.db.blood_requests.find_one({"_id": res.get("request_id")})
        if req and req.get("hospital_latitude") is not None and req.get("hospital_longitude") is not None:
            lat = res.get("donor_latitude")
            lng = res.get("donor_longitude")
            if lat is None or lng is None:
                # Fallback to donor profile
                if dp and dp.get('location'):
                    coords = dp['location']['coordinates']
                    lat, lng = coords[1], coords[0]
            
            if lat is not None and lng is not None:
                calc_dist = haversine_distance(req.get("hospital_latitude"), req.get("hospital_longitude"), lat, lng)
                print(f"  Calculated Distance: {calc_dist:.2f} km")
                if abs(calc_dist - (res.get("distance_km") or 0)) > 0.01:
                    print(f"    WARNING: Distance mismatch! Stored: {res.get('distance_km')} vs Calculated: {calc_dist:.2f}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(check())
