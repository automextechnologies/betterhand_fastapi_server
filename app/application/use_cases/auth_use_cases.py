from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.domain.entities.user import User, HospitalProfile, DonorProfile, DonorQuestionnaire
from app.domain.repositories.user_repo import UserRepository, HospitalProfileRepository, DonorProfileRepository
from app.domain.repositories.donation_repo import BloodRequestRepository, DonationResponseRepository
from app.domain.repositories.ward_repo import WardRepository, WardMemberRepository
from app.application.dto.auth_dto import (
    HospitalRegisterDTO, DonorRegisterDTO, LoginDTO, TokenResponse,
    ChangePasswordDTO, UpdateLocationDTO
)

class AuthUseCases:
    def __init__(
        self,
        user_repo: UserRepository,
        hospital_repo: HospitalProfileRepository,
        donor_repo: DonorProfileRepository,
        request_repo: Optional[BloodRequestRepository] = None,
        response_repo: Optional[DonationResponseRepository] = None,
        ward_repo: Optional[WardRepository] = None,
        ward_member_repo: Optional[WardMemberRepository] = None
    ):
        self.user_repo = user_repo
        self.hospital_repo = hospital_repo
        self.donor_repo = donor_repo
        self.request_repo = request_repo
        self.response_repo = response_repo
        self.ward_repo = ward_repo
        self.ward_member_repo = ward_member_repo

    async def register_hospital(self, dto: HospitalRegisterDTO) -> User:
        # Check if email is already taken
        existing_user = await self.user_repo.get_by_email(dto.email)
        if existing_user:
            raise ValueError("Email already registered.")
            
        # Create User entity
        user = User(
            email=dto.email,
            hashed_password=hash_password(dto.password),
            role="hospital",
            is_active=True,
            fcm_token=dto.fcm_token
        )
        created_user = await self.user_repo.create(user)
        
        # Create HospitalProfile entity
        profile = HospitalProfile(
            user_id=created_user.id,
            name=dto.name,
            registration_number=dto.registration_number,
            phone=dto.phone,
            address=dto.address,
            city=dto.city,
            state=dto.state,
            district=dto.district,
            local_body_type=dto.local_body_type,
            local_body_name=dto.local_body_name,
            ward_number=dto.ward_number,
            pincode=dto.pincode,
            whatsapp_number=dto.whatsapp_number
        )
        await self.hospital_repo.create(profile)
        return created_user

    async def register_donor(self, dto: DonorRegisterDTO) -> User:
        # Check if phone is already taken
        existing_user = await self.user_repo.get_by_phone(dto.phone)
        if existing_user:
            raise ValueError("Phone number already registered.")
            
        # Create User entity
        user = User(
            phone=dto.phone,
            hashed_password=hash_password(dto.password),
            role="donor",
            is_active=True,
            fcm_token=dto.fcm_token
        )
        created_user = await self.user_repo.create(user)
        
        # Create DonorProfile entity
        profile = DonorProfile(
            user_id=created_user.id,
            full_name=dto.full_name,
            blood_group=dto.blood_group,
            phone=dto.phone,
            age=dto.age,
            gender=dto.gender,
            state=dto.state,
            district=dto.district,
            local_body_type=dto.local_body_type,
            local_body_name=dto.local_body_name,
            ward_number=dto.ward_number,
            city=dto.city,
            pincode=dto.pincode,
            is_student=dto.is_student,
            college_name=dto.college_name,
            college_district=dto.college_district,
            questionnaire=DonorQuestionnaire()
        )
        
        # Check ward member by mapping district, local body type, local body name, and ward number
        if self.ward_repo and self.ward_member_repo and profile.district and profile.local_body_type and profile.local_body_name and profile.ward_number:
            wards = await self.ward_repo.search_wards({
                "district": profile.district,
                "local_body_type": profile.local_body_type,
                "local_body_name": profile.local_body_name,
                "ward_number": profile.ward_number
            })
            if wards:
                members = await self.ward_member_repo.get_verified_members_by_ward(wards[0].id)
                if not members:
                    # fallback to unverified members if no verified ones are registered
                    members = await self.ward_member_repo.get_members_by_ward(wards[0].id)
                if members:
                    profile.ward_member_id = members[0].id

        await self.donor_repo.create(profile)
        return created_user

    async def login_user(self, dto: LoginDTO) -> Tuple[User, TokenResponse]:
        if dto.email:
            user = await self.user_repo.get_by_email(dto.email)
            if not user or user.role != "hospital":
                raise ValueError("Invalid email or password.")
        elif dto.phone:
            user = await self.user_repo.get_by_phone(dto.phone)
            if not user or user.role not in ("donor", "ward_member"):
                raise ValueError("Invalid phone number or password.")
        else:
            raise ValueError("Email or phone number required.")
            
        if not verify_password(dto.password, user.hashed_password):
            if dto.email:
                raise ValueError("Invalid email or password.")
            else:
                raise ValueError("Invalid phone number or password.")
            
        if not user.is_active:
            raise ValueError("Account is disabled.")
            
        # Update FCM token if provided
        if dto.fcm_token:
            user.fcm_token = dto.fcm_token
            await self.user_repo.update(user)
            
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        
        return user, TokenResponse(access=access_token, refresh=refresh_token)

    async def change_password(self, user_id: str, dto: ChangePasswordDTO) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found.")
            
        if not verify_password(dto.old_password, user.hashed_password):
            raise ValueError("Old password is incorrect.")
            
        user.hashed_password = hash_password(dto.new_password)
        await self.user_repo.update(user)

    async def update_location(self, user_id: str, role: str, dto: UpdateLocationDTO) -> None:
        if role == "donor":
            profile = await self.donor_repo.get_by_user_id(user_id)
            if not profile:
                raise ValueError("Donor profile not found.")
            profile.latitude = dto.latitude
            profile.longitude = dto.longitude
            await self.donor_repo.update(profile)
        elif role == "hospital":
            profile = await self.hospital_repo.get_by_user_id(user_id)
            if not profile:
                raise ValueError("Hospital profile not found.")
            profile.latitude = dto.latitude
            profile.longitude = dto.longitude
            await self.hospital_repo.update(profile)
            
            # Synchronize active blood requests and recalculate response distances
            if self.request_repo and self.response_repo:
                from app.domain.services.location import haversine_distance
                requests = await self.request_repo.list_by_hospital(user_id)
                for br in requests:
                    if br.status in ("pending", "active", "confirmed"):
                        br.hospital_latitude = dto.latitude
                        br.hospital_longitude = dto.longitude
                        await self.request_repo.update(br)
                        
                        responses = await self.response_repo.list_by_request(br.id)
                        for resp in responses:
                            lat = resp.donor_latitude
                            lng = resp.donor_longitude
                            if lat is None or lng is None:
                                dp = await self.donor_repo.get_by_user_id(resp.donor_id)
                                if dp:
                                    lat = dp.latitude
                                    lng = dp.longitude
                            
                            if lat is not None and lng is not None:
                                try:
                                    resp.distance_km = round(haversine_distance(
                                        dto.latitude, dto.longitude,
                                        lat, lng
                                    ), 2)
                                    await self.response_repo.update(resp)
                                except Exception:
                                    pass
        else:
            raise ValueError("Unsupported role for location updates.")

    async def update_fcm_token(self, user_id: str, fcm_token: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found.")
        user.fcm_token = fcm_token
        await self.user_repo.update(user)

    async def send_test_notification(self) -> dict:
        donors = await self.user_repo.get_by_role("donor")
        tokens = [d.fcm_token for d in donors if d.fcm_token]
        if not tokens:
            return {"sent": 0, "message": "No active donor FCM tokens found."}
            
        from app.infrastructure.external_services.firebase_fcm import send_push_to_many
        send_push_to_many(
            fcm_tokens=tokens,
            title="Test Notification",
            body="This is a test notification from the BetterHand Hospital command."
        )
        return {"sent": len(tokens), "message": f"Test notification broadcasted to {len(tokens)} donor(s)."}

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        from jose import jwt
        from app.core.config import settings
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid refresh token payload.")
                
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError("User not found.")
                
            access_token = create_access_token(user.id)
            new_refresh_token = create_refresh_token(user.id)
            return TokenResponse(access=access_token, refresh=new_refresh_token)
        except Exception:
            raise ValueError("Invalid or expired refresh token.")
