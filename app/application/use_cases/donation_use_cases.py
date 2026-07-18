from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Tuple, Any
from bson import ObjectId
from app.core.config import settings
from app.domain.entities.donation import (
    BloodRequest, DonationResponse, DonationRecord,
    DonorRating, DonorBadge, BloodCamp,
    CampRegistration, Notification
)
from app.domain.entities.ward import WardBloodAlert
from app.domain.services.location import haversine_distance
from app.domain.repositories.user_repo import UserRepository, HospitalProfileRepository, DonorProfileRepository
from app.domain.repositories.ward_repo import WardRepository, WardMemberRepository, WardBloodAlertRepository, WardDonorNotificationRepository
from app.domain.repositories.donation_repo import (
    BloodRequestRepository, DonationResponseRepository, DonationRecordRepository,
    DonorRatingRepository, DonorBadgeRepository,
    BloodCampRepository, CampRegistrationRepository, NotificationRepository
)
from app.application.dto.donation_dto import (
    BloodRequestCreateDTO, DonationResponseCreateDTO,
    DonationRecordCreateDTO, DonorRatingCreateDTO,
    BloodCampCreateDTO
)

# Background tasks / push / WebSocket interfaces
from app.infrastructure.external_services.firebase_fcm import send_push_notification
from app.infrastructure.external_services.openroute import calculate_driving_distance_and_eta

class DonationUseCases:
    def __init__(
        self,
        user_repo: UserRepository,
        hospital_repo: HospitalProfileRepository,
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
        camp_repo: BloodCampRepository,
        camp_reg_repo: CampRegistrationRepository,
        notif_repo: NotificationRepository,
        ws_broadcast_func: Optional[Any] = None # We will inject a function for WebSockets broadcast
    ):
        self.user_repo = user_repo
        self.hospital_repo = hospital_repo
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
        self.camp_repo = camp_repo
        self.camp_reg_repo = camp_reg_repo
        self.notif_repo = notif_repo
        self.ws_broadcast = ws_broadcast_func or (lambda g, ev, p: None)

    def _resolve_and_calculate_distance(
        self,
        br_lat: Optional[float],
        br_lng: Optional[float],
        r_lat: Optional[float],
        r_lng: Optional[float],
        hp_lat: Optional[float],
        hp_lng: Optional[float],
        dp_lat: Optional[float],
        dp_lng: Optional[float],
        stored_distance: Optional[float]
    ) -> Optional[float]:
        h_lat = hp_lat if hp_lat is not None else br_lat
        h_lng = hp_lng if hp_lng is not None else br_lng
        d_lat = r_lat if r_lat is not None else dp_lat
        d_lng = r_lng if r_lng is not None else dp_lng
        
        if h_lat is not None and h_lng is not None and d_lat is not None and d_lng is not None:
            try:
                return round(haversine_distance(h_lat, h_lng, d_lat, d_lng), 2)
            except Exception:
                pass
        return stored_distance

    async def create_blood_request(self, hospital_user_id: str, dto: BloodRequestCreateDTO) -> BloodRequest:
        hospital_profile = await self.hospital_repo.get_by_user_id(hospital_user_id)
        if not hospital_profile:
            raise ValueError("Hospital profile not found.")
            
        target_ward_id = None
        if dto.ward_id:
            target_ward = await self.ward_repo.get_by_id(dto.ward_id)
            if target_ward:
                target_ward_id = target_ward.id

        request = BloodRequest(
            hospital_id=hospital_user_id,
            blood_group=dto.blood_group,
            units_needed=dto.units_needed,
            urgency=dto.urgency,
            note=dto.note,
            patient_name=dto.patient_name,
            patient_age=dto.patient_age,
            patient_condition=dto.patient_condition or "",
            patient_ward=dto.patient_ward or "",
            patient_room=dto.patient_room or "",
            patient_bed=dto.patient_bed or "",
            ward_contact_person=dto.ward_contact_person or "",
            ward_contact_phone=dto.ward_contact_phone or "",
            bystander_name=dto.bystander_name or "",
            bystander_phone=dto.bystander_phone or "",
            patient_state=dto.patient_state or "",
            patient_district=dto.patient_district or "",
            patient_local_body_type=dto.patient_local_body_type or "",
            patient_local_body_name=dto.patient_local_body_name or "",
            patient_ward_number=dto.patient_ward_number or "",
            hospital_latitude=hospital_profile.latitude,
            hospital_longitude=hospital_profile.longitude,
            search_radius_km=dto.search_radius_km or 50,
            notify_ward_members=dto.notify_ward_members or False,
            ward_member_message=dto.ward_member_message or "",
            target_ward_id=target_ward_id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=2) # default 2 days expiry
        )
        
        created_request = await self.request_repo.create(request)
        return created_request

    async def notify_donors_and_wards_background(self, request_id: str):
        br = await self.request_repo.get_by_id(request_id)
        if not br:
            return
            
        hospital_user = await self.user_repo.get_by_id(br.hospital_id)
        hospital_profile = await self.hospital_repo.get_by_user_id(br.hospital_id)
        hospital_name = hospital_profile.name if hospital_profile else "Hospital"
        
        # Synchronize coordinates in the blood request if they mismatch
        if hospital_profile and (br.hospital_latitude != hospital_profile.latitude or br.hospital_longitude != hospital_profile.longitude):
            br.hospital_latitude = hospital_profile.latitude
            br.hospital_longitude = hospital_profile.longitude
            await self.request_repo.update(br)
            
        # 1. NOTIFY DONORS
        cooldown_cutoff = (datetime.utcnow() - timedelta(days=settings.DONOR_COOLDOWN_DAYS)).isoformat()
        
        # Search donors nearby using 2dsphere index if coordinates exist
        if br.hospital_longitude is not None and br.hospital_latitude is not None:
            donors = await self.donor_repo.search_donors(
                blood_group=br.blood_group,
                longitude=br.hospital_longitude,
                latitude=br.hospital_latitude,
                radius_km=br.search_radius_km,
                cooldown_cutoff_date=cooldown_cutoff
            )
        else:
            # Fallback if hospital has no coordinates: notify all matching blood group
            # In MongoDB, we query all available donors with correct blood group
            donors = await self.donor_repo.search_donors(
                blood_group=br.blood_group,
                longitude=0,
                latitude=0,
                radius_km=20037.5, # whole earth circumference radius fallback
                cooldown_cutoff_date=cooldown_cutoff
            )

        notified_donors = 0
        for dp in donors:
            dist = 0.0
            h_lat = hospital_profile.latitude if hospital_profile else br.hospital_latitude
            h_lng = hospital_profile.longitude if hospital_profile else br.hospital_longitude
            
            if h_lat is not None and h_lng is not None and dp.latitude is not None and dp.longitude is not None:
                try:
                    dist = round(haversine_distance(
                        h_lat, h_lng,
                        dp.latitude, dp.longitude
                    ), 2)
                except Exception:
                    pass
            
            resp, created = await self.response_repo.get_or_create(
                request_id=br.id,
                donor_id=dp.user_id,
                defaults={
                    "status": "pending",
                    "notification_sent_at": datetime.utcnow(),
                    "distance_km": dist
                }
            )
            if not created:
                continue
                
            donor_user = await self.user_repo.get_by_id(dp.user_id)
            if donor_user and donor_user.fcm_token:
                emoji = {"critical": "🚨", "urgent": "⚠️", "normal": "🩸"}.get(br.urgency, "🩸")
                send_push_notification(
                    fcm_token=donor_user.fcm_token,
                    title=f"{emoji} Blood Request — {br.blood_group}",
                    body=f"{hospital_name} urgently needs {br.blood_group} blood. Tap to respond.",
                    data={
                        "type": "blood_request",
                        "request_id": str(br.id),
                        "response_id": str(resp.id),
                        "blood_group": br.blood_group,
                        "urgency": br.urgency,
                        "hospital_name": hospital_name
                    }
                )
            
            # Send WebSocket alert to donor
            self.ws_broadcast(f"donor_{dp.user_id}", "new_request", {
                "response_id": resp.id,
                "request_id": br.id,
                "blood_group": br.blood_group,
                "urgency": br.urgency,
                "hospital_name": hospital_name,
                "units_needed": br.units_needed,
                "patient_name": br.patient_name,
                "patient_condition": br.patient_condition,
                "hospital_latitude": str(br.hospital_latitude or ""),
                "hospital_longitude": str(br.hospital_longitude or "")
            })
            notified_donors += 1

        if notified_donors > 0 and br.status == "pending":
            br.status = "active"
            await self.request_repo.update(br)
            
        # 2. NOTIFY WARD MEMBERS
        if br.notify_ward_members:
            filters = {}
            if br.target_ward_id:
                # Specific ward selected
                ward_members = await self.ward_member_repo.get_verified_members_by_ward(br.target_ward_id)
            else:
                # Search by patient area
                if br.patient_state:
                    filters["ward__state"] = br.patient_state
                if br.patient_district:
                    filters["ward__district"] = br.patient_district
                if br.patient_local_body_name:
                    filters["ward__local_body_name"] = br.patient_local_body_name
                if br.patient_ward_number:
                    filters["ward__ward_number"] = br.patient_ward_number
                
                # Retrieve matching wards
                if filters:
                    wards = await self.ward_repo.search_wards(filters)
                    ward_members = []
                    for w in wards[:10]:
                        members = await self.ward_member_repo.get_verified_members_by_ward(w.id)
                        ward_members.extend(members)
                else:
                    # Fallback to hospital area
                    wards = await self.ward_repo.search_wards({
                        "state": hospital_profile.state,
                        "district": hospital_profile.district or hospital_profile.city
                    })
                    ward_members = []
                    for w in wards[:10]:
                        members = await self.ward_member_repo.get_verified_members_by_ward(w.id)
                        ward_members.extend(members)
            
            notified_ward_members = 0
            for wm in ward_members[:10]:
                alert, created = await self.ward_alert_repo.get_or_create(
                    ward_member_id=wm.id,
                    blood_request_id=br.id,
                    defaults={
                        "blood_group": br.blood_group,
                        "urgency": br.urgency,
                        "patient_name": br.patient_name,
                        "patient_condition": br.patient_condition,
                        "hospital_name": hospital_name,
                        "hospital_phone": hospital_profile.phone if hospital_profile else "",
                        "hospital_whatsapp": hospital_profile.whatsapp_number if hospital_profile else "",
                        "hospital_latitude": br.hospital_latitude,
                        "hospital_longitude": br.hospital_longitude,
                        "hospital_message": br.ward_member_message,
                        "status": "pending"
                    }
                )
                if created:
                    wm_user = await self.user_repo.get_by_id(wm.user_id)
                    if wm_user and wm_user.fcm_token:
                        send_push_notification(
                            fcm_token=wm_user.fcm_token,
                            title=f"🏥 Blood Alert — {br.blood_group}",
                            body=f"{hospital_name} needs {br.blood_group}. Patient from your ward.",
                            data={
                                "type": "ward_blood_alert",
                                "alert_id": str(alert.id)
                            }
                        )
                    
                    self.ws_broadcast(f"ward_{wm.user_id}", "ward_blood_alert", {
                        "alert_id": alert.id,
                        "blood_group": br.blood_group,
                        "urgency": br.urgency,
                        "hospital_name": hospital_name,
                        "patient_name": br.patient_name,
                        "hospital_message": br.ward_member_message
                    })
                    notified_ward_members += 1

    async def get_hospital_requests(self, hospital_id: str, status: Optional[str] = None) -> List[BloodRequest]:
        return await self.request_repo.list_by_hospital(hospital_id, status)

    async def get_request_detail(self, request_id: str, hospital_id: str) -> BloodRequest:
        br = await self.request_repo.get_by_id(request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not found.")
        return br

    async def cancel_request(self, request_id: str, hospital_id: str) -> None:
        br = await self.request_repo.get_by_id(request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not found.")
        if br.status in ("completed", "cancelled"):
            raise ValueError(f"Already {br.status}.")
            
        br.status = "cancelled"
        await self.request_repo.update(br)

    async def clear_all_requests(self, hospital_id: str) -> int:
        return await self.request_repo.delete_completed_or_cancelled(hospital_id)

    async def get_top_3_donors(self, request_id: str, hospital_id: str) -> List[DonationResponse]:
        br = await self.request_repo.get_by_id(request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not found.")
            
        responses = await self.response_repo.list_by_request(br.id, ["accepted", "confirmed", "completed"])
        
        # Sort based on priority logic:
        # We need to sort by: ETA (lowest first). If ETA is same, sort by distance.
        # If response has no ETA, calculate ETA or put at bottom.
        # Let's also load the donor profile priority score if possible.
        # Let's map responses to include priority scores from donor profiles.
        scored_responses = []
        for r in responses:
            dp = await self.donor_repo.get_by_user_id(r.donor_id)
            priority = dp.priority_score if dp else 0
            # score: lower ETA/distance and higher priority.
            # E.g. sorting key: (status != 'confirmed', eta_minutes or 9999, distance_km or 9999, -priority)
            scored_responses.append((r, priority))
            
        # Sort by:
        # 1. 'confirmed' first (if already confirmed, it stays confirmed)
        # 2. eta_minutes (ascending)
        # 3. priority score (descending)
        scored_responses.sort(key=lambda x: (
            0 if x[0].status == "confirmed" else 1,
            x[0].eta_minutes if x[0].eta_minutes is not None else 99999,
            x[0].distance_km if x[0].distance_km is not None else 99999,
            -x[1]
        ))
        
        # Return top 3 responses
        return [item[0] for item in scored_responses[:3]]

    async def confirm_all_top_3(self, request_id: str, hospital_id: str, response_ids: List[str]) -> List[DonationResponse]:
        br = await self.request_repo.get_by_id(request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not found.")
            
        hospital_profile = await self.hospital_repo.get_by_user_id(hospital_id)
        hospital_name = hospital_profile.name if hospital_profile else "Hospital"
        
        if not response_ids:
            # Auto fallback to get top 3 accepted responses
            top_3 = await self.get_top_3_donors(request_id, hospital_id)
            response_ids = [r.id for r in top_3 if r.status == "accepted"]
            
        confirmed = []
        for rid in response_ids[:3]:
            resp = await self.response_repo.get_by_id(rid)
            if resp and resp.request_id == br.id and resp.status == "accepted":
                resp.status = "confirmed"
                await self.response_repo.update(resp)
                confirmed.append(resp)
                
                # Persist Notification in DB
                new_notif = Notification(
                    recipient_id=resp.donor_id,
                    request_id=br.id,
                    channel="push",
                    subject="✅ You are CONFIRMED!",
                    body=f"{hospital_name} selected you. Head to hospital now!",
                    status="sent",
                    sent_at=datetime.utcnow()
                )
                await self.notif_repo.create(new_notif)
                
                # Push Notification to donor
                donor_user = await self.user_repo.get_by_id(resp.donor_id)
                if donor_user and donor_user.fcm_token:
                    send_push_notification(
                        fcm_token=donor_user.fcm_token,
                        title="✅ You are CONFIRMED!",
                        body=f"{hospital_name} selected you. Head to hospital now!",
                        data={
                            "type": "donation_confirmed",
                            "response_id": str(resp.id),
                            "hospital_latitude": str(br.hospital_latitude or ""),
                            "hospital_longitude": str(br.hospital_longitude or "")
                        }
                    )
                
                # Send WebSocket alert to donor
                self.ws_broadcast(f"donor_{resp.donor_id}", "donation_confirmed", {
                    "response_id": resp.id,
                    "hospital_name": hospital_name,
                    "hospital_latitude": str(br.hospital_latitude or ""),
                    "hospital_longitude": str(br.hospital_longitude or "")
                })
                
                # Send WebSocket to TV dashboard
                dp = await self.donor_repo.get_by_user_id(resp.donor_id)
                if dp:
                    self.ws_broadcast(f"tv_{br.hospital_id}", "donor_confirmed", {
                        "response_id": resp.id,
                        "donor_name": dp.full_name,
                        "donor_phone": dp.phone,
                        "donor_whatsapp": dp.whatsapp_number,
                        "donor_latitude": str(resp.donor_latitude or ""),
                        "donor_longitude": str(resp.donor_longitude or ""),
                        "eta_minutes": resp.eta_minutes
                    })
                    
                # Update ward donor notification status if this was initiated by a ward member
                try:
                    alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
                    if alert:
                        wn_tuple = await self.ward_notif_repo.get_or_create(
                            alert_id=alert.id,
                            donor_id=resp.donor_id,
                            defaults={"status": "confirmed", "contacted_at": datetime.utcnow()}
                        )
                        wn, wn_created = wn_tuple
                        if not wn_created:
                            wn.status = "confirmed"
                            await self.ward_notif_repo.update(wn)
                            
                        # Broadcast real-time status update to ward member
                        self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                            "alert_id": alert.id,
                            "donor_id": resp.donor_id,
                            "donor_name": dp.full_name if dp else "Donor",
                            "status": "confirmed"
                        })
                except Exception:
                    pass
                    
        # Mark all other accepted responses as "missed"
        confirmed_ids = [r.id for r in confirmed]
        
        try:
            alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
            if alert:
                all_resps = await self.response_repo.list_by_request(br.id)
                for other in all_resps:
                    if other.id not in confirmed_ids and other.status == "accepted":
                        wn_tuple = await self.ward_notif_repo.get_or_create(
                            alert_id=alert.id,
                            donor_id=other.donor_id,
                            defaults={"status": "missed", "contacted_at": datetime.utcnow()}
                        )
                        wn, wn_created = wn_tuple
                        if not wn_created:
                            wn.status = "missed"
                            await self.ward_notif_repo.update(wn)
                            
                        self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                            "alert_id": alert.id,
                            "donor_id": other.donor_id,
                            "status": "missed"
                        })
        except Exception:
            pass
            
        await self.response_repo.update_status_by_query(
            {"request_id": br.id, "status": "accepted", "id": {"$nin": confirmed_ids}},
            "missed"
        )
        
        br.status = "confirmed"
        br.confirmed_donors_count = len(confirmed)
        await self.request_repo.update(br)
        
        return confirmed

    async def complete_donation(self, response_id: str, hospital_id: str, dto: DonationRecordCreateDTO) -> Tuple[DonationRecord, int]:
        resp = await self.response_repo.get_by_id(response_id)
        if not resp or resp.status != "confirmed":
            raise ValueError("Confirmed donor response not found.")
            
        br = await self.request_repo.get_by_id(resp.request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not authorized.")
            
        hospital_profile = await self.hospital_repo.get_by_user_id(hospital_id)
        if not hospital_profile:
            raise ValueError("Hospital profile not found.")
            
        cooldown_days = settings.DONOR_COOLDOWN_DAYS
        cooldown_until = datetime.utcnow() + timedelta(days=cooldown_days)
        
        record = DonationRecord(
            donor_id=resp.donor_id,
            request_id=br.id,
            response_id=resp.id,
            blood_group=br.blood_group,
            units_donated=dto.units_donated,
            hospital_name=hospital_profile.name,
            hospital_city=hospital_profile.city or "",
            cooldown_until=cooldown_until,
            notes=dto.notes or ""
        )
        
        created_record = await self.record_repo.create(record)
        
        # Update response status to completed
        resp.status = "completed"
        await self.response_repo.update(resp)
        
        # Update ward donor notification status if this was initiated by a ward member
        try:
            alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
            if alert:
                wn_tuple = await self.ward_notif_repo.get_or_create(
                    alert_id=alert.id,
                    donor_id=resp.donor_id,
                    defaults={"status": "completed", "contacted_at": datetime.utcnow()}
                )
                wn, wn_created = wn_tuple
                if not wn_created:
                    wn.status = "completed"
                    await self.ward_notif_repo.update(wn)
                    
                # Broadcast real-time status update to ward member
                self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                    "alert_id": alert.id,
                    "donor_id": resp.donor_id,
                    "donor_name": donor_user.full_name if 'donor_user' in locals() and donor_user else "Donor",
                    "status": "completed"
                })
        except Exception:
            pass
        
        # Update request completed count
        all_resps = await self.response_repo.list_by_request(br.id)
        br.completed_donations_count = len([r for r in all_resps if r.status == "completed"])
        
        if br.completed_donations_count >= br.units_needed:
            br.status = "completed"
            # Release other confirmed donors
            for other in all_resps:
                if other.status == "confirmed" and other.id != resp.id:
                    other.status = "not_needed"
                    await self.response_repo.update(other)
                    
                    try:
                        alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
                        if alert:
                            wn_tuple = await self.ward_notif_repo.get_or_create(
                                alert_id=alert.id,
                                donor_id=other.donor_id,
                                defaults={"status": "not_needed", "contacted_at": datetime.utcnow()}
                            )
                            wn, wn_created = wn_tuple
                            if not wn_created:
                                wn.status = "not_needed"
                                await self.ward_notif_repo.update(wn)
                                
                            self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                                "alert_id": alert.id,
                                "donor_id": other.donor_id,
                                "status": "not_needed"
                            })
                    except Exception:
                        pass
                    
                    other_donor = await self.user_repo.get_by_id(other.donor_id)
                    if other_donor and other_donor.fcm_token:
                        send_push_notification(
                            fcm_token=other_donor.fcm_token,
                            title="Blood Request Complete",
                            body="Enough blood collected. Thank you for your willingness!",
                            data={"type": "not_needed"}
                        )
                        
        await self.request_repo.update(br)
        
        # Push notification to the donor who donated
        donor_user = await self.user_repo.get_by_id(resp.donor_id)
        if donor_user and donor_user.fcm_token:
            send_push_notification(
                fcm_token=donor_user.fcm_token,
                title="🙏 Thank you for donating!",
                body=f"Recorded at {hospital_profile.name}. You are a hero!",
                data={"type": "donation_completed", "record_id": str(created_record.id)}
            )
            
        # Update badges asynchronously
        await self.update_badges_for_donor(resp.donor_id)
        
        return created_record, cooldown_days

    async def _promote_next_donor(self, br: BloodRequest, exclude_ids: List[str]) -> Optional[DonationResponse]:
        # Find next best accepted response
        responses = await self.response_repo.list_by_request(br.id, ["accepted"])
        # Filter excluded ones
        accepted = [r for r in responses if r.id not in exclude_ids]
        if not accepted:
            return None
            
        # Load priority scores
        scored = []
        for r in accepted:
            dp = await self.donor_repo.get_by_user_id(r.donor_id)
            priority = dp.priority_score if dp else 0
            scored.append((r, priority))
            
        # Sort
        scored.sort(key=lambda x: (
            x[0].eta_minutes if x[0].eta_minutes is not None else 99999,
            x[0].distance_km if x[0].distance_km is not None else 99999,
            -x[1]
        ))
        
        next_resp = scored[0][0]
        next_resp.status = "confirmed"
        await self.response_repo.update(next_resp)
        
        hospital_profile = await self.hospital_repo.get_by_user_id(br.hospital_id)
        hospital_name = hospital_profile.name if hospital_profile else "Hospital"
        
        donor_user = await self.user_repo.get_by_id(next_resp.donor_id)
        if donor_user and donor_user.fcm_token:
            send_push_notification(
                fcm_token=donor_user.fcm_token,
                title="You are CONFIRMED!",
                body=f"{hospital_name} needs you now. Head to the hospital!",
                data={"type": "donation_confirmed", "response_id": str(next_resp.id)}
            )
            
        self.ws_broadcast(f"donor_{next_resp.donor_id}", "donation_confirmed", {
            "response_id": next_resp.id,
            "hospital_name": hospital_name,
            "hospital_latitude": str(br.hospital_latitude or ""),
            "hospital_longitude": str(br.hospital_longitude or "")
        })
        
        return next_resp

    async def complete_without_donation(self, response_id: str, hospital_id: str, reason: str) -> None:
        resp = await self.response_repo.get_by_id(response_id)
        if not resp or resp.status != "confirmed":
            raise ValueError("Confirmed donor response not found.")
            
        br = await self.request_repo.get_by_id(resp.request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not authorized.")
            
        resp.status = "not_needed"
        await self.response_repo.update(resp)
        
        try:
            alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
            if alert:
                wn_tuple = await self.ward_notif_repo.get_or_create(
                    alert_id=alert.id,
                    donor_id=resp.donor_id,
                    defaults={"status": "not_needed", "contacted_at": datetime.utcnow()}
                )
                wn, wn_created = wn_tuple
                if not wn_created:
                    wn.status = "not_needed"
                    await self.ward_notif_repo.update(wn)
                    
                self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                    "alert_id": alert.id,
                    "donor_id": resp.donor_id,
                    "status": "not_needed"
                })
        except Exception:
            pass
        
        # Check if all confirmed are resolved
        all_resps = await self.response_repo.list_by_request(br.id)
        remaining = len([r for r in all_resps if r.status == "confirmed"])
        if remaining == 0:
            br.status = "completed"
            await self.request_repo.update(br)
            
        donor_user = await self.user_repo.get_by_id(resp.donor_id)
        if donor_user and donor_user.fcm_token:
            send_push_notification(
                fcm_token=donor_user.fcm_token,
                title="Blood Request Update",
                body=f"{reason}. Thank you for coming!",
                data={"type": "not_needed"}
            )
            
        self.ws_broadcast(f"donor_{resp.donor_id}", "not_needed", {
            "response_id": resp.id,
            "reason": reason
        })

    async def no_donation_arrived(self, response_id: str, hospital_id: str) -> Optional[DonationResponse]:
        resp = await self.response_repo.get_by_id(response_id)
        if not resp or resp.status != "confirmed":
            raise ValueError("Confirmed donor response not found.")
            
        br = await self.request_repo.get_by_id(resp.request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not authorized.")
            
        resp.status = "arrived_no_donation"
        await self.response_repo.update(resp)
        
        try:
            alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
            if alert:
                wn_tuple = await self.ward_notif_repo.get_or_create(
                    alert_id=alert.id,
                    donor_id=resp.donor_id,
                    defaults={"status": "arrived_no_donation", "contacted_at": datetime.utcnow()}
                )
                wn, wn_created = wn_tuple
                if not wn_created:
                    wn.status = "arrived_no_donation"
                    await self.ward_notif_repo.update(wn)
                    
                self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                    "alert_id": alert.id,
                    "donor_id": resp.donor_id,
                    "status": "arrived_no_donation"
                })
        except Exception:
            pass
        
        all_resps = await self.response_repo.list_by_request(br.id)
        confirmed_ids = [r.id for r in all_resps if r.status == "confirmed"]
        
        promoted = await self._promote_next_donor(br, exclude_ids=confirmed_ids + [resp.id])
        return promoted

    async def cancel_donor_assignment(self, response_id: str, hospital_id: str) -> Optional[DonationResponse]:
        resp = await self.response_repo.get_by_id(response_id)
        if not resp or resp.status not in ("pending", "accepted", "confirmed"):
            raise ValueError("Donor response not found or not in active state.")
            
        br = await self.request_repo.get_by_id(resp.request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not authorized.")
            
        was_confirmed = resp.status == "confirmed"
        resp.status = "cancelled"
        await self.response_repo.update(resp)
        
        try:
            alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
            if alert:
                wn_tuple = await self.ward_notif_repo.get_or_create(
                    alert_id=alert.id,
                    donor_id=resp.donor_id,
                    defaults={"status": "cancelled", "contacted_at": datetime.utcnow()}
                )
                wn, wn_created = wn_tuple
                if not wn_created:
                    wn.status = "cancelled"
                    await self.ward_notif_repo.update(wn)
                    
                self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                    "alert_id": alert.id,
                    "donor_id": resp.donor_id,
                    "status": "cancelled"
                })
        except Exception:
            pass
        
        donor_user = await self.user_repo.get_by_id(resp.donor_id)
        if donor_user and donor_user.fcm_token:
            send_push_notification(
                fcm_token=donor_user.fcm_token,
                title="Request Update",
                body="The hospital has cancelled your assignment.",
                data={"type": "cancelled"}
            )
            
        promoted = None
        if was_confirmed:
            all_resps = await self.response_repo.list_by_request(br.id)
            confirmed_ids = [r.id for r in all_resps if r.status == "confirmed"]
            promoted = await self._promote_next_donor(br, exclude_ids=confirmed_ids + [resp.id])
            
        return promoted

    async def cancel_and_notify_all(self, request_id: str, hospital_id: str) -> None:
        br = await self.request_repo.get_by_id(request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Blood request not found.")
        if br.status in ("completed", "cancelled"):
            raise ValueError(f"Already {br.status}.")
            
        responses = await self.response_repo.list_by_request(br.id, ["pending", "accepted", "confirmed"])
        for resp in responses:
            self.ws_broadcast(f"donor_{resp.donor_id}", "not_needed", {
                "response_id": resp.id,
                "reason": "Request cancelled"
            })
            donor_user = await self.user_repo.get_by_id(resp.donor_id)
            if donor_user and donor_user.fcm_token:
                send_push_notification(
                    fcm_token=donor_user.fcm_token,
                    title="Request Cancelled",
                    body="The blood request has been cancelled.",
                    data={"type": "not_needed"}
                )
                
        # Update response statuses
        response_ids = [r.id for r in responses]
        if response_ids:
            await self.response_repo.update_status_by_query(
                {"id": response_ids},
                "cancelled"
            )
            
        br.status = "cancelled"
        await self.request_repo.update(br)

    async def get_donor_pending_requests(self, donor_id: str) -> List[DonationResponse]:
        return await self.response_repo.list_pending_for_donor(donor_id)

    async def donor_respond(self, response_id: str, donor_id: str, dto: DonationResponseCreateDTO) -> int:
        resp = await self.response_repo.get_by_id(response_id)
        if not resp or resp.donor_id != donor_id or resp.status != "pending":
            raise ValueError("Response not found or already completed.")
            
        br = await self.request_repo.get_by_id(resp.request_id)
        if not br or br.status not in ("pending", "active"):
            raise ValueError("Blood request is no longer active.")
            
        dp = await self.donor_repo.get_by_user_id(donor_id)
        if not dp:
            raise ValueError("Donor profile not found.")
            
        resp.status = dto.status
        resp.responded_at = datetime.utcnow()
        
        eta_minutes = None
        if resp.status == "accepted":
            lat = dto.donor_latitude or dp.latitude
            lng = dto.donor_longitude or dp.longitude
            resp.donor_latitude = lat
            resp.donor_longitude = lng
            
            if lat is not None and lng is not None:
                dp.latitude = lat
                dp.longitude = lng
                await self.donor_repo.update(dp)
                
            hospital_profile = await self.hospital_repo.get_by_user_id(br.hospital_id)
            h_lat = hospital_profile.latitude if hospital_profile else br.hospital_latitude
            h_lng = hospital_profile.longitude if hospital_profile else br.hospital_longitude
            
            if hospital_profile and (br.hospital_latitude != hospital_profile.latitude or br.hospital_longitude != hospital_profile.longitude):
                br.hospital_latitude = hospital_profile.latitude
                br.hospital_longitude = hospital_profile.longitude
                await self.request_repo.update(br)
                
            if lat is not None and h_lat is not None:
                try:
                    resp.distance_km = round(haversine_distance(
                        h_lat, h_lng,
                        lat, lng
                    ), 2)
                except Exception:
                    pass
                    
            if br.status == "pending":
                br.status = "active"
                await self.request_repo.update(br)
                
            # ETA calculation
            if dto.eta_minutes is not None:
                eta_minutes = dto.eta_minutes
                resp.eta_minutes = eta_minutes
            elif resp.distance_km:
                eta_minutes = max(1, int(float(resp.distance_km) / 40 * 60)) # default 40 km/h
                resp.eta_minutes = eta_minutes
        else:
            resp.rejection_reason = dto.rejection_reason or ""
            
        await self.response_repo.update(resp)
        
        # Send WS broadcast to hospital
        self.ws_broadcast(f"hospital_{br.hospital_id}", "donor_responded", {
            "request_id": br.id,
            "response_id": resp.id,
            "donor_name": dp.full_name,
            "status": resp.status,
            "eta_minutes": resp.eta_minutes,
            "distance_km": str(resp.distance_km or ""),
            "donor_latitude": str(resp.donor_latitude or ""),
            "donor_longitude": str(resp.donor_longitude or "")
        })
        
        # Update ward donor notification status if this was initiated by a ward member
        try:
            alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
            if alert:
                wn_tuple = await self.ward_notif_repo.get_or_create(
                    alert_id=alert.id,
                    donor_id=donor_id,
                    defaults={"status": dto.status, "contacted_at": datetime.utcnow()}
                )
                wn, wn_created = wn_tuple
                if not wn_created:
                    wn.status = dto.status
                    await self.ward_notif_repo.update(wn)
                    
                # Broadcast real-time status update to ward member
                self.ws_broadcast(f"ward_{alert.ward_member_id}", "donor_responded", {
                    "alert_id": alert.id,
                    "donor_id": donor_id,
                    "donor_name": dp.full_name,
                    "status": dto.status
                })
        except Exception as e:
            pass
            
        return eta_minutes or 0


    async def get_hospital_dashboard(self, hospital_id: str) -> dict:
        requests = await self.request_repo.list_by_hospital(hospital_id)
        active_reqs = [r for r in requests if r.status in ("pending", "active", "confirmed")]
        
        active_list = []
        for br in active_reqs[:10]:
            top_3 = await self.get_top_3_donors(br.id, hospital_id)
            responses = await self.response_repo.list_by_request(br.id)
            
            # Subdivide response details
            accepted_count = len([x for x in responses if x.status in ("accepted", "confirmed")])
            rejected_count = len([x for x in responses if x.status == "rejected"])
            pending_count = len([x for x in responses if x.status == "pending"])
            
            confirmed_donors = [x for x in responses if x.status in ("confirmed", "completed")]
            
            # Convert to list/detail DTOs later in API layer
            active_list.append({
                "request": br,
                "top_3": top_3,
                "total_notified": len(responses),
                "accepted_count": accepted_count,
                "rejected_count": rejected_count,
                "pending_count": pending_count,
                "confirmed_donors": confirmed_donors
            })
            
        total_requests = len(requests)
        active_requests_count = len(active_reqs)
        completed_donations = await self.record_repo.count_by_hospital(hospital_id)
        
        month_ago = datetime.utcnow() - timedelta(days=30)
        donations_this_month = await self.record_repo.count_by_hospital(hospital_id, since=month_ago)
        
        return {
            "stats": {
                "total_requests": total_requests,
                "active_requests": active_requests_count,
                "completed_donations": completed_donations,
                "donations_this_month": donations_this_month
            },
            "active_requests": active_list
        }

    async def get_tv_screen_data(self, hospital_id: str) -> dict:
        hospital_profile = await self.hospital_repo.get_by_user_id(hospital_id)
        
        # Get latest active/confirmed request
        requests = await self.request_repo.list_by_hospital(hospital_id)
        active = None
        for r in requests:
            if r.status in ("active", "confirmed"):
                active = r
                break
                
        if not active:
            return {"hospital": None, "active_request": None, "confirmed_donors": []}
            
        confirmed_resps = await self.response_repo.list_by_request(active.id, ["confirmed", "completed"])
        donors_data = []
        for r in confirmed_resps:
            dp = await self.donor_repo.get_by_user_id(r.donor_id)
            if dp:
                donors_data.append({
                    "response_id": r.id,
                    "donor_name": dp.full_name,
                    "donor_phone": dp.phone,
                    "donor_whatsapp": dp.whatsapp_number,
                    "eta_minutes": r.eta_minutes,
                    "status": r.status,
                    "donor_latitude": str(r.donor_latitude or ""),
                    "donor_longitude": str(r.donor_longitude or "")
                })
                
        hospital_data = None
        if hospital_profile:
            hospital_data = {
                "name": hospital_profile.name,
                "latitude": str(hospital_profile.latitude or ""),
                "longitude": str(hospital_profile.longitude or "")
            }
            
        return {
            "hospital": hospital_data,
            "active_request": active,
            "confirmed_donors": donors_data
        }

    async def get_analytics(self, hospital_id: str) -> dict:
        stats = await self.record_repo.get_success_rate_and_breakdowns(hospital_id)
        
        month_ago = datetime.utcnow() - timedelta(days=30)
        stats["donations_this_month"] = await self.record_repo.count_by_hospital(hospital_id, since=month_ago)
        
        # Calculate monthly counts for the past 90 days
        stats["monthly_donations"] = await self.record_repo.get_monthly_counts_past_90_days()
        
        avg_rating = await self.rating_repo.get_avg_rating_given_by_hospital(hospital_id)
        stats["avg_donor_rating"] = round(avg_rating or 0.0, 2)
        
        return stats


    # ─── Rating & Badges ───
    async def rate_donor(self, record_id: str, hospital_id: str, dto: DonorRatingCreateDTO) -> DonorRating:
        record = await self.record_repo.get_by_id(record_id)
        if not record:
            raise ValueError("Donation record not found.")
            
        br = await self.request_repo.get_by_id(record.request_id)
        if not br or br.hospital_id != hospital_id:
            raise ValueError("Not authorized to rate this donation.")
            
        existing = await self.rating_repo.get_by_record_id(record_id)
        if existing:
            raise ValueError("Already rated.")
            
        rating = DonorRating(
            record_id=record_id,
            donor_id=record.donor_id,
            rated_by=hospital_id,
            stars=dto.stars,
            punctuality=dto.punctuality or "",
            fitness=dto.fitness or "",
            feedback=dto.feedback or ""
        )
        
        created_rating = await self.rating_repo.create(rating)
        
        # Update badges asynchronously
        await self.update_badges_for_donor(record.donor_id)
        
        return created_rating

    async def update_badges_for_donor(self, donor_id: str) -> List[str]:
        """Calculates and updates donor badges based on counts and ratings."""
        badges = []
        count = await self.record_repo.count_by_donor(donor_id)
        
        if count >= 1:
            await self.badge_repo.get_or_create(donor_id, "first_drop")
            badges.append("first_drop")
        if count >= 5:
            await self.badge_repo.get_or_create(donor_id, "lifesaver")
            badges.append("lifesaver")
        if count >= 10:
            await self.badge_repo.get_or_create(donor_id, "hero")
            badges.append("hero")
        if count >= 20:
            await self.badge_repo.get_or_create(donor_id, "legend")
            badges.append("legend")
            
        # Top-rated badge
        avg_rating = await self.rating_repo.get_avg_rating_for_donor(donor_id)
        if avg_rating and avg_rating >= 4.8 and count >= 3:
            await self.badge_repo.get_or_create(donor_id, "top_rated")
            badges.append("top_rated")
            
        return badges

    async def get_donor_badges(self, donor_id: str) -> List[DonorBadge]:
        return await self.badge_repo.list_by_donor(donor_id)

    # ─── Blood Camps ───
    async def create_blood_camp(self, hospital_id: str, dto: BloodCampCreateDTO) -> BloodCamp:
        camp = BloodCamp(
            hospital_id=hospital_id,
            title=dto.title,
            description=dto.description or "",
            location=dto.location,
            city=dto.city,
            state=dto.state,
            latitude=dto.latitude,
            longitude=dto.longitude,
            scheduled_date=dto.scheduled_date,
            start_time=dto.start_time,
            end_time=dto.end_time,
            capacity=dto.capacity or 50,
            target_blood_groups=dto.target_blood_groups or "",
            is_active=True
        )
        return await self.camp_repo.create(camp)

    async def list_active_camps(self, city: Optional[str] = None, blood_group: Optional[str] = None) -> List[BloodCamp]:
        return await self.camp_repo.list_active_camps(city, blood_group)

    async def register_donor_for_camp(self, camp_id: str, donor_id: str) -> CampRegistration:
        camp = await self.camp_repo.get_by_id(camp_id)
        if not camp or not camp.is_active:
            raise ValueError("Camp not active or not found.")
            
        registered_count = await self.camp_reg_repo.count_active_by_camp(camp_id)
        if registered_count >= camp.capacity:
            raise ValueError("Camp is fully booked.")
            
        reg, created = await self.camp_reg_repo.get_or_create(
            camp_id=camp_id,
            donor_id=donor_id,
            defaults={"status": "registered"}
        )
        if not created:
            if reg.status == "cancelled":
                reg.status = "registered"
                await self.camp_reg_repo.update(reg)
            else:
                raise ValueError("Already registered.")
                
        return reg

    async def cancel_camp_registration(self, camp_id: str, donor_id: str) -> None:
        reg = await self.camp_reg_repo.get_by_camp_and_donor(camp_id, donor_id)
        if not reg or reg.status != "registered":
            raise ValueError("Active registration not found.")
            
        reg.status = "cancelled"
        await self.camp_reg_repo.update(reg)

    async def get_donor_camp_registrations(self, donor_id: str) -> List[CampRegistration]:
        return await self.camp_reg_repo.list_by_donor(donor_id)

    async def get_hospital_camps(self, hospital_id: str) -> List[BloodCamp]:
        return await self.camp_repo.list_by_hospital(hospital_id)

    async def get_notifications(self, recipient_id: str) -> List[Notification]:
        return await self.notif_repo.list_by_recipient(recipient_id)

    async def clear_hospital_data(self, hospital_id: str) -> int:
        return await self.request_repo.clear_hospital_data(hospital_id)

    async def get_request_detail_with_counts(self, request_id: str, hospital_id: str) -> dict:
        br = await self.get_request_detail(request_id, hospital_id)
        responses = await self.response_repo.list_by_request(request_id)
        accepted_cnt = len([x for x in responses if x.status in ("accepted", "confirmed")])
        rejected_cnt = len([x for x in responses if x.status == "rejected"])
        pending_cnt = len([x for x in responses if x.status == "pending"])
        return {
            "request": br,
            "total_notified": len(responses),
            "accepted_count": accepted_cnt,
            "rejected_count": rejected_cnt,
            "pending_count": pending_cnt
        }

    async def get_request_top3_details(self, request_id: str, hospital_id: str) -> dict:
        top_3 = await self.get_top_3_donors(request_id, hospital_id)
        hospital_profile = await self.hospital_repo.get_by_user_id(hospital_id)
        br = await self.request_repo.get_by_id(request_id)
        
        responses = await self.response_repo.list_by_request(request_id)
        total_accepted = len([x for x in responses if x.status in ("accepted", "confirmed")])
        pending_count = len([x for x in responses if x.status == "pending"])
        rejected_count = len([x for x in responses if x.status == "rejected"])
        
        top_3_data = []
        for r in top_3:
            dp = await self.donor_repo.get_by_user_id(r.donor_id)
            avg_rating = await self.rating_repo.get_avg_rating_for_donor(r.donor_id)
            total_donations = await self.record_repo.count_by_donor(r.donor_id)
            all_resps = await self.response_repo.list_history_for_donor(r.donor_id)
            responded = [x for x in all_resps if x.status in ("accepted", "confirmed", "completed", "rejected")]
            accepted = [x for x in responded if x.status in ("accepted", "confirmed", "completed")]
            acceptance_rate = int(len(accepted) / len(responded) * 100) if responded else 0
            
            dist = self._resolve_and_calculate_distance(
                br_lat=br.hospital_latitude if br else None,
                br_lng=br.hospital_longitude if br else None,
                r_lat=r.donor_latitude,
                r_lng=r.donor_longitude,
                hp_lat=hospital_profile.latitude if hospital_profile else None,
                hp_lng=hospital_profile.longitude if hospital_profile else None,
                dp_lat=dp.latitude if dp else None,
                dp_lng=dp.longitude if dp else None,
                stored_distance=r.distance_km
            )
            
            top_3_data.append({
                "id": r.id,
                "donor_id": r.donor_id,
                "donor_name": dp.full_name if dp else "Donor",
                "donor_phone": dp.phone if dp else "",
                "donor_whatsapp": dp.whatsapp_number if dp else "",
                "status": r.status,
                "distance_km": dist,
                "eta_minutes": r.eta_minutes,
                "avg_rating": round(avg_rating, 1) if avg_rating else None,
                "total_donations": total_donations,
                "acceptance_rate": acceptance_rate
            })
            
        return {
            "request_id": request_id,
            "top_3": top_3_data,
            "total_accepted": total_accepted,
            "pending_count": pending_count,
            "rejected_count": rejected_count
        }

    async def confirm_top3_and_get_details(self, request_id: str, hospital_id: str, response_ids: List[str]) -> List[dict]:
        confirmed = await self.confirm_all_top_3(request_id, hospital_id, response_ids)
        hospital_profile = await self.hospital_repo.get_by_user_id(hospital_id)
        br = await self.request_repo.get_by_id(request_id)
        
        confirmed_data = []
        for r in confirmed:
            dp = await self.donor_repo.get_by_user_id(r.donor_id)
            dist = self._resolve_and_calculate_distance(
                br_lat=br.hospital_latitude if br else None,
                br_lng=br.hospital_longitude if br else None,
                r_lat=r.donor_latitude,
                r_lng=r.donor_longitude,
                hp_lat=hospital_profile.latitude if hospital_profile else None,
                hp_lng=hospital_profile.longitude if hospital_profile else None,
                dp_lat=dp.latitude if dp else None,
                dp_lng=dp.longitude if dp else None,
                stored_distance=r.distance_km
            )
            confirmed_data.append({
                "id": r.id,
                "donor_id": r.donor_id,
                "donor_name": dp.full_name if dp else "Donor",
                "donor_phone": dp.phone if dp else "",
                "status": r.status,
                "distance_km": dist,
                "eta_minutes": r.eta_minutes
            })
        return confirmed_data

    async def no_donation_arrived_with_details(self, response_id: str, hospital_id: str) -> dict:
        promoted = await self.no_donation_arrived(response_id, hospital_id)
        promoted_name = None
        if promoted:
            dp = await self.donor_repo.get_by_user_id(promoted.donor_id)
            promoted_name = dp.full_name if dp else "Next donor"
        return {
            "promoted": bool(promoted),
            "promoted_name": promoted_name
        }

    async def cancel_donor_assignment_with_details(self, response_id: str, hospital_id: str) -> dict:
        promoted = await self.cancel_donor_assignment(response_id, hospital_id)
        promoted_name = None
        if promoted:
            dp = await self.donor_repo.get_by_user_id(promoted.donor_id)
            promoted_name = dp.full_name if dp else "Next donor"
        return {
            "promoted": bool(promoted),
            "promoted_name": promoted_name
        }

    async def map_response_to_donor_view(self, r: DonationResponse) -> dict:
        br = await self.request_repo.get_by_id(r.request_id)
        hp = await self.hospital_repo.get_by_user_id(br.hospital_id) if br else None
        dp = await self.donor_repo.get_by_user_id(r.donor_id)
        
        dist = self._resolve_and_calculate_distance(
            br_lat=br.hospital_latitude if br else None,
            br_lng=br.hospital_longitude if br else None,
            r_lat=r.donor_latitude,
            r_lng=r.donor_longitude,
            hp_lat=hp.latitude if hp else None,
            hp_lng=hp.longitude if hp else None,
            dp_lat=dp.latitude if dp else None,
            dp_lng=dp.longitude if dp else None,
            stored_distance=r.distance_km
        )
        
        via_ward = False
        ward_member_name = None
        ward_member_phone = None
        
        if br and br.notify_ward_members:
            via_ward = True
            target_ward_id = br.target_ward_id
            if target_ward_id:
                # Hospital explicitly selected a ward when creating the request.
                # Show the first verified member of that ward.
                wms = await self.ward_member_repo.get_verified_members_by_ward(target_ward_id)
                if wms:
                    ward_member_name = wms[0].full_name
                    ward_member_phone = wms[0].phone
            else:
                # No ward was pre-selected; look up the WardBloodAlert that was
                # created when the background notification task ran.
                alert = await self.ward_alert_repo.get_by_blood_request_id(br.id)
                if alert:
                    wm = await self.ward_member_repo.get_by_id(alert.ward_member_id)
                    if wm:
                        ward_member_name = wm.full_name
                        ward_member_phone = wm.phone
                
                # If still not found, check if the donor has an assigned ward_member_id
                if not ward_member_name and dp and dp.ward_member_id:
                    wm = await self.ward_member_repo.get_by_id(dp.ward_member_id)
                    if wm:
                        ward_member_name = wm.full_name
                        ward_member_phone = wm.phone
                        
        return {
            "id": r.id,
            "request_id": r.request_id,
            "donor_id": r.donor_id,
            "status": r.status,
            "eta_minutes": r.eta_minutes,
            "distance_km": dist,
            "blood_group": br.blood_group if br else "",
            "units_needed": br.units_needed if br else 1,
            "urgency": br.urgency if br else "normal",
            "hospital_name": hp.name if hp else "Hospital",
            "hospital_phone": hp.phone if hp else "",
            "hospital_whatsapp": hp.whatsapp_number if hp else "",
            "hospital_latitude": hp.latitude if hp else None,
            "hospital_longitude": hp.longitude if hp else None,
            "patient_name": br.patient_name if br else "",
            "patient_condition": br.patient_condition if br else "",
            "bystander_name": br.bystander_name if br else "",
            "bystander_phone": br.bystander_phone if br else "",
            "via_ward": via_ward,
            "ward_member_name": ward_member_name,
            "ward_member_phone": ward_member_phone,
            "responded_at": r.responded_at,
            "created_at": r.created_at
        }

    async def get_donor_pending_requests_view(self, donor_id: str) -> List[dict]:
        pending = await self.get_donor_pending_requests(donor_id)
        results = []
        for r in pending:
            mapped = await self.map_response_to_donor_view(r)
            results.append(mapped)
        return results

    async def list_donor_responses_view(self, donor_id: str) -> List[dict]:
        resps = await self.response_repo.list_history_for_donor(donor_id)
        results = []
        for r in resps:
            mapped = await self.map_response_to_donor_view(r)
            results.append(mapped)
        return results

    async def get_donor_history(self, donor_id: str) -> List[dict]:
        records = await self.record_repo.list_by_donor(donor_id)
        results = []
        for r in records:
            results.append({
                "id": r.id,
                "blood_group": r.blood_group,
                "units_donated": r.units_donated,
                "hospital_name": r.hospital_name,
                "hospital_city": r.hospital_city,
                "donated_at": r.donated_at,
                "notes": r.notes
            })
        return results

    async def get_donor_cooldown_status(self, donor_id: str) -> dict:
        last = await self.record_repo.get_last_for_donor(donor_id)
        if not last:
            return {
                "is_on_cooldown": False,
                "last_donation": None,
                "cooldown_until": None,
                "days_remaining": 0
            }
            
        now = datetime.utcnow()
        cd_until = last.cooldown_until
        on_cd = now < cd_until if cd_until else False
        days = max(0, (cd_until - now).days) if on_cd else 0
        
        return {
            "is_on_cooldown": on_cd,
            "last_donation": last.donated_at,
            "cooldown_until": cd_until,
            "days_remaining": days
        }

    async def get_hospital_dashboard_formatted(self, hospital_id: str) -> dict:
        data = await self.get_hospital_dashboard(hospital_id)
        hospital_profile = await self.hospital_repo.get_by_user_id(hospital_id)
        
        formatted_active = []
        for item in data["active_requests"]:
            br = item["request"]
            top_3 = item["top_3"]
            confirmed_donors = item["confirmed_donors"]
            
            top_3_list = []
            for r in top_3:
                dp = await self.donor_repo.get_by_user_id(r.donor_id)
                avg_rating = await self.rating_repo.get_avg_rating_for_donor(r.donor_id)
                total_donations = await self.record_repo.count_by_donor(r.donor_id)
                all_resps = await self.response_repo.list_history_for_donor(r.donor_id)
                responded = [x for x in all_resps if x.status in ("accepted", "confirmed", "completed", "rejected")]
                accepted = [x for x in responded if x.status in ("accepted", "confirmed", "completed")]
                acceptance_rate = int(len(accepted) / len(responded) * 100) if responded else 0
                
                dist = self._resolve_and_calculate_distance(
                    br_lat=br.hospital_latitude,
                    br_lng=br.hospital_longitude,
                    r_lat=r.donor_latitude,
                    r_lng=r.donor_longitude,
                    hp_lat=hospital_profile.latitude if hospital_profile else None,
                    hp_lng=hospital_profile.longitude if hospital_profile else None,
                    dp_lat=dp.latitude if dp else None,
                    dp_lng=dp.longitude if dp else None,
                    stored_distance=r.distance_km
                )
                
                top_3_list.append({
                    "id": r.id,
                    "donor_id": r.donor_id,
                    "donor_name": dp.full_name if dp else "Donor",
                    "donor_phone": dp.phone if dp else "",
                    "donor_whatsapp": dp.whatsapp_number if dp else "",
                    "status": r.status,
                    "distance_km": dist,
                    "eta_minutes": r.eta_minutes,
                    "avg_rating": round(avg_rating, 1) if avg_rating else None,
                    "total_donations": total_donations,
                    "acceptance_rate": acceptance_rate
                })
                
            confirmed_list = []
            for r in confirmed_donors:
                dp = await self.donor_repo.get_by_user_id(r.donor_id)
                dist = self._resolve_and_calculate_distance(
                    br_lat=br.hospital_latitude,
                    br_lng=br.hospital_longitude,
                    r_lat=r.donor_latitude,
                    r_lng=r.donor_longitude,
                    hp_lat=hospital_profile.latitude if hospital_profile else None,
                    hp_lng=hospital_profile.longitude if hospital_profile else None,
                    dp_lat=dp.latitude if dp else None,
                    dp_lng=dp.longitude if dp else None,
                    stored_distance=r.distance_km
                )
                confirmed_list.append({
                    "id": r.id,
                    "donor_id": r.donor_id,
                    "donor_name": dp.full_name if dp else "Donor",
                    "donor_phone": dp.phone if dp else "",
                    "donor_whatsapp": dp.whatsapp_number if dp else "",
                    "status": r.status,
                    "distance_km": dist,
                    "eta_minutes": r.eta_minutes
                })
                
            formatted_active.append({
                "request": {
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
                "top_3": top_3_list,
                "total_notified": item["total_notified"],
                "accepted_count": item["accepted_count"],
                "rejected_count": item["rejected_count"],
                "pending_count": item["pending_count"],
                "confirmed_donors": confirmed_list
            })
            
        return {
            "stats": data["stats"],
            "active_requests": formatted_active
        }

    async def list_active_camps_formatted(self, city: Optional[str] = None, blood_group: Optional[str] = None) -> List[dict]:
        camps = await self.list_active_camps(city, blood_group)
        results = []
        for c in camps:
            count = await self.camp_reg_repo.count_active_by_camp(c.id)
            hp = await self.hospital_repo.get_by_user_id(c.hospital_id)
            hospital_name = hp.name if hp else "Hospital"
            results.append({
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "location": c.location,
                "city": c.city,
                "state": c.state,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "scheduled_date": c.scheduled_date.isoformat() if isinstance(c.scheduled_date, (datetime, date)) else str(c.scheduled_date),
                "start_time": c.start_time,
                "end_time": c.end_time,
                "capacity": c.capacity,
                "target_blood_groups": c.target_blood_groups,
                "registered_count": count,
                "is_full": count >= c.capacity,
                "hospital_name": hospital_name
            })
        return results

    async def get_donor_camp_registrations_formatted(self, donor_id: str) -> List[dict]:
        regs = await self.get_donor_camp_registrations(donor_id)
        results = []
        for r in regs:
            c = await self.camp_repo.get_by_id(r.camp_id)
            if c:
                hp = await self.hospital_repo.get_by_user_id(c.hospital_id)
                hospital_name = hp.name if hp else "Hospital"
                results.append({
                    "id": r.id,
                    "camp": {
                        "id": c.id,
                        "title": c.title,
                        "location": c.location,
                        "scheduled_date": c.scheduled_date.isoformat() if isinstance(c.scheduled_date, (datetime, date)) else str(c.scheduled_date),
                        "hospital_name": hospital_name
                    },
                    "status": r.status,
                    "registered_at": r.registered_at
                })
        return results

    async def get_hospital_camps_formatted(self, hospital_id: str) -> List[dict]:
        camps = await self.get_hospital_camps(hospital_id)
        results = []
        for c in camps:
            count = await self.camp_reg_repo.count_active_by_camp(c.id)
            results.append({
                "id": c.id,
                "title": c.title,
                "location": c.location,
                "scheduled_date": c.scheduled_date.isoformat() if isinstance(c.scheduled_date, (datetime, date)) else str(c.scheduled_date),
                "capacity": c.capacity,
                "registered_count": count,
                "is_full": count >= c.capacity
            })
        return results

