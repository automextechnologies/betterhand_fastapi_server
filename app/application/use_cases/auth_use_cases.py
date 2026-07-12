from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.domain.entities.user import User, HospitalProfile, DonorProfile, DonorQuestionnaire
from app.domain.repositories.user_repo import UserRepository, HospitalProfileRepository, DonorProfileRepository
from app.application.dto.auth_dto import (
    HospitalRegisterDTO, DonorRegisterDTO, LoginDTO, TokenResponse,
    ChangePasswordDTO, UpdateLocationDTO
)

class AuthUseCases:
    def __init__(
        self,
        user_repo: UserRepository,
        hospital_repo: HospitalProfileRepository,
        donor_repo: DonorProfileRepository
    ):
        self.user_repo = user_repo
        self.hospital_repo = hospital_repo
        self.donor_repo = donor_repo

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
