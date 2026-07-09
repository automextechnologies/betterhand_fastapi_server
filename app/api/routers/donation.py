from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
from app.core.config import settings
from app.infrastructure.database.mongodb import db
from app.domain.entities.user import User
from app.domain.entities.donation import (
    BloodRequest, DonationResponse, DonationRecord, ChatMessage,
    DonorRating, DonorBadge, BloodCamp, CampRegistration, Notification
)
from app.application.dto.donation_dto import (
    BloodRequestCreateDTO, DonationResponseCreateDTO,
    DonationRecordCreateDTO, ChatMessageCreateDTO, DonorRatingCreateDTO,
    BloodCampCreateDTO, BloodCampResponse, CampRegistrationResponse,
    TVScreenDataResponse, NotificationResponseDTO
)

from app.application.use_cases.donation_use_cases import DonationUseCases
from app.dependencies.db_repos import get_donation_use_cases
from app.dependencies.auth import get_current_user, require_hospital, require_donor
from app.utils.websocket import manager
from app.infrastructure.external_services.openroute import calculate_driving_distance_and_eta

router = APIRouter()

# Helper to verify ObjectId strings
def get_object_id_or_404(pk: str) -> ObjectId:
    try:
        return ObjectId(pk)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid ID format.")

# ─── Blood Requests Endpoints ───

@router.post("/requests/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_request(
    dto: BloodRequestCreateDTO,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        br = await donation_use_cases.create_blood_request(current_user.id, dto)
        # Enqueue background task for donor and ward member notification
        bg_tasks.add_task(donation_use_cases.notify_donors_and_wards_background, br.id)
        
        # Serialize response matching django
        return {
            "id": br.id,
            "blood_group": br.blood_group,
            "units_needed": br.units_needed,
            "urgency": br.urgency,
            "status": br.status,
            "patient_name": br.patient_name,
            "patient_condition": br.patient_condition,
            "bystander_name": br.bystander_name,
            "bystander_phone": br.bystander_phone,
            "created_at": br.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/requests/hospital/")
async def list_hospital_requests(
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    reqs = await donation_use_cases.get_hospital_requests(current_user.id, status)
    results = []
    for r in reqs:
        results.append({
            "id": r.id,
            "blood_group": r.blood_group,
            "units_needed": r.units_needed,
            "urgency": r.urgency,
            "status": r.status,
            "patient_name": r.patient_name,
            "patient_condition": r.patient_condition,
            "bystander_name": r.bystander_name,
            "bystander_phone": r.bystander_phone,
            "created_at": r.created_at
        })
    return results

@router.get("/requests/{pk}/")
async def get_request_detail(
    pk: str,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        r = await donation_use_cases.get_request_detail(pk, current_user.id)
        # get counts
        responses = await db.db.donation_responses.find({"request_id": ObjectId(pk)}).to_list(length=1000)
        accepted_cnt = len([x for x in responses if x.get("status") in ("accepted", "confirmed")])
        rejected_cnt = len([x for x in responses if x.get("status") == "rejected"])
        pending_cnt = len([x for x in responses if x.get("status") == "pending"])
        
        return {
            "id": r.id,
            "blood_group": r.blood_group,
            "units_needed": r.units_needed,
            "urgency": r.urgency,
            "status": r.status,
            "patient_name": r.patient_name,
            "patient_age": r.patient_age,
            "patient_condition": r.patient_condition,
            "patient_ward": r.patient_ward,
            "patient_room": r.patient_room,
            "patient_bed": r.patient_bed,
            "ward_contact_person": r.ward_contact_person,
            "ward_contact_phone": r.ward_contact_phone,
            "bystander_name": r.bystander_name,
            "bystander_phone": r.bystander_phone,
            "hospital_latitude": r.hospital_latitude,
            "hospital_longitude": r.hospital_longitude,
            "created_at": r.created_at,
            "total_notified": len(responses),
            "accepted_count": accepted_cnt,
            "rejected_count": rejected_cnt,
            "pending_count": pending_cnt
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/requests/{pk}/cancel/")
async def cancel_request(
    pk: str,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        await donation_use_cases.cancel_request(pk, current_user.id)
        return {"message": "Cancelled."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/requests/{pk}/top3/")
async def get_request_top3(
    pk: str,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        top_3 = await donation_use_cases.get_top_3_donors(pk, current_user.id)
        
        # Count helper
        responses = await db.db.donation_responses.find({"request_id": ObjectId(pk)}).to_list(length=1000)
        total_accepted = len([x for x in responses if x.get("status") in ("accepted", "confirmed")])
        pending_count = len([x for x in responses if x.get("status") == "pending"])
        rejected_count = len([x for x in responses if x.get("status") == "rejected"])
        
        top_3_data = []
        for r in top_3:
            dp = await db.db.donor_profiles.find_one({"user_id": ObjectId(r.donor_id)})
            top_3_data.append({
                "id": r.id,
                "donor_id": r.donor_id,
                "donor_name": dp.get("full_name", "") if dp else "Donor",
                "donor_phone": dp.get("phone", "") if dp else "",
                "status": r.status,
                "distance_km": r.distance_km,
                "eta_minutes": r.eta_minutes
            })
            
        return {
            "request_id": pk,
            "top_3": top_3_data,
            "total_accepted": total_accepted,
            "pending_count": pending_count,
            "rejected_count": rejected_count
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/requests/{pk}/confirm-all/")
async def confirm_all_top3(
    pk: str,
    data: dict,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        response_ids = data.get("response_ids", [])
        confirmed = await donation_use_cases.confirm_all_top_3(pk, current_user.id, response_ids)
        
        confirmed_data = []
        for r in confirmed:
            dp = await db.db.donor_profiles.find_one({"user_id": ObjectId(r.donor_id)})
            confirmed_data.append({
                "id": r.id,
                "donor_id": r.donor_id,
                "donor_name": dp.get("full_name", "") if dp else "Donor",
                "donor_phone": dp.get("phone", "") if dp else "",
                "status": r.status,
                "distance_km": r.distance_km,
                "eta_minutes": r.eta_minutes
            })
            
        return {
            "message": f"{len(confirmed)} donor(s) confirmed.",
            "confirmed": confirmed_data
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── Donor Response Actions ───

@router.get("/donor/pending-requests/")
async def get_donor_pending_requests(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    pending = await donation_use_cases.get_donor_pending_requests(current_user.id)
    results = []
    for r in pending:
        br = await db.db.blood_requests.find_one({"_id": ObjectId(r.request_id)})
        hp = await db.db.hospital_profiles.find_one({"user_id": ObjectId(br["hospital_id"])}) if br else None
        
        results.append({
            "id": r.id,
            "request": {
                "id": r.request_id,
                "blood_group": br.get("blood_group") if br else "",
                "units_needed": br.get("units_needed") if br else 1,
                "urgency": br.get("urgency") if br else "normal",
                "patient_name": br.get("patient_name") if br else "",
                "patient_condition": br.get("patient_condition") if br else "",
                "bystander_name": br.get("bystander_name", "") if br else "",
                "bystander_phone": br.get("bystander_phone", "") if br else "",
                "hospital_name": hp.get("name") if hp else "Hospital",
                "hospital_phone": hp.get("phone") if hp else "",
                "hospital_whatsapp": hp.get("whatsapp_number") if hp else "",
                "hospital_latitude": br.get("hospital_latitude") if br else None,
                "hospital_longitude": br.get("hospital_longitude") if br else None,
                "note": br.get("note") if br else ""
            },
            "status": r.status,
            "created_at": r.created_at
        })
    return results

@router.post("/responses/{pk}/respond/")
async def respond_to_request(
    pk: str,
    dto: DonationResponseCreateDTO,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        eta = await donation_use_cases.donor_respond(pk, current_user.id, dto)
        if dto.status == "accepted":
            # Schedule exact routing computation
            bg_tasks.add_task(donation_use_cases.calculate_live_eta_background, pk)
        return {
            "message": f"Response: {dto.status}.",
            "eta_minutes": eta
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/responses/{pk}/location/")
@router.post("/responses/{pk}/location/")
async def update_response_location(
    pk: str,
    data: dict,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    lat = data.get("latitude")
    lng = data.get("longitude")
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="latitude and longitude required.")
        
    try:
        dist = await donation_use_cases.update_donor_live_location(pk, current_user.id, float(lat), float(lng))
        # Trigger background routing update
        bg_tasks.add_task(donation_use_cases.calculate_live_eta_background, pk)
        return {
            "message": "Location updated.",
            "distance_remaining_km": dist
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/responses/{pk}/no-donation/")
async def no_donation(
    pk: str,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        promoted = await donation_use_cases.no_donation_arrived(pk, current_user.id)
        msg = "Marked arrived (no donation, no cooldown)."
        if promoted:
            dp = await db.db.donor_profiles.find_one({"user_id": ObjectId(promoted.donor_id)})
            name = dp.get("full_name", "") if dp else "Next donor"
            msg += f" Next donor {name} auto-confirmed."
        return {
            "message": msg,
            "promoted": bool(promoted)
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/responses/{pk}/cancel/")
async def cancel_response(
    pk: str,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        promoted = await donation_use_cases.cancel_donor_assignment(pk, current_user.id)
        msg = "Donor cancelled."
        if promoted:
            dp = await db.db.donor_profiles.find_one({"user_id": ObjectId(promoted.donor_id)})
            name = dp.get("full_name", "") if dp else "Next donor"
            msg += f" {name} auto-promoted as replacement."
        return {
            "message": msg,
            "promoted": bool(promoted)
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/responses/{pk}/complete/")
async def complete_donation(
    pk: str,
    dto: DonationRecordCreateDTO,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        record, cooldown = await donation_use_cases.complete_donation(pk, current_user.id, dto)
        return {
            "message": "✅ Donation completed and recorded.",
            "record_id": record.id,
            "cooldown_until": record.cooldown_until.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/donor/responses/")
async def list_donor_responses(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    # Retrieve all donor responses
    resps = await db.db.donation_responses.find({"donor_id": ObjectId(current_user.id)}).sort("created_at", -1).to_list(length=1000)
    results = []
    for r in resps:
        br = await db.db.blood_requests.find_one({"_id": r["request_id"]})
        hp = await db.db.hospital_profiles.find_one({"user_id": br["hospital_id"]}) if br else None
        
        results.append({
            "id": str(r["_id"]),
            "request": {
                "id": str(r["request_id"]),
                "blood_group": br.get("blood_group") if br else "",
                "units_needed": br.get("units_needed") if br else 1,
                "urgency": br.get("urgency") if br else "normal",
                "patient_name": br.get("patient_name") if br else "",
                "patient_condition": br.get("patient_condition") if br else "",
                "bystander_name": br.get("bystander_name", "") if br else "",
                "bystander_phone": br.get("bystander_phone", "") if br else "",
                "hospital_name": hp.get("name") if hp else "Hospital",
                "hospital_phone": hp.get("phone") if hp else "",
                "hospital_whatsapp": hp.get("whatsapp_number") if hp else "",
                "hospital_latitude": br.get("hospital_latitude") if br else None,
                "hospital_longitude": br.get("hospital_longitude") if br else None,
                "note": br.get("note") if br else ""
            },
            "status": r.get("status"),
            "created_at": r.get("created_at")
        })
    return results

@router.get("/donor/history/")
async def list_donor_history(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    records = await db.db.donation_records.find({"donor_id": ObjectId(current_user.id)}).sort("donated_at", -1).to_list(length=1000)
    results = []
    for r in records:
        results.append({
            "id": str(r["_id"]),
            "blood_group": r.get("blood_group"),
            "units_donated": r.get("units_donated", 1),
            "hospital_name": r.get("hospital_name"),
            "hospital_city": r.get("hospital_city"),
            "donated_at": r.get("donated_at"),
            "notes": r.get("notes")
        })
    return results

@router.get("/donor/cooldown/")
async def get_cooldown_status(
    current_user: User = Depends(require_donor)
):
    last = await db.db.donation_records.find_one({"donor_id": ObjectId(current_user.id)}, sort=[("donated_at", -1)])
    if not last:
        return {
            "is_on_cooldown": False,
            "last_donation": None,
            "cooldown_until": None,
            "days_remaining": 0
        }
        
    now = datetime.utcnow()
    cd_until = last.get("cooldown_until")
    on_cd = now < cd_until if cd_until else False
    days = max(0, (cd_until - now).days) if on_cd else 0
    
    return {
        "is_on_cooldown": on_cd,
        "last_donation": last.get("donated_at"),
        "cooldown_until": cd_until,
        "days_remaining": days
    }


# ─── Dashboard & Analytics ───

@router.get("/dashboard/")
async def get_hospital_dashboard(
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    data = await donation_use_cases.get_hospital_dashboard(current_user.id)
    
    formatted_active = []
    for item in data["active_requests"]:
        br = item["request"]
        top_3 = item["top_3"]
        confirmed_donors = item["confirmed_donors"]
        
        top_3_list = []
        for r in top_3:
            dp = await db.db.donor_profiles.find_one({"user_id": ObjectId(r.donor_id)})
            top_3_list.append({
                "id": r.id,
                "donor_id": r.donor_id,
                "donor_name": dp.get("full_name", "") if dp else "Donor",
                "donor_phone": dp.get("phone", "") if dp else "",
                "status": r.status,
                "distance_km": r.distance_km,
                "eta_minutes": r.eta_minutes
            })
            
        confirmed_list = []
        for r in confirmed_donors:
            dp = await db.db.donor_profiles.find_one({"user_id": ObjectId(r.donor_id)})
            confirmed_list.append({
                "id": r.id,
                "donor_id": r.donor_id,
                "donor_name": dp.get("full_name", "") if dp else "Donor",
                "donor_phone": dp.get("phone", "") if dp else "",
                "status": r.status,
                "distance_km": r.distance_km,
                "eta_minutes": r.eta_minutes
            })
            
        formatted_active.append({
            "request": {
                "id": br.id,
                "blood_group": br.blood_group,
                "units_needed": br.units_needed,
                "urgency": br.urgency,
                "status": br.status,
                "patient_name": br.patient_name,
                "patient_condition": br.patient_condition,
                "bystander_name": br.bystander_name,
                "bystander_phone": br.bystander_phone,
                "created_at": br.created_at
            },
            "top_3": top_3_list,
            "total_notified": item["total_notified"],
            "accepted_count": item["accepted_count"],
            "rejected_count": item["rejected_count"],
            "pending_count": item["pending_count"],
            "confirmed_donors": confirmed_list
        })
        
    return {
        "stats": data["stats"],
        "active_requests": formatted_active
    }

@router.get("/tv/{hospital_id}/")
async def get_tv_data(
    hospital_id: str,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    if current_user.id != hospital_id:
        raise HTTPException(status_code=403, detail="Forbidden.")
        
    data = await donation_use_cases.get_tv_screen_data(hospital_id)
    if not data["active_request"]:
        return {
            "active_request": None,
            "confirmed_donors": []
        }
        
    br = data["active_request"]
    return {
        "hospital": data["hospital"],
        "active_request": {
            "id": br.id,
            "blood_group": br.blood_group,
            "units_needed": br.units_needed,
            "urgency": br.urgency,
            "status": br.status,
            "patient_name": br.patient_name,
            "patient_condition": br.patient_condition,
            "bystander_name": br.bystander_name,
            "bystander_phone": br.bystander_phone,
            "created_at": br.created_at
        },
        "confirmed_donors": data["confirmed_donors"]
    }

@router.get("/analytics/")
async def get_analytics(
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    return await donation_use_cases.get_analytics(current_user.id)


# ─── Chat ───

@router.get("/chat/{response_id}/messages/")
async def get_chat_history(
    response_id: str,
    current_user: User = Depends(get_current_user),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        resp, messages = await donation_use_cases.get_chat_history(response_id, current_user.id)
        results = []
        for m in messages:
            # Resolve sender name
            sender_name = "User"
            sender_role = "donor"
            sender_doc = await db.db.users.find_one({"_id": ObjectId(m.sender_id)})
            if sender_doc:
                sender_role = sender_doc.get("role", "donor")
                if sender_role == "donor":
                    dp = await db.db.donor_profiles.find_one({"user_id": sender_doc["_id"]})
                    sender_name = dp.get("full_name", "") if dp else "Donor"
                elif sender_role == "hospital":
                    hp = await db.db.hospital_profiles.find_one({"user_id": sender_doc["_id"]})
                    sender_name = hp.get("name", "") if hp else "Hospital"
            results.append({
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_name": sender_name,
                "sender_role": sender_role,
                "message": m.message,
                "created_at": m.created_at,
                "is_read": m.is_read
            })
        return results
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/chat/{response_id}/messages/", status_code=status.HTTP_201_CREATED)
async def post_chat_message(
    response_id: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    text = data.get("message", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
    try:
        msg = await donation_use_cases.create_chat_message(response_id, current_user.id, current_user.role, text)
        return {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "message": msg.message,
            "created_at": msg.created_at,
            "is_read": msg.is_read
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/chat/unread/")
async def get_unread_chat(
    current_user: User = Depends(get_current_user)
):
    # Find responses where user is sender/receiver
    if current_user.role == "donor":
        resps = await db.db.donation_responses.find({"donor_id": ObjectId(current_user.id)}).to_list(length=1000)
    else:
        reqs = await db.db.blood_requests.find({"hospital_id": ObjectId(current_user.id)}).to_list(length=1000)
        req_ids = [r["_id"] for r in reqs]
        resps = await db.db.donation_responses.find({"request_id": {"$in": req_ids}}).to_list(length=1000)
        
    resp_ids = [str(r["_id"]) for r in resps]
    pipeline = [
        {"$match": {
            "response_id": {"$in": resp_ids},
            "is_read": False,
            "sender_id": {"$ne": ObjectId(current_user.id)}
        }},
        {"$group": {
            "_id": "$response_id",
            "unread": {"$sum": 1}
        }}
    ]
    cursor = db.db.chat_messages.aggregate(pipeline)
    counts = await cursor.to_list(length=1000)
    return {str(c["_id"]): c["unread"] for c in counts}


# ─── Rating & Badges ───

@router.post("/records/{record_id}/rate/", status_code=status.HTTP_201_CREATED)
async def rate_donor(
    record_id: str,
    dto: DonorRatingCreateDTO,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        rating = await donation_use_cases.rate_donor(record_id, current_user.id, dto)
        return {
            "id": rating.id,
            "record_id": rating.record_id,
            "stars": rating.stars,
            "punctuality": rating.punctuality,
            "fitness": rating.fitness,
            "feedback": rating.feedback
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/my/badges/")
async def get_my_badges(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    badges = await donation_use_cases.get_donor_badges(current_user.id)
    return [{"id": b.id, "badge": b.badge, "earned_at": b.earned_at} for b in badges]


# ─── Blood Camps ───

@router.get("/camps/")
async def list_active_camps(
    city: Optional[str] = Query(None),
    blood_group: Optional[str] = Query(None),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    camps = await donation_use_cases.list_active_camps(city, blood_group)
    results = []
    for c in camps:
        # Load registered count
        count = await db.db.camp_registrations.count_documents({"camp_id": ObjectId(c.id), "status": "registered"})
        
        hp = await db.db.hospital_profiles.find_one({"user_id": ObjectId(c.hospital_id)})
        hospital_name = hp.get("name") if hp else "Hospital"
        
        results.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "location": c.location,
            "city": c.city,
            "state": c.state,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "scheduled_date": c.scheduled_date.isoformat(),
            "start_time": c.start_time,
            "end_time": c.end_time,
            "capacity": c.capacity,
            "target_blood_groups": c.target_blood_groups,
            "registered_count": count,
            "is_full": count >= c.capacity,
            "hospital_name": hospital_name
        })
    return results

@router.post("/camps/", status_code=status.HTTP_201_CREATED)
async def create_camp(
    dto: BloodCampCreateDTO,
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    c = await donation_use_cases.create_blood_camp(current_user.id, dto)
    return {
        "id": c.id,
        "title": c.title,
        "location": c.location,
        "scheduled_date": c.scheduled_date.isoformat(),
        "capacity": c.capacity
    }

@router.post("/camps/{pk}/register/", status_code=status.HTTP_201_CREATED)
async def register_camp(
    pk: str,
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        reg = await donation_use_cases.register_donor_for_camp(pk, current_user.id)
        return {
            "message": "Registered." if reg.status == "registered" else "Re-registered.",
            "registration_id": reg.id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/camps/{pk}/register/")
async def cancel_camp_registration(
    pk: str,
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    try:
        await donation_use_cases.cancel_camp_registration(pk, current_user.id)
        return {"message": "Registration cancelled."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/my/camp-registrations/")
async def get_my_camp_registrations(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    regs = await donation_use_cases.get_donor_camp_registrations(current_user.id)
    results = []
    for r in regs:
        c = await db.db.blood_camps.find_one({"_id": ObjectId(r.camp_id)})
        if c:
            hp = await db.db.hospital_profiles.find_one({"user_id": c["hospital_id"]})
            hospital_name = hp.get("name") if hp else "Hospital"
            results.append({
                "id": r.id,
                "camp": {
                    "id": str(c["_id"]),
                    "title": c.get("title"),
                    "location": c.get("location"),
                    "scheduled_date": c.get("scheduled_date").isoformat() if isinstance(c.get("scheduled_date"), datetime) else str(c.get("scheduled_date")),
                    "hospital_name": hospital_name
                },
                "status": r.status,
                "registered_at": r.registered_at
            })
    return results

@router.get("/my/camps/")
async def get_hospital_camps(
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    camps = await donation_use_cases.get_hospital_camps(current_user.id)
    results = []
    for c in camps:
        count = await db.db.camp_registrations.count_documents({"camp_id": ObjectId(c.id), "status": "registered"})
        results.append({
            "id": c.id,
            "title": c.title,
            "location": c.location,
            "scheduled_date": c.scheduled_date.isoformat(),
            "capacity": c.capacity,
            "registered_count": count,
            "is_full": count >= c.capacity
        })
    return results


# ─── Directions and Notifications ───

@router.get("/notifications/")
async def get_notifications(
    current_user: User = Depends(get_current_user),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    notifs = await donation_use_cases.get_notifications(current_user.id)
    return [{
        "id": n.id,
        "title": n.title,
        "body": n.body,
        "data": n.data,
        "is_read": n.is_read,
        "created_at": n.created_at
    } for n in notifs]

@router.get("/directions/")
async def get_directions(
    origin: str = Query(...),
    destination: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    if not origin or not destination:
        raise HTTPException(status_code=400, detail="origin and destination required.")
        
    try:
        o_lat, o_lng = map(float, origin.split(","))
        d_lat, d_lng = map(float, destination.split(","))
    except Exception:
        raise HTTPException(status_code=400, detail="Coords format must be 'lat,lng'.")
        
    route_data = await calculate_driving_distance_and_eta(o_lat, o_lng, d_lat, d_lng)
    if not route_data:
        return {"status": "NO_KEY", "routes": []}
        
    dur = route_data["duration_seconds"]
    dist = route_data["distance_meters"]
    
    return {
        "status": "OK",
        "routes": [{
            "overview_polyline": {"points": route_data.get("geometry", "")},
            "legs": [{
                "duration": {"value": int(dur), "text": f"{int(dur // 60)} mins"},
                "distance": {"value": int(dist), "text": f"{round(dist / 1000, 1)} km"}
            }]
        }]
    }

@router.post("/clear-data/")
async def clear_hospital_data(
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    count = await donation_use_cases.clear_hospital_data(current_user.id)
    return {"message": f"Cleared {count} blood requests and all related data."}


# ─── WebSocket Endpoint ───

@router.websocket("/ws/donation/")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    if not token:
        logger.warning("WebSocket connection rejected: No token query parameter provided.")
        await websocket.close(code=4001)
        return
        
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        logger.warning(f"WebSocket connection rejected: Token is invalid, expired, or signature verification failed. Token prefix: {token[:15]}...")
        await websocket.close(code=4001)
        return
        
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("WebSocket connection rejected: Token payload is missing the 'sub' field.")
        await websocket.close(code=4001)
        return
        
    user_doc = await db.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        logger.warning(f"WebSocket connection rejected: User ID '{user_id}' not found in the database.")
        await websocket.close(code=4001)
        return
        
    if not user_doc.get("is_active"):
        logger.warning(f"WebSocket connection rejected: User '{user_id}' is marked as inactive.")
        await websocket.close(code=4001)
        return
        
    user_role = user_doc.get("role")
    if user_role == "hospital":
        group_name = f"hospital_{user_id}"
    elif user_role == "donor":
        group_name = f"donor_{user_id}"
    elif user_role == "ward_member":
        group_name = f"ward_{user_id}"
    else:
        logger.warning(f"WebSocket connection rejected: User '{user_id}' has an invalid role '{user_role}'.")
        await websocket.close(code=4001)
        return
        
    # Join role-specific group
    await manager.connect(websocket, group_name)
    
    # Hospitals also join TV screen group
    if user_role == "hospital":
        await manager.connect(websocket, f"tv_{user_id}")
        
    # Keep track of room names this websocket joins
    joined_rooms = {group_name}
    if user_role == "hospital":
        joined_rooms.add(f"tv_{user_id}")
        
    try:
        # Welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected",
            "role": user_role
        })
        
        while True:
            # Keep connection open and handle incoming text messages
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "join_chat":
                response_id = data.get("response_id")
                if response_id:
                    room = f"chat_{response_id}"
                    await manager.connect(websocket, room)
                    joined_rooms.add(room)
                    await websocket.send_json({
                        "type": "chat_joined",
                        "response_id": response_id
                    })
                    
            elif msg_type == "leave_chat":
                response_id = data.get("response_id")
                if response_id:
                    room = f"chat_{response_id}"
                    manager.disconnect(websocket, room)
                    joined_rooms.discard(room)
                    
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        # Disconnect from all rooms
        for r in list(joined_rooms):
            manager.disconnect(websocket, r)
