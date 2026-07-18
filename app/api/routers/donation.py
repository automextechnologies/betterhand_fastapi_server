from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
from app.core.config import settings
from app.domain.entities.user import User
from app.domain.entities.donation import (
    BloodRequest, DonationResponse, DonationRecord,
    DonorRating, DonorBadge, BloodCamp, CampRegistration, Notification
)
from app.application.dto.donation_dto import (
    BloodRequestCreateDTO, DonationResponseCreateDTO,
    DonationRecordCreateDTO, DonorRatingCreateDTO,
    BloodCampCreateDTO, BloodCampResponse, CampRegistrationResponse,
    TVScreenDataResponse, NotificationResponseDTO, DonationResponseDonorView
)

from app.application.use_cases.donation_use_cases import DonationUseCases
from app.dependencies.db_repos import get_donation_use_cases
from app.dependencies.auth import get_current_user, require_hospital, require_donor
from app.utils.websocket import manager
from app.infrastructure.external_services.openroute import calculate_driving_distance_and_eta

router = APIRouter()
ws_router = APIRouter()

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
        data = await donation_use_cases.get_request_detail_with_counts(pk, current_user.id)
        r = data["request"]
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
            "total_notified": data["total_notified"],
            "accepted_count": data["accepted_count"],
            "rejected_count": data["rejected_count"],
            "pending_count": data["pending_count"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
        return await donation_use_cases.get_request_top3_details(pk, current_user.id)
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
        confirmed_data = await donation_use_cases.confirm_top3_and_get_details(pk, current_user.id, response_ids)
        
        return {
            "message": f"{len(confirmed_data)} donor(s) confirmed.",
            "confirmed": confirmed_data
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── Donor Response Actions ───

@router.get("/donor/pending-requests/", response_model=List[DonationResponseDonorView])
async def get_donor_pending_requests(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    return await donation_use_cases.get_donor_pending_requests_view(current_user.id)

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
        return {
            "message": f"Response: {dto.status}.",
            "eta_minutes": eta
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
        res = await donation_use_cases.no_donation_arrived_with_details(pk, current_user.id)
        msg = "Marked arrived (no donation, no cooldown)."
        if res["promoted"]:
            msg += f" Next donor {res['promoted_name']} auto-confirmed."
        return {
            "message": msg,
            "promoted": res["promoted"]
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
        res = await donation_use_cases.cancel_donor_assignment_with_details(pk, current_user.id)
        msg = "Donor cancelled."
        if res["promoted"]:
            msg += f" {res['promoted_name']} auto-promoted as replacement."
        return {
            "message": msg,
            "promoted": res["promoted"]
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

@router.get("/donor/responses/", response_model=List[DonationResponseDonorView])
async def list_donor_responses(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    return await donation_use_cases.list_donor_responses_view(current_user.id)

@router.get("/donor/history/")
async def list_donor_history(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    return await donation_use_cases.get_donor_history(current_user.id)

@router.get("/donor/cooldown/")
async def get_cooldown_status(
    current_user: User = Depends(require_donor),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    return await donation_use_cases.get_donor_cooldown_status(current_user.id)


# ─── Dashboard & Analytics ───

@router.get("/dashboard/")
async def get_hospital_dashboard(
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    return await donation_use_cases.get_hospital_dashboard_formatted(current_user.id)

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
    return await donation_use_cases.list_active_camps_formatted(city, blood_group)

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
    return await donation_use_cases.get_donor_camp_registrations_formatted(current_user.id)

@router.get("/my/camps/")
async def get_hospital_camps(
    current_user: User = Depends(require_hospital),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    return await donation_use_cases.get_hospital_camps_formatted(current_user.id)


# ─── Directions and Notifications ───

@router.get("/notifications/")
async def get_notifications(
    current_user: User = Depends(get_current_user),
    donation_use_cases: DonationUseCases = Depends(get_donation_use_cases)
):
    notifs = await donation_use_cases.get_notifications(current_user.id)
    return [{
        "id": n.id,
        "title": getattr(n, "title", getattr(n, "subject", "")),
        "body": n.body,
        "data": getattr(n, "data", {}),
        "is_read": getattr(n, "is_read", False),
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

@ws_router.websocket("/ws/donation/")
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
        
    from app.dependencies.db_repos import get_user_repository
    user_repo = get_user_repository()
    user = await user_repo.get_by_id(user_id)
    if not user:
        logger.warning(f"WebSocket connection rejected: User ID '{user_id}' not found in the database.")
        await websocket.close(code=4001)
        return
        
    if not user.is_active:
        logger.warning(f"WebSocket connection rejected: User '{user_id}' is marked as inactive.")
        await websocket.close(code=4001)
        return
        
    user_role = user.role
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
            
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        # Disconnect from all rooms
        for r in list(joined_rooms):
            manager.disconnect(websocket, r)
