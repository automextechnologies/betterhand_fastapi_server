from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from datetime import datetime
from app.domain.entities.user import User
from app.domain.entities.ward import WardMember, Ward, WardBloodAlert

from app.application.dto.ward_dto import (
    WardMemberRegisterDTO, WardMemberProfileResponse, WardResponse,
    WardBloodAlertResponse, WardTopDonorDTO, WardDonorNotificationResponse
)
from app.application.use_cases.ward_use_cases import WardUseCases
from app.dependencies.db_repos import get_ward_use_cases, get_ward_repository, get_ward_member_repository, get_ward_alert_repository, get_ward_notif_repository
from app.dependencies.auth import get_current_user, require_ward_member
from app.domain.repositories.ward_repo import WardRepository, WardMemberRepository, WardBloodAlertRepository, WardDonorNotificationRepository
from app.infrastructure.database.mongodb import db
from bson import ObjectId

router = APIRouter()

@router.post("/register/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_ward_member(
    dto: WardMemberRegisterDTO,
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_repo: WardRepository = Depends(get_ward_repository)
):
    try:
        user = await ward_use_cases.register_ward_member(dto)
        from app.core.security import create_access_token, create_refresh_token
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        
        profile, ward = await ward_use_cases.get_ward_member_profile(user.id)
        ward_data = None
        if ward:
            ward_data = ward.__dict__.copy()
            ward_data["id"] = ward.id
            
        return {
            "message": "Registered successfully. Await admin verification.",
            "access": access,
            "refresh": refresh,
            "role": user.role,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role
            },
            "member": {
                "id": profile.id,
                "full_name": profile.full_name,
                "is_verified": profile.is_verified,
                "ward": ward_data
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login/")
async def login_ward_member(
    data: dict,
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    user_repo = Depends(get_ward_use_cases) # we get user repo, or use raw mongo
):
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password required.")
        
    user_doc = await db.db.users.find_one({"email": email})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
        
    from app.core.security import verify_password, create_access_token, create_refresh_token
    if not verify_password(password, user_doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
        
    if user_doc.get("role") != "ward_member":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a ward member account.")
        
    # Update FCM token
    fcm_token = data.get("fcm_token", "").strip()
    if fcm_token:
        await db.db.users.update_one({"_id": user_doc["_id"]}, {"$set": {"fcm_token": fcm_token}})
        
    user_id = str(user_doc["_id"])
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    
    profile, ward = await ward_use_cases.get_ward_member_profile(user_id)
    ward_data = None
    if ward:
        ward_data = ward.__dict__.copy()
        ward_data["id"] = ward.id
        
    return {
        "access": access,
        "refresh": refresh,
        "role": user_doc["role"],
        "user": {
            "id": user_id,
            "email": user_doc["email"],
            "role": user_doc["role"],
            "profile": {
                "id": profile.id,
                "full_name": profile.full_name,
                "phone": profile.phone,
                "designation": profile.designation,
                "is_verified": profile.is_verified,
                "ward": ward_data
            }
        },
        "member": {
            "id": profile.id,
            "full_name": profile.full_name,
            "phone": profile.phone,
            "is_verified": profile.is_verified,
            "ward": ward_data
        }
    }

@router.post("/logout/")
async def logout():
    return {"message": "Logged out."}

@router.get("/profile/", response_model=WardMemberProfileResponse)
async def get_profile(
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    
    # Nested members mapping for WardResponse model
    members_data = []
    if ward:
        m_docs = await db.db.ward_members.find({"ward_id": ObjectId(ward.id)}).to_list(length=100)
        for m in m_docs:
            members_data.append({
                "id": str(m["_id"]),
                "full_name": m.get("full_name", ""),
                "phone": m.get("phone", ""),
                "designation": m.get("designation", ""),
                "is_verified": m.get("is_verified", False)
            })
            
    ward_resp = None
    if ward:
        ward_resp = WardResponse(
            id=ward.id,
            ward_number=ward.ward_number,
            local_body_name=ward.local_body_name,
            local_body_type=ward.local_body_type,
            district=ward.district,
            state=ward.state,
            latitude=ward.latitude,
            longitude=ward.longitude,
            members=members_data
        )
        
    return WardMemberProfileResponse(
        id=profile.id,
        email=current_user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        designation=profile.designation,
        is_verified=profile.is_verified,
        ward=ward_resp
    )

@router.patch("/profile/", response_model=WardMemberProfileResponse)
async def update_profile(
    data: dict,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_member_repo: WardMemberRepository = Depends(get_ward_member_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    for k, v in data.items():
        if hasattr(profile, k) and k not in ("id", "user_id", "created_at", "ward_id"):
            setattr(profile, k, v)
            
    await ward_member_repo.update(profile)
    
    # Reload profile
    return await get_profile(current_user, ward_use_cases)

@router.post("/fcm-token/")
async def update_fcm_token(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    token = data.get("fcm_token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="fcm_token required.")
    await db.db.users.update_one({"_id": ObjectId(current_user.id)}, {"$set": {"fcm_token": token}})
    return {"message": "FCM token updated."}

@router.get("/wards/", response_model=List[WardResponse])
async def list_wards(
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    local_body_name: Optional[str] = Query(None),
    local_body_type: Optional[str] = Query(None),
    ward_number: Optional[str] = Query(None),
    has_member: Optional[str] = Query(None),
    ward_repo: WardRepository = Depends(get_ward_repository)
):
    filters = {}
    if state: filters["state"] = state
    if district: filters["district"] = district
    if local_body_name: filters["local_body_name"] = local_body_name
    if local_body_type: filters["local_body_type"] = local_body_type
    if ward_number: filters["ward_number"] = ward_number
    
    members_verified = has_member == "true"
    wards = await ward_repo.search_wards(filters, has_member=members_verified)
    
    results = []
    for w in wards:
        m_docs = await db.db.ward_members.find({"ward_id": ObjectId(w.id)}).to_list(length=100)
        members_data = []
        for m in m_docs:
            members_data.append({
                "id": str(m["_id"]),
                "full_name": m.get("full_name", ""),
                "phone": m.get("phone", ""),
                "designation": m.get("designation", ""),
                "is_verified": m.get("is_verified", False)
            })
        results.append(WardResponse(
            id=w.id,
            ward_number=w.ward_number,
            local_body_name=w.local_body_name,
            local_body_type=w.local_body_type,
            district=w.district,
            state=w.state,
            latitude=w.latitude,
            longitude=w.longitude,
            members=members_data
        ))
    return results

@router.get("/dashboard/")
async def get_dashboard(
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_alert_repo: WardBloodAlertRepository = Depends(get_ward_alert_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    if not ward:
        raise HTTPException(status_code=400, detail="Ward not associated.")
        
    alerts = await ward_alert_repo.list_by_member(profile.id)
    
    # Strict ward match for count of local donors
    ward_q = {
        "ward_number": str(ward.ward_number),
        "local_body_name": {"$regex": f"^{ward.local_body_name}$", "$options": "i"},
        "state": {"$regex": f"^{ward.state}$", "$options": "i"}
    }
    total_donors = await db.db.donor_profiles.count_documents(ward_q)
    avail_donors = await db.db.donor_profiles.count_documents({**ward_q, "is_available": True})
    
    recent_alerts_data = []
    # Fetch details for the first 5 alerts
    from app.infrastructure.repositories.mongo_ward_repo import map_alert_to_entity
    for a in alerts[:5]:
        recent_alerts_data.append({
            "id": a.id,
            "blood_group": a.blood_group,
            "urgency": a.urgency,
            "patient_name": a.patient_name,
            "patient_condition": a.patient_condition,
            "hospital_name": a.hospital_name,
            "hospital_phone": a.hospital_phone,
            "hospital_whatsapp": a.hospital_whatsapp,
            "bystander_phone": a.bystander_phone,
            "hospital_latitude": a.hospital_latitude,
            "hospital_longitude": a.hospital_longitude,
            "hospital_message": a.hospital_message,
            "status": a.status,
            "ward_name": ward.local_body_name,
            "ward_number": ward.ward_number,
            "member_name": profile.full_name,
            "member_phone": profile.phone,
            "blood_request_id": a.blood_request_id,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "created_at": a.created_at.isoformat()
        })
        
    ward_data = ward.__dict__.copy()
    ward_data["id"] = ward.id
    
    return {
        "ward": ward_data,
        "member_name": profile.full_name,
        "is_verified": profile.is_verified,
        "alerts": {
            "total": len(alerts),
            "pending": len([x for x in alerts if x.status == "pending"]),
            "notified": len([x for x in alerts if x.status == "notified"]),
            "resolved": len([x for x in alerts if x.status == "resolved"])
        },
        "ward_donors": {
            "total": total_donors,
            "available": avail_donors
        },
        "recent_alerts": recent_alerts_data
    }

@router.get("/donors/")
async def list_ward_donors(
    blood_group: Optional[str] = Query(""),
    available: Optional[str] = Query(""),
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    if not ward:
        raise HTTPException(status_code=400, detail="Ward not associated.")
        
    donors = await ward_use_cases.get_top_donors_in_ward(current_user.id)
    
    if blood_group:
        donors = [d for d in donors if d["blood_group"].lower().strip() == blood_group.lower().strip()]
        
    if available == "true":
        donors = [d for d in donors if d["is_available"]]
        
    ward_data = ward.__dict__.copy()
    ward_data["id"] = ward.id
    
    # Format date fields
    for d in donors:
        if d["last_donated"]:
            d["last_donated"] = d["last_donated"].isoformat()
            
    return {
        "ward": ward_data,
        "total": len(donors),
        "available": len([d for d in donors if d["is_available"]]),
        "donors": donors
    }

@router.get("/alerts/", response_model=List[WardBloodAlertResponse])
async def get_alerts(
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_alert_repo: WardBloodAlertRepository = Depends(get_ward_alert_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    alerts = await ward_alert_repo.list_by_member(profile.id, status)
    
    results = []
    for a in alerts:
        results.append(WardBloodAlertResponse(
            id=a.id,
            blood_group=a.blood_group,
            urgency=a.urgency,
            patient_name=a.patient_name,
            patient_condition=a.patient_condition,
            hospital_name=a.hospital_name,
            hospital_phone=a.hospital_phone,
            hospital_whatsapp=a.hospital_whatsapp,
            bystander_phone=a.bystander_phone,
            hospital_latitude=a.hospital_latitude,
            hospital_longitude=a.hospital_longitude,
            hospital_message=a.hospital_message,
            status=a.status,
            ward_name=ward.local_body_name if ward else "",
            ward_number=ward.ward_number if ward else "",
            member_name=profile.full_name,
            member_phone=profile.phone,
            blood_request_id=a.blood_request_id,
            resolved_at=a.resolved_at,
            created_at=a.created_at
        ))
    return results

@router.get("/alerts/{pk}/", response_model=WardBloodAlertResponse)
async def get_alert_detail(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_alert_repo: WardBloodAlertRepository = Depends(get_ward_alert_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    a = await ward_alert_repo.get_by_id(pk)
    if not a or a.ward_member_id != profile.id:
        raise HTTPException(status_code=404, detail="Alert not found.")
        
    return WardBloodAlertResponse(
        id=a.id,
        blood_group=a.blood_group,
        urgency=a.urgency,
        patient_name=a.patient_name,
        patient_condition=a.patient_condition,
        hospital_name=a.hospital_name,
        hospital_phone=a.hospital_phone,
        hospital_whatsapp=a.hospital_whatsapp,
        bystander_phone=a.bystander_phone,
        hospital_latitude=a.hospital_latitude,
        hospital_longitude=a.hospital_longitude,
        hospital_message=a.hospital_message,
        status=a.status,
        ward_name=ward.local_body_name if ward else "",
        ward_number=ward.ward_number if ward else "",
        member_name=profile.full_name,
        member_phone=profile.phone,
        blood_request_id=a.blood_request_id,
        resolved_at=a.resolved_at,
        created_at=a.created_at
    )

@router.post("/alerts/{pk}/broadcast/")
async def broadcast_alert(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_alert_repo: WardBloodAlertRepository = Depends(get_ward_alert_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    a = await ward_alert_repo.get_by_id(pk)
    if not a or a.ward_member_id != profile.id:
        raise HTTPException(status_code=404, detail="Alert not found.")
        
    if a.status == "resolved":
        raise HTTPException(status_code=400, detail="Already resolved.")
        
    count = await ward_use_cases.broadcast_ward_alert(pk)
    return {
        "message": f"Broadcast sent to {count} ward donors.",
        "alert_id": a.id
    }

@router.get("/alerts/{pk}/top3/")
async def get_alert_top3_donors(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_alert_repo: WardBloodAlertRepository = Depends(get_ward_alert_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    a = await ward_alert_repo.get_by_id(pk)
    if not a or a.ward_member_id != profile.id:
        raise HTTPException(status_code=404, detail="Alert not found.")
        
    donors = await ward_use_cases.get_top_donors_in_ward(current_user.id)
    
    # Filter matching blood group
    matching = [d for d in donors if d["blood_group"].lower().strip() == a.blood_group.lower().strip()]
    
    # Format date fields
    for d in matching:
        if d["last_donated"]:
            d["last_donated"] = d["last_donated"].isoformat()
            
    # bystander phone fallback
    bystander = ""
    if a.blood_request_id:
        br = await db.db.blood_requests.find_one({"_id": ObjectId(a.blood_request_id)})
        if br:
            bystander = br.get("bystander_phone", "")
            
    return {
        "blood_group": a.blood_group,
        "urgency": a.urgency,
        "hospital_name": a.hospital_name,
        "hospital_phone": a.hospital_phone,
        "hospital_whatsapp": a.hospital_whatsapp,
        "patient_name": a.patient_name,
        "hospital_message": a.hospital_message,
        "bystander_phone": bystander,
        "top_donors": matching[:3]
    }

@router.post("/alerts/{pk}/resolve/")
async def resolve_alert(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_alert_repo: WardBloodAlertRepository = Depends(get_ward_alert_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    a = await ward_alert_repo.get_by_id(pk)
    if not a or a.ward_member_id != profile.id:
        raise HTTPException(status_code=404, detail="Alert not found.")
        
    a.status = "resolved"
    a.resolved_at = datetime.utcnow()
    await ward_alert_repo.update(a)
    return {"message": "Alert resolved."}

@router.get("/alerts/{pk}/notifications/", response_model=List[WardDonorNotificationResponse])
async def get_alert_notification_log(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases),
    ward_alert_repo: WardBloodAlertRepository = Depends(get_ward_alert_repository),
    ward_notif_repo: WardDonorNotificationRepository = Depends(get_ward_notif_repository)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    a = await ward_alert_repo.get_by_id(pk)
    if not a or a.ward_member_id != profile.id:
        raise HTTPException(status_code=404, detail="Alert not found.")
        
    notifs = await ward_notif_repo.list_by_alert(pk)
    
    results = []
    for n in notifs:
        # Load donor full_name
        donor_profile = await db.db.donor_profiles.find_one({"user_id": ObjectId(n.donor_id)})
        donor_name = donor_profile.get("full_name", "Donor") if donor_profile else "Donor"
        donor_phone = donor_profile.get("phone", "") if donor_profile else ""
        
        results.append(WardDonorNotificationResponse(
            id=n.id,
            donor_name=donor_name,
            donor_phone=donor_phone,
            status=n.status,
            notes=n.notes,
            contacted_at=n.contacted_at,
            created_at=n.created_at
        ))
    return results
