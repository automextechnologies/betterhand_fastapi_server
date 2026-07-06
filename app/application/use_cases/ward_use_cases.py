from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Tuple, Any
from bson import ObjectId
from app.core.config import settings
from app.core.security import hash_password
from app.infrastructure.database.mongodb import db
from app.domain.entities.user import User
from app.domain.entities.ward import Ward, WardMember, WardBloodAlert, WardDonorNotification
from app.domain.entities.donation import DonationResponse
from app.domain.repositories.user_repo import UserRepository, DonorProfileRepository
from app.domain.repositories.ward_repo import WardRepository, WardMemberRepository, WardBloodAlertRepository, WardDonorNotificationRepository
from app.domain.repositories.donation_repo import (
    BloodRequestRepository, DonationResponseRepository, DonationRecordRepository,
    DonorRatingRepository, DonorBadgeRepository
)
from app.application.dto.ward_dto import WardMemberRegisterDTO
from app.infrastructure.external_services.firebase_fcm import send_push_notification
from app.domain.services.location import haversine_distance

class WardUseCases:
    def __init__(
        self,
        user_repo: UserRepository,
        donor_repo: DonorProfileRepository,
        ward_repo: WardRepository,
        ward_member_repo: WardMemberRepository,
        ward_alert_repo: WardBloodAlertRepository,
        ward_notif_repo: WardDonorNotificationRepository,
        request_repo: BloodRequestRepository,
        response_repo: DonationResponseRepository,
        record_repo: DonationRecordRepository,
        rating_repo: DonorRatingRepository,
        badge_repo: DonorBadgeRepository,
        ws_broadcast_func: Optional[Any] = None
    ):
        self.user_repo = user_repo
        self.donor_repo = donor_repo
        self.ward_repo = ward_repo
        self.ward_member_repo = ward_member_repo
        self.ward_alert_repo = ward_alert_repo
        self.ward_notif_repo = ward_notif_repo
        self.request_repo = request_repo
        self.response_repo = response_repo
        self.record_repo = record_repo
        self.rating_repo = rating_repo
        self.badge_repo = badge_repo
        self.ws_broadcast = ws_broadcast_func or (lambda g, ev, p: None)

    async def register_ward_member(self, dto: WardMemberRegisterDTO) -> User:
        # Check if email is already taken
        existing_user = await self.user_repo.get_by_email(dto.email)
        if existing_user:
            raise ValueError("Email already registered.")
            
        # Resolve ward
        if dto.ward_id:
            ward = await self.ward_repo.get_by_id(dto.ward_id)
            if not ward:
                raise ValueError("Ward not found.")
        else:
            if not (dto.state and dto.district and dto.ward_number):
                raise ValueError("Provide either ward_id or (state + district + ward_number).")
                
            ward, _ = await self.ward_repo.get_or_create(
                ward_number=dto.ward_number,
                local_body_name=dto.local_body_name or dto.district,
                state=dto.state,
                defaults={
                    "district": dto.district,
                    "local_body_type": dto.local_body_type or "gram_panchayat"
                }
            )
            
        # Create User entity
        user = User(
            email=dto.email,
            hashed_password=hash_password(dto.password),
            role="ward_member",
            is_active=True
        )
        created_user = await self.user_repo.create(user)
        
        # Create WardMember Profile
        member = WardMember(
            user_id=created_user.id,
            ward_id=ward.id,
            full_name=dto.full_name,
            phone=dto.phone,
            designation=dto.designation or ""
        )
        await self.ward_member_repo.create(member)
        return created_user

    async def get_ward_member_profile(self, user_id: str) -> Tuple[WardMember, Optional[Ward]]:
        member = await self.ward_member_repo.get_by_user_id(user_id)
        if not member:
            raise ValueError("Ward member profile not found.")
        ward = await self.ward_repo.get_by_id(member.ward_id)
        return member, ward

    async def list_ward_alerts(self, user_id: str, status: Optional[str] = None) -> List[WardBloodAlert]:
        member = await self.ward_member_repo.get_by_user_id(user_id)
        if not member:
            raise ValueError("Ward member profile not found.")
        return await self.ward_alert_repo.list_by_member(member.id, status)

    async def get_top_donors_in_ward(self, user_id: str) -> List[dict]:
        member = await self.ward_member_repo.get_by_user_id(user_id)
        if not member:
            raise ValueError("Ward member profile not found.")
            
        ward = await self.ward_repo.get_by_id(member.ward_id)
        if not ward:
            raise ValueError("Ward not found.")
            
        # strict ward match on location details (state, local body name, ward number)
        # Find all donor profiles matching these fields
        # Note: we match case insensitively where possible or directly in MongoDB
        # Let's write an aggregation query or query donor profiles
        query = {
            "state": {"$regex": f"^{ward.state}$", "$options": "i"},
            "local_body_name": {"$regex": f"^{ward.local_body_name}$", "$options": "i"},
            "ward_number": str(ward.ward_number)
        }
        
        docs = await db.db.donor_profiles.find(query).to_list(length=1000)
        
        top_donors = []
        cooldown_cutoff = datetime.utcnow() - timedelta(days=settings.DONOR_COOLDOWN_DAYS)
        
        for d in docs:
            donor_id = str(d["_id"])
            user_id_str = str(d["user_id"])
            
            # check last donation and cooldown
            last_record = await self.record_repo.get_last_for_donor(user_id_str)
            last_donated = last_record.donated_at.date() if last_record else None
            on_cooldown = last_record.cooldown_until > datetime.utcnow() if last_record else False
            
            # average rating
            avg_rating = await self.rating_repo.get_avg_rating_for_donor(user_id_str)
            
            # total donations count
            donation_count = await self.record_repo.count_by_donor(user_id_str)
            
            # badges
            badges_list = await self.badge_repo.list_by_donor(user_id_str)
            badges = [b.badge for b in badges_list]
            
            dist = 0.0
            if ward.latitude and ward.longitude and d.get("location"):
                coords = d["location"]["coordinates"]
                dist = haversine_distance(ward.latitude, ward.longitude, coords[1], coords[0])
                
            whatsapp_link = None
            if d.get("whatsapp_number"):
                whatsapp_link = f"https://wa.me/{d['whatsapp_number']}"
            elif d.get("phone"):
                whatsapp_link = f"https://wa.me/{d['phone']}"
                
            top_donors.append({
                "donor_id": user_id_str,
                "full_name": d.get("full_name", ""),
                "phone": d.get("phone", ""),
                "blood_group": d.get("blood_group", ""),
                "district": d.get("district", ""),
                "local_body_name": d.get("local_body_name", ""),
                "ward_number": d.get("ward_number", ""),
                "distance_km": round(dist, 2),
                "is_available": d.get("is_available", True),
                "last_donated": last_donated,
                "on_cooldown": on_cooldown,
                "avg_rating": round(avg_rating, 2) if avg_rating else None,
                "donation_count": donation_count,
                "badges": badges,
                "whatsapp_link": whatsapp_link
            })
            
        # Sort: priority logic
        top_donors.sort(key=lambda x: (
            x["on_cooldown"], # available first
            -x["donation_count"], # highest donations count first
            -(x["avg_rating"] or 0.0)
        ))
        
        return top_donors

    async def broadcast_ward_alert(self, alert_id: str) -> int:
        alert = await self.ward_alert_repo.get_by_id(alert_id)
        if not alert:
            return 0
            
        wm = await self.ward_member_repo.get_by_id(alert.ward_member_id)
        if not wm:
            return 0
            
        ward = await self.ward_repo.get_by_id(wm.ward_id)
        if not ward:
            return 0
            
        br = None
        if alert.blood_request_id:
            br = await self.request_repo.get_by_id(alert.blood_request_id)
            if br and br.status not in ("pending", "active"):
                br.status = "active"
                await self.request_repo.update(br)
                
        cooldown_cutoff = datetime.utcnow() - timedelta(days=settings.DONOR_COOLDOWN_DAYS)
        
        # STRICT WARD MATCH — same ward only, matching blood group
        query = {
            "blood_group": alert.blood_group,
            "is_available": True,
            "ward_number": str(ward.ward_number),
            "local_body_name": {"$regex": f"^{ward.local_body_name}$", "$options": "i"},
            "state": {"$regex": f"^{ward.state}$", "$options": "i"}
        }
        
        docs = await db.db.donor_profiles.find(query).to_list(length=1000)
        
        n = 0
        for d in docs:
            donor_user_id = str(d["user_id"])
            
            # Check cooldown
            last_record = await self.record_repo.get_last_for_donor(donor_user_id)
            if last_record and last_record.donated_at >= cooldown_cutoff:
                continue # on cooldown, skip
                
            # Create WardDonorNotification
            await self.ward_notif_repo.get_or_create(
                alert_id=alert.id,
                donor_id=donor_user_id,
                defaults={"status": "pending", "contacted_at": datetime.utcnow()}
            )
            
            if br:
                resp, created = await self.response_repo.get_or_create(
                    request_id=br.id,
                    donor_id=donor_user_id,
                    defaults={"status": "pending", "notification_sent_at": datetime.utcnow()}
                )
                if created:
                    # WebSocket push to donor
                    self.ws_broadcast(f"donor_{donor_user_id}", "new_request", {
                        "response_id": resp.id,
                        "request_id": br.id,
                        "blood_group": alert.blood_group,
                        "urgency": alert.urgency,
                        "hospital_name": alert.hospital_name,
                        "units_needed": br.units_needed,
                        "patient_name": alert.patient_name,
                        "via_ward": True,
                        "ward_member_name": wm.full_name
                    })
                    
            donor_user = await self.user_repo.get_by_id(donor_id=donor_user_id)
            if donor_user and donor_user.fcm_token:
                send_push_notification(
                    fcm_token=donor_user.fcm_token,
                    title=f"🩸 Ward Alert — {alert.blood_group}",
                    body=f"{wm.full_name} requests {alert.blood_group} for {alert.hospital_name}.",
                    data={"type": "ward_blood_alert", "alert_id": str(alert.id)}
                )
            n += 1
            
        alert.status = "notified"
        await self.ward_alert_repo.update(alert)
        return n

