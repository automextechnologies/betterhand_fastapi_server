from typing import List
from app.domain.repositories.user_repo import UserRepository, HospitalProfileRepository, DonorProfileRepository
from app.domain.repositories.ward_repo import WardMemberRepository, WardRepository
from app.infrastructure.external_services.firebase_fcm import send_push_to_many

class AdminUseCases:
    def __init__(
        self,
        user_repo: UserRepository,
        hospital_repo: HospitalProfileRepository,
        donor_repo: DonorProfileRepository,
        ward_member_repo: WardMemberRepository,
        ward_repo: WardRepository
    ):
        self.user_repo = user_repo
        self.hospital_repo = hospital_repo
        self.donor_repo = donor_repo
        self.ward_member_repo = ward_member_repo
        self.ward_repo = ward_repo

    async def get_admin_dashboard_data(self) -> dict:
        users = await self.user_repo.list_all()
        hospitals = await self.hospital_repo.list_all()
        donors = await self.donor_repo.list_all()
        ward_members = await self.ward_member_repo.list_all()
        wards = await self.ward_repo.list_all()

        return {
            "users": users,
            "hospitals": hospitals,
            "donors": donors,
            "ward_members": ward_members,
            "wards": wards
        }

    async def broadcast_admin_notification(self, title: str, body: str) -> dict:
        users = await self.user_repo.get_users_with_fcm_token()
        tokens = [u.fcm_token for u in users if u.fcm_token]
        if not tokens:
            return {"status": "success", "message": "No users with FCM tokens found."}
            
        send_push_to_many(
            fcm_tokens=tokens,
            title=title,
            body=body
        )
        return {"status": "success", "message": f"Broadcast notification sent successfully to {len(tokens)} user(s)."}
