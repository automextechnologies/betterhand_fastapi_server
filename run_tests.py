import asyncio
import sys
import logging
from datetime import datetime, timedelta, date
from bson import ObjectId

# Override Settings for Test Database before importing app modules
from app.core.config import settings
settings.DB_NAME = "betterhand_db_test"

from app.infrastructure.database.mongodb import db, connect_to_mongo, close_mongo_connection
from app.dependencies.db_repos import get_auth_use_cases, get_donation_use_cases, get_ward_use_cases, get_donor_repository
from app.application.dto.auth_dto import HospitalRegisterDTO, DonorRegisterDTO, UpdateLocationDTO
from app.application.dto.ward_dto import WardMemberRegisterDTO
from app.application.dto.donation_dto import BloodRequestCreateDTO, DonationResponseCreateDTO, DonationRecordCreateDTO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRunner")

async def clear_test_db():
    logger.info("Clearing test database...")
    collections = await db.db.list_collection_names()
    for col in collections:
        await db.db[col].delete_many({})
    logger.info("Cleared all collections in test database.")

async def run_tests():
    logger.info("Starting integration tests...")
    await connect_to_mongo()
    await clear_test_db()
    
    # ─── Initialize dependencies ───
    from app.dependencies.db_repos import (
        get_user_repository, get_hospital_repository, get_donor_repository,
        get_ward_repository, get_ward_member_repository, get_ward_alert_repository,
        get_ward_notif_repository, get_request_repository, get_response_repository,
        get_record_repository, get_rating_repository,
        get_badge_repository, get_camp_repository, get_camp_reg_repository,
        get_notif_repository
    )
    from app.application.use_cases.auth_use_cases import AuthUseCases
    from app.application.use_cases.donation_use_cases import DonationUseCases
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
    camp_repo = get_camp_repository()
    camp_reg_repo = get_camp_reg_repository()
    notif_repo = get_notif_repository()
    
    auth_use_cases = AuthUseCases(user_repo, hospital_repo, donor_repo)
    donation_use_cases = DonationUseCases(
        user_repo=user_repo,
        hospital_repo=hospital_repo,
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
        camp_repo=camp_repo,
        camp_reg_repo=camp_reg_repo,
        notif_repo=notif_repo,
        ws_broadcast_func=ws_broadcast
    )
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
    
    try:
        # 1. Create a Test Ward
        logger.info("Test Step 1: Creating a test ward...")
        ward_doc = {
            "ward_number": "12",
            "local_body_name": "Test Panchayat",
            "local_body_type": "panchayat",
            "district": "Ernakulam",
            "state": "Kerala",
            "location": {
                "type": "Point",
                "coordinates": [76.267304, 9.981636]  # Kochi coordinates
            }
        }
        res_ward = await db.db.wards.insert_one(ward_doc)
        ward_id = str(res_ward.inserted_id)
        logger.info(f"Test Ward created with ID: {ward_id}")
        
        # 2. Register Hospital
        logger.info("Test Step 2: Registering a hospital...")
        h_dto = HospitalRegisterDTO(
            email="test_hospital@betterhand.org",
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
            whatsapp_number="+919876543210"
        )
        h_user = await auth_use_cases.register_hospital(h_dto)
        assert h_user.id is not None
        assert h_user.role == "hospital"
        await auth_use_cases.update_location(h_user.id, "hospital", UpdateLocationDTO(latitude=9.981636, longitude=76.267304))
        logger.info(f"Hospital registered successfully: {h_user.email} (ID: {h_user.id}) and coordinates set.")
        
        # 3. Register Near Donor A (O+ blood, within 5 km)
        logger.info("Test Step 3: Registering Near Donor A...")
        d_a_dto = DonorRegisterDTO(
            password="donorpassword123",
            full_name="Donor A (Near)",
            blood_group="O+",
            phone="+919988776655",
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
            whatsapp_number="+919988776655",
            is_student=False,
            q_weight_ok=True,
            q_age_ok=True,
            q_no_illness=True,
            q_no_medication=True,
            q_no_recent_donation=True,
            q_no_tattoo=True,
            q_no_alcohol=True,
            consent_given=True
        )
        donor_a = await auth_use_cases.register_donor(d_a_dto)
        assert donor_a.id is not None
        await auth_use_cases.update_location(donor_a.id, "donor", UpdateLocationDTO(latitude=9.982000, longitude=76.267400))
        logger.info(f"Donor A registered: {donor_a.phone} (ID: {donor_a.id}) and coordinates set.")
        
        # 4. Register Far Donor B (O+ blood, 15 km away)
        logger.info("Test Step 4: Registering Far Donor B...")
        d_b_dto = DonorRegisterDTO(
            password="donorpassword123",
            full_name="Donor B (Far)",
            blood_group="O+",
            phone="+919988776644",
            age=30,
            gender="F",
            address="Far village",
            state="Kerala",
            district="Ernakulam",
            local_body_type="panchayat",
            local_body_name="Test Panchayat",
            ward_number="12",
            city="Test Town",
            pincode="682025",
            whatsapp_number="+919988776644",
            is_student=False,
            q_weight_ok=True,
            q_age_ok=True,
            q_no_illness=True,
            q_no_medication=True,
            q_no_recent_donation=True,
            q_no_tattoo=True,
            q_no_alcohol=True,
            consent_given=True
        )
        donor_b = await auth_use_cases.register_donor(d_b_dto)
        assert donor_b.id is not None
        await auth_use_cases.update_location(donor_b.id, "donor", UpdateLocationDTO(latitude=10.150000, longitude=76.350000))
        logger.info(f"Donor B registered: {donor_b.phone} (ID: {donor_b.id}) and coordinates set.")
        
        # 4b. Test search_donors repository with radius 10 km and radius 0 (All)
        logger.info("Test Step 4b: Testing search_donors repository with radius 10 km...")
        donor_repo = get_donor_repository()
        donors_10k = await donor_repo.search_donors(
            blood_group="O+",
            longitude=76.267304,
            latitude=9.981636,
            radius_km=10.0
        )
        assert len(donors_10k) == 1
        assert donors_10k[0].user_id == donor_a.id
        logger.info("Radius 10 km search matched only Donor A (near) correctly.")
 
        logger.info("Testing search_donors repository with radius 0 (All)...")
        donors_all = await donor_repo.search_donors(
            blood_group="O+",
            longitude=76.267304,
            latitude=9.981636,
            radius_km=0.0
        )
        assert len(donors_all) >= 2
        donor_ids = [d.user_id for d in donors_all]
        assert donor_a.id in donor_ids
        assert donor_b.id in donor_ids
        logger.info("Radius 0 (All) search matched both Donor A (near) and Donor B (far) successfully!")
        
        # 5. Create Blood Request with 10 km radius (should match only Donor A)
        logger.info("Test Step 5: Creating blood request and matching donors...")
        br_dto = BloodRequestCreateDTO(
            blood_group="O+",
            units_needed=1,
            urgency="critical",
            note="Emergency surgery",
            patient_name="Alex John",
            patient_age=45,
            patient_condition="Severe blood loss",
            patient_state="Kerala",
            patient_district="Ernakulam",
            patient_local_body_type="panchayat",
            patient_local_body_name="Test Panchayat",
            patient_ward_number="12",
            bystander_name="Jane Bystander",
            bystander_phone="+918888888888",
            search_radius_km=10,  # 10 km limit
            notify_ward_members=True,
            ward_member_message="Need help mobilization.",
            ward_id=ward_id
        )
        
        br = await donation_use_cases.create_blood_request(h_user.id, br_dto)
        assert br.id is not None
        assert br.bystander_name == "Jane Bystander"
        assert br.bystander_phone == "+918888888888"
        logger.info(f"Blood Request created with bystander info: ID {br.id}")
        
        # Trigger background matching
        await donation_use_cases.notify_donors_and_wards_background(br.id)
        
        # Verify responses collection
        responses = await db.db.donation_responses.find({"request_id": ObjectId(br.id)}).to_list(length=10)
        assert len(responses) == 1
        assert str(responses[0]["donor_id"]) == donor_a.id
        logger.info("Geospatial Donor Search PASSED: Only Donor A (within 10km radius) matched, Donor B (18km away) excluded.")
        
        # 6. Register Ward Member for the ward
        logger.info("Test Step 6: Registering ward member...")
        wm_dto = WardMemberRegisterDTO(
            password="wardmember123",
            full_name="John Doe",
            phone="+919876500000",
            designation="Ward Councilor",
            state="Kerala",
            district="Ernakulam",
            local_body_type="panchayat",
            local_body_name="Test Panchayat",
            ward_number="12"
        )
        wm_user = await ward_use_cases.register_ward_member(wm_dto)
        assert wm_user.id is not None
        
        # Automatically mark ward member as verified for tests
        await db.db.ward_members.update_one({"user_id": ObjectId(wm_user.id)}, {"$set": {"is_verified": True}})
        logger.info(f"Ward Member registered and verified: {wm_user.phone} (ID: {wm_user.id})")
        
        # Trigger notification match again to notify the newly registered and verified ward member
        await donation_use_cases.notify_donors_and_wards_background(br.id)
        
        # 7. Check Ward Alert Broadcast
        logger.info("Test Step 7: Testing alert broadcasting and mobilization...")
        # Check that alert was created during request background task
        alerts = await db.db.ward_blood_alerts.find({"blood_request_id": ObjectId(br.id)}).to_list(length=10)
        assert len(alerts) == 1
        alert_id = str(alerts[0]["_id"])
        logger.info(f"Ward Blood Alert created automatically: {alert_id}")
        
        # Perform broadcast
        count = await ward_use_cases.broadcast_ward_alert(alert_id)
        # Should notify Donor B who is registered in ward 12, state Kerala, district Ernakulam, local body Test Panchayat
        assert count == 1
        
        # Verify that notification logs were created
        notifs = await db.db.ward_donor_notifications.find({"alert_id": ObjectId(alert_id)}).to_list(length=10)
        assert len(notifs) == 1
        assert str(notifs[0]["donor_id"]) == donor_b.id
        logger.info("Ward Alert Broadcast & Mobilization PASSED.")
        
        # 8. Donor Responds to Request
        logger.info("Test Step 8: Donor responding...")
        resp_id = str(responses[0]["_id"])
        resp_dto = DonationResponseCreateDTO(
            status="accepted",
            donor_latitude=9.982000,
            longitude=76.267400
        )
        await donation_use_cases.donor_respond(resp_id, donor_a.id, resp_dto)
        
        # 9. Hospital Confirms Donor A
        logger.info("Test Step 9: Hospital confirming donor...")
        confirmed_list = await donation_use_cases.confirm_all_top_3(br.id, h_user.id, [resp_id])
        assert len(confirmed_list) == 1
        assert confirmed_list[0].status == "confirmed"
        
        # 10. Complete Donation
        logger.info("Test Step 10: Completing donation and recording...")
        rec_dto = DonationRecordCreateDTO(
            units_donated=1,
            notes="Successful donation. Very prompt."
        )
        record, cooldown = await donation_use_cases.complete_donation(resp_id, h_user.id, rec_dto)
        assert record.id is not None
        assert cooldown == 90
        
        # Verify donor is now on cooldown
        cooldown_status = await db.db.donation_records.find_one({"donor_id": ObjectId(donor_a.id)})
        assert cooldown_status["cooldown_until"] > datetime.utcnow()
        logger.info("Donation Completion & Cooldown verification PASSED.")
        
        logger.info("🏆 ALL INTEGRATION TESTS PASSED SUCCESSFULLY! 🏆")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await clear_test_db()
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run_tests())
