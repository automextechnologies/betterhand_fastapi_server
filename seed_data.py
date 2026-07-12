import asyncio
import logging
from app.core.config import settings
from app.infrastructure.database.mongodb import db, connect_to_mongo, close_mongo_connection
from app.dependencies.db_repos import get_auth_use_cases, get_ward_use_cases
from app.application.dto.auth_dto import HospitalRegisterDTO, DonorRegisterDTO
from app.application.dto.ward_dto import WardMemberRegisterDTO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Seeder")

async def seed():
    logger.info("Connecting to MongoDB...")
    await connect_to_mongo()
    
    from app.dependencies.db_repos import (
        get_user_repository, get_hospital_repository, get_donor_repository,
        get_ward_repository, get_ward_member_repository, get_ward_alert_repository,
        get_ward_notif_repository, get_request_repository, get_response_repository,
        get_record_repository, get_rating_repository, get_badge_repository
    )
    from app.application.use_cases.auth_use_cases import AuthUseCases
    from app.application.use_cases.ward_use_cases import WardUseCases
    from app.utils.websocket import ws_broadcast
    
    user_repo = get_user_repository()
    hospital_repo = get_hospital_repository()
    donor_repo = get_donor_repository()
    ward_repo = get_ward_repository()
    ward_member_repo = get_ward_member_repository()
    ward_alert_repo = get_ward_alert_repository()
    ward_notif_repo = get_ward_notif_repository()
    request_repo = get_request_repository()
    response_repo = get_response_repository()
    record_repo = get_record_repository()
    rating_repo = get_rating_repository()
    badge_repo = get_badge_repository()
    
    auth_use_cases = AuthUseCases(user_repo, hospital_repo, donor_repo)
    ward_use_cases = WardUseCases(
        user_repo=user_repo,
        donor_repo=donor_repo,
        ward_repo=ward_repo,
        ward_member_repo=ward_member_repo,
        ward_alert_repo=ward_alert_repo,
        ward_notif_repo=ward_notif_repo,
        request_repo=request_repo,
        response_repo=response_repo,
        record_repo=record_repo,
        rating_repo=rating_repo,
        badge_repo=badge_repo,
        ws_broadcast_func=ws_broadcast
    )
    
    # 1. Create Ward if not exists
    logger.info("Seeding Ward...")
    ward_num = "12"
    existing_ward = await db.db.wards.find_one({"ward_number": ward_num})
    if not existing_ward:
        ward_doc = {
            "ward_number": ward_num,
            "local_body_name": "Kochi Municipal Corporation",
            "local_body_type": "corporation",
            "district": "Ernakulam",
            "state": "Kerala",
            "location": {
                "type": "Point",
                "coordinates": [76.267304, 9.981636]
            }
        }
        res = await db.db.wards.insert_one(ward_doc)
        ward_id = str(res.inserted_id)
        logger.info(f"Created ward with ID: {ward_id}")
    else:
        ward_id = str(existing_ward["_id"])
        logger.info(f"Ward already exists with ID: {ward_id}")

    # 2. Seed Hospital
    hospital_email = "test_hospital@betterhand.org"
    existing_hospital = await db.db.users.find_one({"email": hospital_email})
    if not existing_hospital:
        logger.info("Registering test hospital...")
        h_dto = HospitalRegisterDTO(
            email=hospital_email,
            password="securepassword123",
            name="General Hospital Kochi",
            registration_number="GH-12345",
            phone="+919876543210",
            address="Kochi Main Road",
            city="Kochi",
            state="Kerala",
            district="Ernakulam",
            local_body_type="corporation",
            local_body_name="Kochi Corporation",
            ward_number="5",
            pincode="682011",
            latitude=9.981636,
            longitude=76.267304,
            whatsapp_number="+919876543210"
        )
        await auth_use_cases.register_hospital(h_dto)
        logger.info(f"Registered hospital user: {hospital_email} with password: securepassword123")
    else:
        logger.info(f"Hospital {hospital_email} already exists.")

    # 3. Seed Donor
    donor_phone = "+919988776655"
    existing_donor = await db.db.users.find_one({"phone": donor_phone})
    if not existing_donor:
        logger.info("Registering test donor...")
        d_dto = DonorRegisterDTO(
            password="donorpassword123",
            full_name="Donor A (Near)",
            blood_group="O+",
            phone=donor_phone,
            age=25,
            gender="M",
            address="Sub-street Kochi",
            state="Kerala",
            district="Ernakulam",
            local_body_type="corporation",
            local_body_name="Kochi Corporation",
            ward_number="5",
            city="Kochi",
            pincode="682011",
            latitude=9.982000,
            longitude=76.267400,
            whatsapp_number="+919988776655"
        )
        await auth_use_cases.register_donor(d_dto)
        logger.info(f"Registered donor user with phone: {donor_phone} with password: donorpassword123")
    else:
        logger.info(f"Donor with phone {donor_phone} already exists.")

    # 4. Seed Ward Member
    ward_phone = "+919998887776"
    existing_ward_user = await db.db.users.find_one({"phone": ward_phone})
    if not existing_ward_user:
        logger.info("Registering test ward member...")
        w_dto = WardMemberRegisterDTO(
            password="wardpassword123",
            full_name="Ward Member A",
            phone=ward_phone,
            designation="Councillor",
            ward_id=ward_id,
            state="Kerala",
            district="Ernakulam",
            local_body_type="corporation",
            local_body_name="Kochi Corporation",
            ward_number="12"
        )
        await ward_use_cases.register_ward_member(w_dto)
        logger.info(f"Registered ward member with phone: {ward_phone} with password: wardpassword123")
    else:
        logger.info(f"Ward member with phone {ward_phone} already exists.")

    await close_mongo_connection()
    logger.info("Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed())
