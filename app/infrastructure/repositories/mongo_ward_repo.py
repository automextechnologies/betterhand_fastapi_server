from typing import Optional, List, Dict
from datetime import datetime
from bson import ObjectId
from app.infrastructure.database.mongodb import db
from app.domain.entities.ward import Ward, WardMember, WardBloodAlert, WardDonorNotification
from app.domain.repositories.ward_repo import (
    WardRepository, WardMemberRepository, WardBloodAlertRepository, WardDonorNotificationRepository
)

def map_ward_to_entity(doc: dict) -> Ward:
    loc = doc.get("location")
    lat, lng = None, None
    if loc and loc.get("type") == "Point":
        coords = loc.get("coordinates")
        if coords and len(coords) == 2:
            lng, lat = coords[0], coords[1]
            
    return Ward(
        id=str(doc["_id"]),
        ward_number=doc.get("ward_number", ""),
        local_body_name=doc.get("local_body_name", ""),
        local_body_type=doc.get("local_body_type", "Gram Panchayat"),
        district=doc.get("district", ""),
        state=doc.get("state", ""),
        latitude=lat,
        longitude=lng,
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_ward_to_db(entity: Ward) -> dict:
    data = {
        "ward_number": entity.ward_number,
        "local_body_name": entity.local_body_name,
        "local_body_type": entity.local_body_type,
        "district": entity.district,
        "state": entity.state,
        "created_at": entity.created_at
    }
    
    if entity.longitude is not None and entity.latitude is not None:
        data["location"] = {
            "type": "Point",
            "coordinates": [float(entity.longitude), float(entity.latitude)]
        }
    else:
        data["location"] = None
        
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


def map_ward_member_to_entity(doc: dict) -> WardMember:
    return WardMember(
        id=str(doc["_id"]),
        user_id=str(doc.get("user_id", "")),
        ward_id=str(doc.get("ward_id", "")),
        full_name=doc.get("full_name", ""),
        phone=doc.get("phone", ""),
        designation=doc.get("designation", ""),
        is_verified=doc.get("is_verified", False),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_ward_member_to_db(entity: WardMember) -> dict:
    data = {
        "user_id": ObjectId(entity.user_id) if entity.user_id else "",
        "ward_id": ObjectId(entity.ward_id) if entity.ward_id else "",
        "full_name": entity.full_name,
        "phone": entity.phone,
        "designation": entity.designation,
        "is_verified": entity.is_verified,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


def map_alert_to_entity(doc: dict) -> WardBloodAlert:
    return WardBloodAlert(
        id=str(doc["_id"]),
        ward_member_id=str(doc.get("ward_member_id", "")),
        blood_request_id=str(doc.get("blood_request_id")) if doc.get("blood_request_id") else None,
        blood_group=doc.get("blood_group", ""),
        urgency=doc.get("urgency", "normal"),
        patient_name=doc.get("patient_name", ""),
        patient_condition=doc.get("patient_condition", ""),
        hospital_name=doc.get("hospital_name", ""),
        hospital_phone=doc.get("hospital_phone", ""),
        hospital_whatsapp=doc.get("hospital_whatsapp", ""),
        hospital_latitude=doc.get("hospital_latitude"),
        hospital_longitude=doc.get("hospital_longitude"),
        hospital_message=doc.get("hospital_message", ""),
        bystander_phone=doc.get("bystander_phone", ""),
        status=doc.get("status", "pending"),
        resolved_at=doc.get("resolved_at"),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_alert_to_db(entity: WardBloodAlert) -> dict:
    data = {
        "ward_member_id": ObjectId(entity.ward_member_id) if entity.ward_member_id else "",
        "blood_request_id": ObjectId(entity.blood_request_id) if entity.blood_request_id else None,
        "blood_group": entity.blood_group,
        "urgency": entity.urgency,
        "patient_name": entity.patient_name,
        "patient_condition": entity.patient_condition,
        "hospital_name": entity.hospital_name,
        "hospital_phone": entity.hospital_phone,
        "hospital_whatsapp": entity.hospital_whatsapp,
        "hospital_latitude": entity.hospital_latitude,
        "hospital_longitude": entity.hospital_longitude,
        "hospital_message": entity.hospital_message,
        "bystander_phone": entity.bystander_phone,
        "status": entity.status,
        "resolved_at": entity.resolved_at,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


def map_notif_to_entity(doc: dict) -> WardDonorNotification:
    return WardDonorNotification(
        id=str(doc["_id"]),
        alert_id=str(doc.get("alert_id", "")),
        donor_id=str(doc.get("donor_id", "")),
        status=doc.get("status", "pending"),
        notes=doc.get("notes", ""),
        contacted_at=doc.get("contacted_at"),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_notif_to_db(entity: WardDonorNotification) -> dict:
    data = {
        "alert_id": ObjectId(entity.alert_id) if entity.alert_id else "",
        "donor_id": ObjectId(entity.donor_id) if entity.donor_id else "",
        "status": entity.status,
        "notes": entity.notes,
        "contacted_at": entity.contacted_at,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


class MongoWardRepository(WardRepository):
    async def get_by_id(self, ward_id: str) -> Optional[Ward]:
        try:
            doc = await db.db.wards.find_one({"_id": ObjectId(ward_id)})
            return map_ward_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_or_create(
        self,
        ward_number: str,
        local_body_name: str,
        state: str,
        defaults: dict
    ) -> tuple[Ward, bool]:
        query = {
            "ward_number": ward_number.strip(),
            "local_body_name": local_body_name.strip(),
            "state": state.strip()
        }
        doc = await db.db.wards.find_one(query)
        if doc:
            return map_ward_to_entity(doc), False
            
        new_ward_data = query.copy()
        new_ward_data.update(defaults)
        
        # Check coordinates and convert to location
        lat = new_ward_data.pop("latitude", None)
        lng = new_ward_data.pop("longitude", None)
        ward = Ward(
            ward_number=ward_number,
            local_body_name=local_body_name,
            state=state,
            local_body_type=new_ward_data.get("local_body_type", "Gram Panchayat"),
            district=new_ward_data.get("district", ""),
            latitude=lat,
            longitude=lng
        )
        
        db_doc = map_ward_to_db(ward)
        result = await db.db.wards.insert_one(db_doc)
        ward.id = str(result.inserted_id)
        return ward, True

    async def search_wards(self, filters: dict, has_member: bool = False) -> List[Ward]:
        query = {}
        for k, v in filters.items():
            clean_key = k.replace("ward__", "")
            if v:
                if isinstance(v, str):
                    query[clean_key] = {"$regex": f"^{v}$", "$options": "i"}
                else:
                    query[clean_key] = v

        # Optionally restrict results to wards that have at least one
        # registered ward member.
        if has_member:
            registered_members = await db.db.ward_members.find(
                {}
            ).to_list(length=1000)

            ward_ids = []
            for m in registered_members:
                raw = m.get("ward_id")
                if raw is None:
                    continue
                try:
                    ward_ids.append(raw if isinstance(raw, ObjectId) else ObjectId(raw))
                except Exception:
                    continue

            ward_ids = list(set(ward_ids))

            if ward_ids:
                query["_id"] = {"$in": ward_ids}
            else:
                # No members exist — return empty immediately.
                return []

        docs = await db.db.wards.find(query).to_list(length=200)
        return [map_ward_to_entity(doc) for doc in docs]


    async def list_all(self) -> List[Ward]:
        docs = await db.db.wards.find({}).to_list(length=10000)
        return [map_ward_to_entity(doc) for doc in docs]


class MongoWardMemberRepository(WardMemberRepository):
    async def get_by_id(self, member_id: str) -> Optional[WardMember]:
        try:
            doc = await db.db.ward_members.find_one({"_id": ObjectId(member_id)})
            return map_ward_member_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_by_user_id(self, user_id: str) -> Optional[WardMember]:
        try:
            doc = await db.db.ward_members.find_one({"user_id": ObjectId(user_id)})
            return map_ward_member_to_entity(doc) if doc else None
        except Exception:
            return None

    async def create(self, member: WardMember) -> WardMember:
        doc = map_ward_member_to_db(member)
        result = await db.db.ward_members.insert_one(doc)
        member.id = str(result.inserted_id)
        return member

    async def update(self, member: WardMember) -> WardMember:
        doc = map_ward_member_to_db(member)
        await db.db.ward_members.replace_one({"_id": ObjectId(member.id)}, doc)
        return member

    async def get_verified_members_by_ward(self, ward_id: str) -> List[WardMember]:
        if not ward_id:
            return []
        try:
            oid = ObjectId(ward_id) if not isinstance(ward_id, ObjectId) else ward_id
            docs = await db.db.ward_members.find({
                "ward_id": {"$in": [oid, str(oid)]},
                "is_verified": True
            }).to_list(length=100)
            return [map_ward_member_to_entity(doc) for doc in docs]
        except Exception:
            return []

    async def search_members(self, filters: dict, limit: int = 10) -> List[WardMember]:
        query = {}
        for k, v in filters.items():
            if v:
                query[k] = v
        docs = await db.db.ward_members.find(query).limit(limit).to_list(length=limit)
        return [map_ward_member_to_entity(doc) for doc in docs]

    async def list_all(self) -> List[WardMember]:
        docs = await db.db.ward_members.find({}).to_list(length=10000)
        return [map_ward_member_to_entity(doc) for doc in docs]

    async def get_members_by_ward(self, ward_id: str) -> List[WardMember]:
        if not ward_id:
            return []
        try:
            oid = ObjectId(ward_id) if not isinstance(ward_id, ObjectId) else ward_id
            docs = await db.db.ward_members.find({
                "ward_id": {"$in": [oid, str(oid)]}
            }).to_list(length=100)
            return [map_ward_member_to_entity(doc) for doc in docs]
        except Exception:
            return []


class MongoWardBloodAlertRepository(WardBloodAlertRepository):
    async def get_by_id(self, alert_id: str) -> Optional[WardBloodAlert]:
        try:
            doc = await db.db.ward_blood_alerts.find_one({"_id": ObjectId(alert_id)})
            return map_alert_to_entity(doc) if doc else None
        except Exception:
            return None

    async def create(self, alert: WardBloodAlert) -> WardBloodAlert:
        doc = map_alert_to_db(alert)
        result = await db.db.ward_blood_alerts.insert_one(doc)
        alert.id = str(result.inserted_id)
        return alert

    async def update(self, alert: WardBloodAlert) -> WardBloodAlert:
        doc = map_alert_to_db(alert)
        await db.db.ward_blood_alerts.replace_one({"_id": ObjectId(alert.id)}, doc)
        return alert

    async def get_or_create(self, ward_member_id: str, blood_request_id: str, defaults: dict) -> tuple[WardBloodAlert, bool]:
        query = {
            "ward_member_id": ObjectId(ward_member_id),
            "blood_request_id": ObjectId(blood_request_id) if blood_request_id else None
        }
        doc = await db.db.ward_blood_alerts.find_one(query)
        if doc:
            return map_alert_to_entity(doc), False
            
        new_data = query.copy()
        new_data.update(defaults)
        
        # Build alert entity
        alert = WardBloodAlert(
            ward_member_id=ward_member_id,
            blood_request_id=blood_request_id,
            blood_group=new_data.get("blood_group", ""),
            urgency=new_data.get("urgency", "normal"),
            patient_name=new_data.get("patient_name", ""),
            patient_condition=new_data.get("patient_condition", ""),
            hospital_name=new_data.get("hospital_name", ""),
            hospital_phone=new_data.get("hospital_phone", ""),
            hospital_whatsapp=new_data.get("hospital_whatsapp", ""),
            hospital_latitude=new_data.get("hospital_latitude"),
            hospital_longitude=new_data.get("hospital_longitude"),
            hospital_message=new_data.get("hospital_message", ""),
            bystander_phone=new_data.get("bystander_phone", ""),
            status=new_data.get("status", "pending")
        )
        
        db_doc = map_alert_to_db(alert)
        result = await db.db.ward_blood_alerts.insert_one(db_doc)
        alert.id = str(result.inserted_id)
        return alert, True

    async def list_by_member(self, ward_member_id: str, status: Optional[str] = None) -> List[WardBloodAlert]:
        query = {"ward_member_id": ObjectId(ward_member_id)}
        if status:
            query["status"] = status
        docs = await db.db.ward_blood_alerts.find(query).sort("created_at", -1).to_list(length=500)
        return [map_alert_to_entity(doc) for doc in docs]

    async def get_by_blood_request_id(self, request_id: str) -> Optional[WardBloodAlert]:
        try:
            doc = await db.db.ward_blood_alerts.find_one({"blood_request_id": ObjectId(request_id)})
            return map_alert_to_entity(doc) if doc else None
        except Exception:
            return None


class MongoWardDonorNotificationRepository(WardDonorNotificationRepository):
    async def get_or_create(self, alert_id: str, donor_id: str, defaults: dict) -> tuple[WardDonorNotification, bool]:
        query = {
            "alert_id": ObjectId(alert_id),
            "donor_id": ObjectId(donor_id)
        }
        doc = await db.db.ward_donor_notifications.find_one(query)
        if doc:
            return map_notif_to_entity(doc), False
            
        new_data = query.copy()
        new_data.update(defaults)
        
        notif = WardDonorNotification(
            alert_id=alert_id,
            donor_id=donor_id,
            status=new_data.get("status", "pending"),
            notes=new_data.get("notes", ""),
            contacted_at=new_data.get("contacted_at")
        )
        
        db_doc = map_notif_to_db(notif)
        result = await db.db.ward_donor_notifications.insert_one(db_doc)
        notif.id = str(result.inserted_id)
        return notif, True

    async def list_by_alert(self, alert_id: str) -> List[WardDonorNotification]:
        docs = await db.db.ward_donor_notifications.find({"alert_id": ObjectId(alert_id)}).sort("created_at", -1).to_list(length=1000)
        return [map_notif_to_entity(doc) for doc in docs]

    async def update(self, notif: WardDonorNotification) -> WardDonorNotification:
        doc = map_notif_to_db(notif)
        await db.db.ward_donor_notifications.replace_one({"_id": ObjectId(notif.id)}, doc)
        return notif
