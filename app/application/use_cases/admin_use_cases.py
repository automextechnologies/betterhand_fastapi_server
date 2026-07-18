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

    async def verify_ward_member(self, member_id: str) -> dict:
        """
        Mark a ward member as verified by an administrator.

        This is a privileged action performed exclusively from the admin dashboard.
        The ward member's `is_verified` flag is flipped to True and persisted.
        A push notification is sent to the ward member's device if an FCM token
        exists, so they are immediately informed without needing to refresh.

        Args:
            member_id: The WardMember document ID (not the User ID).

        Returns:
            A dict confirming the action with the member's name.

        Raises:
            ValueError: If the member is not found.
        """
        member = await self.ward_member_repo.get_by_id(member_id)
        if not member:
            raise ValueError(f"Ward member with id '{member_id}' not found.")

        if member.is_verified:
            return {
                "status": "already_verified",
                "message": f"{member.full_name} is already verified.",
                "member_id": member_id
            }

        member.is_verified = True
        await self.ward_member_repo.update(member)

        # Notify the ward member via push if they have an FCM token
        if member.user_id:
            user = await self.user_repo.get_by_id(member.user_id)
            if user and user.fcm_token:
                try:
                    send_push_to_many(
                        fcm_tokens=[user.fcm_token],
                        title="✅ Account Verified",
                        body="Your ward member account has been verified by the administrator. You can now manage donors and broadcast alerts."
                    )
                except Exception:
                    pass  # Notification failure must not block the verification action

        return {
            "status": "success",
            "message": f"{member.full_name} has been verified successfully.",
            "member_id": member_id,
            "full_name": member.full_name
        }
