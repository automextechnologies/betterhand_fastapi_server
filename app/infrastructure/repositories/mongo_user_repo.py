from typing import Optional, List
from datetime import datetime, date
from bson import ObjectId
from app.infrastructure.database.mongodb import db
from app.domain.entities.user import User, HospitalProfile, DonorProfile, DonorQuestionnaire
from app.domain.repositories.user_repo import UserRepository, HospitalProfileRepository, DonorProfileRepository

def map_user_to_entity(doc: dict) -> User:
    return User(
        id=str(doc["_id"]),
        email=doc.get("email", ""),
        hashed_password=doc.get("hashed_password", ""),
        role=doc.get("role", ""),
        is_active=doc.get("is_active", True),
        is_staff=doc.get("is_staff", False),
        date_joined=doc.get("date_joined", datetime.utcnow()),
        fcm_token=doc.get("fcm_token")
    )

def map_user_to_db(entity: User) -> dict:
    data = {
        "email": entity.email,
        "hashed_password": entity.hashed_password,
        "role": entity.role,
        "is_active": entity.is_active,
        "is_staff": entity.is_staff,
        "date_joined": entity.date_joined,
        "fcm_token": entity.fcm_token
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


def map_hospital_to_entity(doc: dict) -> HospitalProfile:
    loc = doc.get("location")
    lat, lng = None, None
    if loc and loc.get("type") == "Point":
        coords = loc.get("coordinates")
        if coords and len(coords) == 2:
            lng, lat = coords[0], coords[1]
            
    return HospitalProfile(
        id=str(doc["_id"]),
        user_id=str(doc.get("user_id", "")),
        name=doc.get("name", ""),
        registration_number=doc.get("registration_number", ""),
        phone=doc.get("phone", ""),
        address=doc.get("address", ""),
        city=doc.get("city", ""),
        state=doc.get("state", ""),
        district=doc.get("district", ""),
        local_body_type=doc.get("local_body_type", ""),
        local_body_name=doc.get("local_body_name", ""),
        ward_number=doc.get("ward_number", ""),
        pincode=doc.get("pincode", ""),
        latitude=lat,
        longitude=lng,
        whatsapp_number=doc.get("whatsapp_number", ""),
        logo=doc.get("logo"),
        is_verified=doc.get("is_verified", False),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow())
    )

def map_hospital_to_db(entity: HospitalProfile) -> dict:
    data = {
        "user_id": ObjectId(entity.user_id) if entity.user_id else "",
        "name": entity.name,
        "registration_number": entity.registration_number,
        "phone": entity.phone,
        "address": entity.address,
        "city": entity.city,
        "state": entity.state,
        "district": entity.district,
        "local_body_type": entity.local_body_type,
        "local_body_name": entity.local_body_name,
        "ward_number": entity.ward_number,
        "pincode": entity.pincode,
        "whatsapp_number": entity.whatsapp_number,
        "logo": entity.logo,
        "is_verified": entity.is_verified,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at
    }
    
    if entity.longitude is not None and entity.latitude is not None:
        data["location"] = {
            "type": "Point",
            "coordinates": [float(entity.longitude), float(entity.latitude)]
        }
    else:
        data["location"] = None
        
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


def map_donor_to_entity(doc: dict) -> DonorProfile:
    loc = doc.get("location")
    lat, lng = None, None
    if loc and loc.get("type") == "Point":
        coords = loc.get("coordinates")
        if coords and len(coords) == 2:
            lng, lat = coords[0], coords[1]
            
    q_doc = doc.get("questionnaire", {})
    
    # Safely convert last donation date
    q_last_donation_date = None
    ld_date = q_doc.get("q_last_donation_date")
    if ld_date:
        if isinstance(ld_date, datetime):
            q_last_donation_date = ld_date.date()
        elif isinstance(ld_date, date):
            q_last_donation_date = ld_date
        elif isinstance(ld_date, str):
            try:
                q_last_donation_date = datetime.strptime(ld_date.split("T")[0], "%Y-%m-%d").date()
            except ValueError:
                pass

    questionnaire = DonorQuestionnaire(
        questionnaire_completed=q_doc.get("questionnaire_completed", False),
        q_weight_ok=q_doc.get("q_weight_ok", False),
        q_age_ok=q_doc.get("q_age_ok", False),
        q_no_illness=q_doc.get("q_no_illness", False),
        q_no_medication=q_doc.get("q_no_medication", False),
        q_no_recent_donation=q_doc.get("q_no_recent_donation", False),
        q_no_tattoo=q_doc.get("q_no_tattoo", False),
        q_no_alcohol=q_doc.get("q_no_alcohol", False),
        q_last_donation_date=q_last_donation_date,
        q_chronic_conditions=q_doc.get("q_chronic_conditions", ""),
        consent_given=q_doc.get("consent_given", False),
        consent_date=q_doc.get("consent_date")
    )
    
    return DonorProfile(
        id=str(doc["_id"]),
        user_id=str(doc.get("user_id", "")),
        full_name=doc.get("full_name", ""),
        blood_group=doc.get("blood_group", ""),
        phone=doc.get("phone", ""),
        age=doc.get("age"),
        gender=doc.get("gender", ""),
        address=doc.get("address", ""),
        state=doc.get("state", ""),
        district=doc.get("district", ""),
        local_body_type=doc.get("local_body_type", ""),
        local_body_name=doc.get("local_body_name", ""),
        ward_number=doc.get("ward_number", ""),
        city=doc.get("city", ""),
        pincode=doc.get("pincode", ""),
        latitude=lat,
        longitude=lng,
        is_available=doc.get("is_available", True),
        whatsapp_number=doc.get("whatsapp_number", ""),
        is_student=doc.get("is_student", False),
        college_name=doc.get("college_name", ""),
        college_district=doc.get("college_district", ""),
        questionnaire=questionnaire,
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow())
    )

def map_donor_to_db(entity: DonorProfile) -> dict:
    # Convert date to datetime for MongoDB
    ld_date = entity.questionnaire.q_last_donation_date
    if ld_date and isinstance(ld_date, date) and not isinstance(ld_date, datetime):
        ld_date = datetime(ld_date.year, ld_date.month, ld_date.day)

    data = {
        "user_id": ObjectId(entity.user_id) if entity.user_id else "",
        "full_name": entity.full_name,
        "blood_group": entity.blood_group,
        "phone": entity.phone,
        "age": entity.age,
        "gender": entity.gender,
        "address": entity.address,
        "state": entity.state,
        "district": entity.district,
        "local_body_type": entity.local_body_type,
        "local_body_name": entity.local_body_name,
        "ward_number": entity.ward_number,
        "city": entity.city,
        "pincode": entity.pincode,
        "is_available": entity.is_available,
        "whatsapp_number": entity.whatsapp_number,
        "is_student": entity.is_student,
        "college_name": entity.college_name,
        "college_district": entity.college_district,
        "questionnaire": {
            "questionnaire_completed": entity.questionnaire.questionnaire_completed,
            "q_weight_ok": entity.questionnaire.q_weight_ok,
            "q_age_ok": entity.questionnaire.q_age_ok,
            "q_no_illness": entity.questionnaire.q_no_illness,
            "q_no_medication": entity.questionnaire.q_no_medication,
            "q_no_recent_donation": entity.questionnaire.q_no_recent_donation,
            "q_no_tattoo": entity.questionnaire.q_no_tattoo,
            "q_no_alcohol": entity.questionnaire.q_no_alcohol,
            "q_last_donation_date": ld_date,
            "q_chronic_conditions": entity.questionnaire.q_chronic_conditions,
            "consent_given": entity.questionnaire.consent_given,
            "consent_date": entity.questionnaire.consent_date
        },
        "created_at": entity.created_at,
        "updated_at": entity.updated_at
    }
    
    if entity.longitude is not None and entity.latitude is not None:
        data["location"] = {
            "type": "Point",
            "coordinates": [float(entity.longitude), float(entity.latitude)]
        }
    else:
        data["location"] = None
        
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


class MongoUserRepository(UserRepository):
    async def get_by_id(self, user_id: str) -> Optional[User]:
        if not user_id:
            return None
        try:
            doc = await db.db.users.find_one({"_id": ObjectId(user_id)})
            return map_user_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_by_email(self, email: str) -> Optional[User]:
        doc = await db.db.users.find_one({"email": email.strip().lower()})
        return map_user_to_entity(doc) if doc else None

    async def create(self, user: User) -> User:
        user.email = user.email.strip().lower()
        doc = map_user_to_db(user)
        result = await db.db.users.insert_one(doc)
        user.id = str(result.inserted_id)
        return user

    async def update(self, user: User) -> User:
        user.email = user.email.strip().lower()
        doc = map_user_to_db(user)
        await db.db.users.replace_one({"_id": ObjectId(user.id)}, doc)
        return user

    async def delete(self, user_id: str) -> bool:
        result = await db.db.users.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    async def get_by_role(self, role: str) -> List[User]:
        cursor = db.db.users.find({"role": role})
        docs = await cursor.to_list(length=1000)
        return [map_user_to_entity(doc) for doc in docs]


class MongoHospitalProfileRepository(HospitalProfileRepository):
    async def get_by_id(self, profile_id: str) -> Optional[HospitalProfile]:
        try:
            doc = await db.db.hospital_profiles.find_one({"_id": ObjectId(profile_id)})
            return map_hospital_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_by_user_id(self, user_id: str) -> Optional[HospitalProfile]:
        try:
            doc = await db.db.hospital_profiles.find_one({"user_id": ObjectId(user_id)})
            return map_hospital_to_entity(doc) if doc else None
        except Exception:
            return None

    async def create(self, profile: HospitalProfile) -> HospitalProfile:
        doc = map_hospital_to_db(profile)
        result = await db.db.hospital_profiles.insert_one(doc)
        profile.id = str(result.inserted_id)
        return profile

    async def update(self, profile: HospitalProfile) -> HospitalProfile:
        profile.updated_at = datetime.utcnow()
        doc = map_hospital_to_db(profile)
        await db.db.hospital_profiles.replace_one({"_id": ObjectId(profile.id)}, doc)
        return profile


class MongoDonorProfileRepository(DonorProfileRepository):
    async def get_by_id(self, profile_id: str) -> Optional[DonorProfile]:
        try:
            doc = await db.db.donor_profiles.find_one({"_id": ObjectId(profile_id)})
            return map_donor_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_by_user_id(self, user_id: str) -> Optional[DonorProfile]:
        try:
            doc = await db.db.donor_profiles.find_one({"user_id": ObjectId(user_id)})
            return map_donor_to_entity(doc) if doc else None
        except Exception:
            return None

    async def create(self, profile: DonorProfile) -> DonorProfile:
        doc = map_donor_to_db(profile)
        result = await db.db.donor_profiles.insert_one(doc)
        profile.id = str(result.inserted_id)
        return profile

    async def update(self, profile: DonorProfile) -> DonorProfile:
        profile.updated_at = datetime.utcnow()
        doc = map_donor_to_db(profile)
        await db.db.donor_profiles.replace_one({"_id": ObjectId(profile.id)}, doc)
        return profile

    async def search_donors(
        self,
        blood_group: str,
        longitude: float,
        latitude: float,
        radius_km: float,
        cooldown_cutoff_date: Optional[str] = None
    ) -> List[DonorProfile]:
        """
        Geospatial query to find matching available donors within radius_km.
        Excludes donors with recent donations (on cooldown).
        """
        # Exclude donors who have recent donations.
        # Find donor user_ids with donations since cooldown_cutoff_date.
        excluded_donor_ids = []
        if cooldown_cutoff_date:
            cutoff_dt = datetime.fromisoformat(cooldown_cutoff_date)
            # Find donor ids from donation records that are active after cutoff_dt
            records = await db.db.donation_records.find(
                {"cooldown_until": {"$gt": datetime.utcnow()}}
            ).to_list(length=1000)
            excluded_donor_ids = [ObjectId(r["donor_id"]) for r in records if "donor_id" in r]
            
        # MongoDB 2d Sphere Geospatial Query
        # 1 radian ~ 6378.1 km, so distance in radians is radius_km / 6378.1
        query = {
            "blood_group": blood_group,
            "is_available": True,
        }
        
        if radius_km > 0 and longitude is not None and latitude is not None:
            query["location"] = {
                "$nearSphere": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [float(longitude), float(latitude)]
                    },
                    "$maxDistance": float(radius_km) * 1000 # maxDistance is in meters for $nearSphere GeoJSON Point
                }
            }
        
        if excluded_donor_ids:
            query["user_id"] = {"$nin": excluded_donor_ids}
            
        docs = await db.db.donor_profiles.find(query).to_list(length=500)
        return [map_donor_to_entity(doc) for doc in docs]

    async def get_distinct_colleges(self, district: Optional[str] = None) -> List[dict]:
        match_stage = {"college_name": {"$ne": ""}}
        if district:
            match_stage["college_district"] = {"$regex": f"^{district}$", "$options": "i"}
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": {
                    "name": {"$trim": {"input": "$college_name"}},
                    "district": {"$trim": {"input": "$college_district"}}
                }
            }},
            {"$project": {
                "_id": 0,
                "name": "$_id.name",
                "district": "$_id.district"
            }},
            {"$sort": {"name": 1}}
        ]
        
        cursor = db.db.donor_profiles.aggregate(pipeline)
        return await cursor.to_list(length=1000)
