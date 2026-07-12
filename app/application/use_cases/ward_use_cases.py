from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Tuple, Any
from bson import ObjectId
from app.core.config import settings
from app.core.security import hash_password
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
        # Check if phone is already taken
        existing_user = await self.user_repo.get_by_phone(dto.phone)
        if existing_user:
            raise ValueError("Phone number already registered.")
            
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
            phone=dto.phone,
            hashed_password=hash_password(dto.password),
            role="ward_member",
            is_active=True,
            fcm_token=dto.fcm_token
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
        donors = await self.donor_repo.list_by_ward(
            state=ward.state,
            local_body_name=ward.local_body_name,
            ward_number=ward.ward_number
        )
        
        top_donors = []
        cooldown_cutoff = datetime.utcnow() - timedelta(days=settings.DONOR_COOLDOWN_DAYS)
        
        for d in donors:
            donor_id = d.id
            user_id_str = d.user_id
            
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
            if ward.latitude and ward.longitude and d.latitude and d.longitude:
                dist = haversine_distance(ward.latitude, ward.longitude, d.latitude, d.longitude)
                
            whatsapp_link = None
            if d.whatsapp_number:
                whatsapp_link = f"https://wa.me/{d.whatsapp_number}"
            elif d.phone:
                whatsapp_link = f"https://wa.me/{d.phone}"
                
            top_donors.append({
                "donor_id": user_id_str,
                "full_name": d.full_name or "",
                "phone": d.phone or "",
                "blood_group": d.blood_group or "",
                "district": d.district or "",
                "local_body_name": d.local_body_name or "",
                "ward_number": d.ward_number or "",
                "distance_km": round(dist, 2),
                "is_available": d.is_available,
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

    async def broadcast_ward_alert(self, alert_id: str, donor_ids: Optional[List[str]] = None) -> int:
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
        donors = await self.donor_repo.list_by_ward(
            state=ward.state,
            local_body_name=ward.local_body_name,
            ward_number=ward.ward_number,
            is_available=True,
            user_ids=donor_ids,
            blood_group=alert.blood_group
        )
        
        n = 0
        for d in donors:
            donor_user_id = d.user_id
            
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
                    
            donor_user = await self.user_repo.get_by_id(user_id=donor_user_id)
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

    async def get_ward_members(self, ward_id: str) -> List[WardMember]:
        return await self.ward_member_repo.get_members_by_ward(ward_id)

    async def get_ward_dashboard_stats(self, ward_member_id: str) -> dict:
        profile = await self.ward_member_repo.get_by_id(ward_member_id)
        if not profile:
            raise ValueError("Ward member profile not found.")
            
        ward = await self.ward_repo.get_by_id(profile.ward_id)
        if not ward:
            raise ValueError("Ward not associated.")
            
        alerts = await self.ward_alert_repo.list_by_member(profile.id)
        
        total_donors = await self.donor_repo.count_by_ward(
            state=ward.state,
            local_body_name=ward.local_body_name,
            ward_number=ward.ward_number
        )
        avail_donors = await self.donor_repo.count_by_ward(
            state=ward.state,
            local_body_name=ward.local_body_name,
            ward_number=ward.ward_number,
            is_available=True
        )
        
        recent_alerts_data = []
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
        ward_data = {k: v for k, v in ward_data.items() if not k.startswith("_")}
        
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

    async def login_ward_member(self, phone: str, password: str, fcm_token: Optional[str] = None) -> dict:
        user = await self.user_repo.get_by_phone(phone)
        if not user:
            raise ValueError("Invalid credentials.")
            
        from app.core.security import verify_password, create_access_token, create_refresh_token
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials.")
            
        if user.role != "ward_member":
            raise ValueError("Not a ward member account.")
            
        if fcm_token:
            user.fcm_token = fcm_token
            await self.user_repo.update(user)
            
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        
        profile = await self.ward_member_repo.get_by_user_id(user.id)
        ward = await self.ward_repo.get_by_id(profile.ward_id) if profile else None
        
        ward_data = None
        if ward:
            ward_data = {
                "id": ward.id,
                "ward_number": ward.ward_number,
                "local_body_name": ward.local_body_name,
                "district": ward.district,
                "state": ward.state
            }
            
        return {
            "access": access,
            "refresh": refresh,
            "role": user.role,
            "user": {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "profile": {
                    "id": profile.id if profile else None,
                    "full_name": profile.full_name if profile else None,
                    "phone": profile.phone if profile else None,
                    "designation": profile.designation if profile else None,
                    "is_verified": profile.is_verified if profile else False,
                    "ward": ward_data
                }
            }
        }

    async def get_ward_member_profile_response(self, user_id: str) -> dict:
        profile = await self.ward_member_repo.get_by_user_id(user_id)
        if not profile:
            raise ValueError("Ward member profile not found.")
            
        ward = await self.ward_repo.get_by_id(profile.ward_id) if profile.ward_id else None
        
        members_data = []
        if ward:
            members = await self.ward_member_repo.get_members_by_ward(ward.id)
            for m in members:
                members_data.append({
                    "id": m.id,
                    "full_name": m.full_name,
                    "phone": m.phone,
                    "designation": m.designation,
                    "is_verified": m.is_verified
                })
                
        ward_resp = None
        if ward:
            ward_resp = {
                "id": ward.id,
                "ward_number": ward.ward_number,
                "local_body_name": ward.local_body_name,
                "local_body_type": ward.local_body_type,
                "district": ward.district,
                "state": ward.state,
                "latitude": ward.latitude,
                "longitude": ward.longitude,
                "members": members_data
            }
            
        return {
            "id": profile.id,
            "full_name": profile.full_name,
            "phone": profile.phone,
            "designation": profile.designation,
            "is_verified": profile.is_verified,
            "ward": ward_resp
        }

    async def list_wards_formatted(self, filters: dict, has_member: bool = False) -> List[dict]:
        wards = await self.ward_repo.search_wards(filters, has_member=has_member)
        results = []
        for w in wards:
            members = await self.ward_member_repo.get_members_by_ward(w.id)
            members_data = []
            for m in members:
                members_data.append({
                    "id": m.id,
                    "full_name": m.full_name,
                    "phone": m.phone,
                    "designation": m.designation,
                    "is_verified": m.is_verified
                })
            results.append({
                "id": w.id,
                "ward_number": w.ward_number,
                "local_body_name": w.local_body_name,
                "local_body_type": w.local_body_type,
                "district": w.district,
                "state": w.state,
                "latitude": w.latitude,
                "longitude": w.longitude,
                "members": members_data
            })
        return results

    async def get_alert_details_formatted(self, alert_id: str, ward_member_id: str) -> dict:
        a = await self.ward_alert_repo.get_by_id(alert_id)
        if not a or a.ward_member_id != ward_member_id:
            raise ValueError("Alert not found.")
            
        donors = await self.get_top_donors_in_ward(ward_member_id)
        matching = [d for d in donors if d["blood_group"].lower().strip() == a.blood_group.lower().strip()]
        
        for d in matching:
            if d["last_donated"]:
                d["last_donated"] = d["last_donated"].isoformat()
                
        bystander = ""
        if a.blood_request_id:
            br = await self.request_repo.get_by_id(a.blood_request_id)
            if br:
                bystander = br.bystander_phone or ""
                
        return {
            "blood_group": a.blood_group,
            "urgency": a.urgency,
            "hospital_name": a.hospital_name,
            "hospital_phone": a.hospital_phone,
            "hospital_whatsapp": a.hospital_whatsapp,
            "patient_name": a.patient_name,
            "hospital_message": a.hospital_message,
            "bystander_phone": bystander,
            "top_donors": matching
        }

    async def resolve_alert(self, alert_id: str, ward_member_id: str) -> None:
        a = await self.ward_alert_repo.get_by_id(alert_id)
        if not a or a.ward_member_id != ward_member_id:
            raise ValueError("Alert not found.")
            
        a.status = "resolved"
        a.resolved_at = datetime.utcnow()
        await self.ward_alert_repo.update(a)

    async def get_alert_notifications_formatted(self, alert_id: str, ward_member_id: str) -> List[dict]:
        a = await self.ward_alert_repo.get_by_id(alert_id)
        if not a or a.ward_member_id != ward_member_id:
            raise ValueError("Alert not found.")
            
        notifs = await self.ward_notif_repo.list_by_alert(alert_id)
        
        results = []
        for n in notifs:
            donor_profile = await self.donor_repo.get_by_user_id(n.donor_id)
            donor_name = donor_profile.full_name if donor_profile else "Donor"
            donor_phone = donor_profile.phone if donor_profile else ""
            
            status_val = n.status
            if a.blood_request_id:
                resp = await self.response_repo.get_by_request_and_donor(a.blood_request_id, n.donor_id)
                if resp:
                    status_val = resp.status
                    
            results.append({
                "id": n.id,
                "donor_name": donor_name,
                "donor_phone": donor_phone,
                "status": status_val,
                "notes": n.notes,
                "contacted_at": n.contacted_at,
                "created_at": n.created_at
            })
        return results


