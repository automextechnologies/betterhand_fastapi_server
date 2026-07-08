from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from app.domain.entities.user import User, HospitalProfile, DonorProfile
from app.application.dto.auth_dto import (
    HospitalRegisterDTO, DonorRegisterDTO, LoginDTO, TokenResponse,
    ChangePasswordDTO, UpdateLocationDTO, UpdateFCMTokenDTO,
    HospitalProfileResponse, DonorProfileResponse, UserMeResponse, DonorQuestionnaireDTO
)
from app.application.use_cases.auth_use_cases import AuthUseCases
from app.dependencies.db_repos import get_auth_use_cases, get_hospital_repository, get_donor_repository
from app.dependencies.auth import get_current_user, require_hospital, require_donor
from app.domain.repositories.user_repo import HospitalProfileRepository, DonorProfileRepository
from app.infrastructure.repositories.mongo_user_repo import map_hospital_to_entity, map_donor_to_entity

router = APIRouter()

@router.post("/hospital/register/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_hospital(
    dto: HospitalRegisterDTO,
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases)
):
    try:
        user = await auth_use_cases.register_hospital(dto)
        # Generate token
        from app.core.security import create_access_token, create_refresh_token
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        return {
            "message": "Hospital registered successfully.",
            "access": access,
            "refresh": refresh,
            "role": user.role
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/donor/register/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_donor(
    dto: DonorRegisterDTO,
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases)
):
    try:
        user = await auth_use_cases.register_donor(dto)
        # Generate token
        from app.core.security import create_access_token, create_refresh_token
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        return {
            "message": "Donor registered successfully.",
            "access": access,
            "refresh": refresh,
            "role": user.role
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login/")
async def login(
    dto: LoginDTO,
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases),
    hospital_repo: HospitalProfileRepository = Depends(get_hospital_repository),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    try:
        user, tokens = await auth_use_cases.login_user(dto)
        
        # Serialize user detail
        profile_data = None
        if user.role == "hospital":
            prof = await hospital_repo.get_by_user_id(user.id)
            if prof:
                profile_data = prof.__dict__.copy()
                profile_data["id"] = prof.id
        elif user.role == "donor":
            prof = await donor_repo.get_by_user_id(user.id)
            if prof:
                profile_data = prof.__dict__.copy()
                profile_data["id"] = prof.id
                profile_data["questionnaire"] = prof.questionnaire.__dict__.copy()
                if profile_data["questionnaire"]["q_last_donation_date"]:
                    profile_data["questionnaire"]["q_last_donation_date"] = profile_data["questionnaire"]["q_last_donation_date"].isoformat()
                
        user_data = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "date_joined": user.date_joined.isoformat(),
            "profile": profile_data
        }
        return {
            "access": tokens.access,
            "refresh": tokens.refresh,
            "tokens": {
                "access": tokens.access,
                "refresh": tokens.refresh
            },
            "user": user_data
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/token/refresh/")
@router.post("/token/refresh")
async def token_refresh(data: dict):
    refresh_token = data.get("refresh")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token required.")
        
    from app.core.security import decode_access_token, create_access_token, create_refresh_token
    payload = decode_access_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
        
    user_doc = await db.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_doc or not user_doc.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or not found.")
        
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    
    return {
        "access": new_access,
        "refresh": new_refresh,
        "tokens": {
            "access": new_access,
            "refresh": new_refresh
        }
    }

@router.post("/logout/")
async def logout():
    return {"message": "Logged out successfully."}

@router.get("/me/")
async def get_me(
    current_user: User = Depends(get_current_user),
    hospital_repo: HospitalProfileRepository = Depends(get_hospital_repository),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    profile_data = None
    if current_user.role == "hospital":
        prof = await hospital_repo.get_by_user_id(current_user.id)
        if prof:
            profile_data = prof.__dict__.copy()
            profile_data["id"] = prof.id
    elif current_user.role == "donor":
        prof = await donor_repo.get_by_user_id(current_user.id)
        if prof:
            profile_data = prof.__dict__.copy()
            profile_data["id"] = prof.id
            profile_data["questionnaire"] = prof.questionnaire.__dict__.copy()
            if profile_data["questionnaire"]["q_last_donation_date"]:
                profile_data["questionnaire"]["q_last_donation_date"] = profile_data["questionnaire"]["q_last_donation_date"].isoformat()
            
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "date_joined": current_user.date_joined,
        "profile": profile_data
    }

@router.post("/change-password/")
async def change_password(
    dto: ChangePasswordDTO,
    current_user: User = Depends(get_current_user),
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases)
):
    try:
        await auth_use_cases.change_password(current_user.id, dto)
        return {"message": "Password changed successfully."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/hospital/profile/", response_model=HospitalProfileResponse)
async def get_hospital_profile(
    current_user: User = Depends(require_hospital),
    hospital_repo: HospitalProfileRepository = Depends(get_hospital_repository)
):
    profile = await hospital_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile

@router.put("/hospital/profile/", response_model=HospitalProfileResponse)
async def update_hospital_profile(
    data: dict,
    current_user: User = Depends(require_hospital),
    hospital_repo: HospitalProfileRepository = Depends(get_hospital_repository)
):
    profile = await hospital_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
        
    for k, v in data.items():
        if hasattr(profile, k) and k not in ("id", "user_id", "created_at"):
            setattr(profile, k, v)
            
    await hospital_repo.update(profile)
    return profile

@router.get("/donor/profile/", response_model=DonorProfileResponse)
async def get_donor_profile(
    current_user: User = Depends(require_donor),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    profile = await donor_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile

@router.put("/donor/profile/", response_model=DonorProfileResponse)
async def update_donor_profile(
    data: dict,
    current_user: User = Depends(require_donor),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    profile = await donor_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
        
    # questionnaire fields might be in nested format or flat. Let's support both.
    q_data = data.pop("questionnaire", None)
    for k, v in data.items():
        if hasattr(profile, k) and k not in ("id", "user_id", "created_at", "questionnaire"):
            setattr(profile, k, v)
            
    if q_data:
        for qk, qv in q_data.items():
            if hasattr(profile.questionnaire, qk):
                if qk == "q_last_donation_date" and qv:
                    from datetime import datetime
                    try:
                        profile.questionnaire.q_last_donation_date = datetime.strptime(qv.split("T")[0], "%Y-%m-%d").date()
                    except ValueError:
                        pass
                else:
                    setattr(profile.questionnaire, qk, qv)
                    
    await donor_repo.update(profile)
    return profile

# Patch and Post both for live compatibility
@router.patch("/location/")
@router.post("/location/")
async def update_location(
    dto: UpdateLocationDTO,
    current_user: User = Depends(get_current_user),
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases)
):
    try:
        await auth_use_cases.update_location(current_user.id, current_user.role, dto)
        return {
            "message": "Location updated.",
            "latitude": str(round(dto.latitude, 6)),
            "longitude": str(round(dto.longitude, 6))
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/fcm-token/")
@router.post("/fcm-token/")
async def update_fcm_token(
    dto: UpdateFCMTokenDTO,
    current_user: User = Depends(get_current_user),
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases)
):
    await auth_use_cases.update_fcm_token(current_user.id, dto.fcm_token)
    return {"message": "FCM token updated."}

@router.get("/donors/search/")
async def search_donors(
    blood_group: str = Query(...),
    radius_km: float = Query(50.0),
    current_user: User = Depends(require_hospital),
    hospital_repo: HospitalProfileRepository = Depends(get_hospital_repository),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    hospital = await hospital_repo.get_by_user_id(current_user.id)
    has_location = hospital and hospital.latitude is not None and hospital.longitude is not None
    
    if radius_km > 0 and not has_location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hospital location not set.")
        
    from app.core.config import settings
    from datetime import datetime, timedelta
    cooldown_cutoff = (datetime.utcnow() - timedelta(days=settings.DONOR_COOLDOWN_DAYS)).isoformat()
    
    lon = hospital.longitude if has_location else 0.0
    lat = hospital.latitude if has_location else 0.0
    
    donors = await donor_repo.search_donors(
        blood_group=blood_group,
        longitude=lon,
        latitude=lat,
        radius_km=radius_km,
        cooldown_cutoff_date=cooldown_cutoff
    )
    
    results = []
    from app.domain.services.location import haversine_distance
    for d in donors:
        dist = 0.0
        if has_location and d.latitude is not None and d.longitude is not None:
            dist = round(haversine_distance(hospital.latitude, hospital.longitude, d.latitude, d.longitude), 2)
        results.append({
            "id": d.id,
            "full_name": d.full_name,
            "blood_group": d.blood_group,
            "phone": d.phone,
            "whatsapp_number": d.whatsapp_number or d.phone,
            "state": d.state,
            "district": d.district,
            "local_body_name": d.local_body_name,
            "ward_number": d.ward_number,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "distance_km": dist
        })
        
    # Sort by distance (donors with location coordinates first)
    results.sort(key=lambda x: x["distance_km"])
    
    return {
        "count": len(results),
        "blood_group": blood_group,
        "radius_km": radius_km,
        "results": results
    }

@router.patch("/donor/availability/")
@router.post("/donor/availability/")
async def toggle_availability(
    current_user: User = Depends(require_donor),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    profile = await donor_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
        
    profile.is_available = not profile.is_available
    await donor_repo.update(profile)
    
    return {
        "message": f"Availability set to {'available' if profile.is_available else 'unavailable'}.",
        "is_available": profile.is_available
    }

@router.get("/colleges/")
async def get_colleges(
    district: Optional[str] = Query(""),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    results = await donor_repo.get_distinct_colleges(district)
    return {"colleges": results}

@router.post("/donor/questionnaire/")
async def submit_questionnaire(
    data: dict,
    current_user: User = Depends(require_donor),
    donor_repo: DonorProfileRepository = Depends(get_donor_repository)
):
    profile = await donor_repo.get_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
        
    for f in ["q_weight_ok", "q_age_ok", "q_no_illness", "q_no_medication",
              "q_no_recent_donation", "q_no_tattoo", "q_no_alcohol", "consent_given"]:
        setattr(profile.questionnaire, f, bool(data.get(f, False)))
        
    profile.questionnaire.q_chronic_conditions = data.get("q_chronic_conditions", "")
    
    ld_date = data.get("q_last_donation_date")
    if ld_date:
        from datetime import datetime
        try:
            profile.questionnaire.q_last_donation_date = datetime.strptime(ld_date.split("T")[0], "%Y-%m-%d").date()
        except ValueError:
            pass
            
    profile.questionnaire.questionnaire_completed = True
    if profile.questionnaire.consent_given:
        profile.questionnaire.consent_date = datetime.utcnow()
        
    await donor_repo.update(profile)
    
    return {
        "message": "Questionnaire saved. You now have priority status!",
        "questionnaire_completed": True,
        "priority_score": profile.priority_score
    }

@router.post("/test-notification/")
async def test_notification(
    current_user: User = Depends(require_hospital),
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases)
):
    return await auth_use_cases.send_test_notification()
