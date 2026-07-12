from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from datetime import datetime
from app.domain.entities.user import User
from app.domain.entities.ward import WardMember, Ward, WardBloodAlert

from app.application.dto.ward_dto import (
    WardMemberRegisterDTO, WardMemberProfileResponse, WardResponse,
    WardBloodAlertResponse, WardTopDonorDTO, WardDonorNotificationResponse,
    BroadcastAlertDTO
)
from app.application.use_cases.ward_use_cases import WardUseCases
from app.dependencies.db_repos import get_ward_use_cases, get_ward_repository, get_ward_member_repository, get_ward_alert_repository, get_ward_notif_repository
from app.dependencies.auth import get_current_user, require_ward_member
from app.domain.repositories.ward_repo import WardRepository, WardMemberRepository, WardBloodAlertRepository, WardDonorNotificationRepository
from app.application.use_cases.auth_use_cases import AuthUseCases
from app.dependencies.db_repos import get_auth_use_cases

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
                "phone": user.phone,
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
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    phone = data.get("phone", "").strip()
    password = data.get("password", "")
    fcm_token = data.get("fcm_token", "").strip()
    if not phone or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number and password required.")
        
    try:
        res = await ward_use_cases.login_ward_member(phone, password, fcm_token)
        # We need both "user" and "member" to be returned
        user_block = res["user"]
        profile_block = user_block["profile"]
        member_block = {
            "id": profile_block["id"],
            "full_name": profile_block["full_name"],
            "phone": profile_block["phone"],
            "is_verified": profile_block["is_verified"],
            "ward": profile_block["ward"]
        }
        res["member"] = member_block
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/logout/")
async def logout():
    return {"message": "Logged out."}

@router.get("/profile/", response_model=WardMemberProfileResponse)
async def get_profile(
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    try:
        return await ward_use_cases.get_ward_member_profile_response(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
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
    current_user: User = Depends(get_current_user),
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases)
):
    token = data.get("fcm_token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="fcm_token required.")
    try:
        await auth_use_cases.update_fcm_token(current_user.id, token)
        return {"message": "FCM token updated."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/wards/", response_model=List[WardResponse])
async def list_wards(
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    local_body_name: Optional[str] = Query(None),
    local_body_type: Optional[str] = Query(None),
    ward_number: Optional[str] = Query(None),
    has_member: Optional[str] = Query(None),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    filters = {}
    if state: filters["state"] = state
    if district: filters["district"] = district
    if local_body_name: filters["local_body_name"] = local_body_name
    if local_body_type: filters["local_body_type"] = local_body_type
    if ward_number: filters["ward_number"] = ward_number
    
    members_verified = has_member == "true"
    return await ward_use_cases.list_wards_formatted(filters, has_member=members_verified)

@router.get("/dashboard/")
async def get_dashboard(
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    if not ward:
        raise HTTPException(status_code=400, detail="Ward not associated.")
    return await ward_use_cases.get_ward_dashboard_stats(profile.id)

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
    dto: Optional[BroadcastAlertDTO] = None,
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
        
    donor_ids = dto.donor_ids if dto else None
    count = await ward_use_cases.broadcast_ward_alert(pk, donor_ids=donor_ids)
    return {
        "message": f"Broadcast sent to {count} ward donors.",
        "alert_id": a.id
    }

@router.get("/alerts/{pk}/top3/")
async def get_alert_top3_donors(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    try:
        return await ward_use_cases.get_alert_details_formatted(pk, profile.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/alerts/{pk}/resolve/")
async def resolve_alert(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    try:
        await ward_use_cases.resolve_alert(pk, profile.id)
        return {"message": "Alert resolved."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/alerts/{pk}/notifications/", response_model=List[WardDonorNotificationResponse])
async def get_alert_notification_log(
    pk: str,
    current_user: User = Depends(require_ward_member),
    ward_use_cases: WardUseCases = Depends(get_ward_use_cases)
):
    profile, ward = await ward_use_cases.get_ward_member_profile(current_user.id)
    try:
        data = await ward_use_cases.get_alert_notifications_formatted(pk, profile.id)
        return [WardDonorNotificationResponse(**x) for x in data]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
