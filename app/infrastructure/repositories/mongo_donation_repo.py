from typing import Optional, List, Dict
from datetime import datetime
from bson import ObjectId
from app.infrastructure.database.mongodb import db
from app.domain.entities.donation import (
    BloodRequest, DonationResponse, DonationRecord,
    ChatMessage, DonorRating, DonorBadge, BloodCamp,
    CampRegistration, Notification
)
from app.domain.repositories.donation_repo import (
    BloodRequestRepository, DonationResponseRepository, DonationRecordRepository,
    ChatMessageRepository, DonorRatingRepository, DonorBadgeRepository,
    BloodCampRepository, CampRegistrationRepository, NotificationRepository
)

# ─── BloodRequest Mappers ───
def map_request_to_entity(doc: dict) -> BloodRequest:
    return BloodRequest(
        id=str(doc["_id"]),
        hospital_id=str(doc.get("hospital_id", "")),
        blood_group=doc.get("blood_group", ""),
        units_needed=doc.get("units_needed", 1),
        urgency=doc.get("urgency", "normal"),
        note=doc.get("note", ""),
        patient_name=doc.get("patient_name", ""),
        patient_age=doc.get("patient_age"),
        patient_condition=doc.get("patient_condition", ""),
        patient_ward=doc.get("patient_ward", ""),
        patient_room=doc.get("patient_room", ""),
        patient_bed=doc.get("patient_bed", ""),
        ward_contact_person=doc.get("ward_contact_person", ""),
        ward_contact_phone=doc.get("ward_contact_phone", ""),
        bystander_name=doc.get("bystander_name", ""),
        bystander_phone=doc.get("bystander_phone", ""),
        patient_state=doc.get("patient_state", ""),
        patient_district=doc.get("patient_district", ""),
        patient_local_body_type=doc.get("patient_local_body_type", ""),
        patient_local_body_name=doc.get("patient_local_body_name", ""),
        patient_ward_number=doc.get("patient_ward_number", ""),
        hospital_latitude=doc.get("hospital_latitude"),
        hospital_longitude=doc.get("hospital_longitude"),
        status=doc.get("status", "pending"),
        search_radius_km=doc.get("search_radius_km", 50),
        is_emergency_broadcast=doc.get("is_emergency_broadcast", False),
        notify_ward_members=doc.get("notify_ward_members", False),
        ward_member_message=doc.get("ward_member_message", ""),
        target_ward_id=str(doc.get("target_ward_id")) if doc.get("target_ward_id") else None,
        confirmed_donors_count=doc.get("confirmed_donors_count", 0),
        completed_donations_count=doc.get("completed_donations_count", 0),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow()),
        expires_at=doc.get("expires_at")
    )

def map_request_to_db(entity: BloodRequest) -> dict:
    data = {
        "hospital_id": ObjectId(entity.hospital_id) if entity.hospital_id else "",
        "blood_group": entity.blood_group,
        "units_needed": entity.units_needed,
        "urgency": entity.urgency,
        "note": entity.note,
        "patient_name": entity.patient_name,
        "patient_age": entity.patient_age,
        "patient_condition": entity.patient_condition,
        "patient_ward": entity.patient_ward,
        "patient_room": entity.patient_room,
        "patient_bed": entity.patient_bed,
        "ward_contact_person": entity.ward_contact_person,
        "ward_contact_phone": entity.ward_contact_phone,
        "bystander_name": entity.bystander_name,
        "bystander_phone": entity.bystander_phone,
        "patient_state": entity.patient_state,
        "patient_district": entity.patient_district,
        "patient_local_body_type": entity.patient_local_body_type,
        "patient_local_body_name": entity.patient_local_body_name,
        "patient_ward_number": entity.patient_ward_number,
        "hospital_latitude": entity.hospital_latitude,
        "hospital_longitude": entity.hospital_longitude,
        "status": entity.status,
        "search_radius_km": entity.search_radius_km,
        "is_emergency_broadcast": entity.is_emergency_broadcast,
        "notify_ward_members": entity.notify_ward_members,
        "ward_member_message": entity.ward_member_message,
        "target_ward_id": ObjectId(entity.target_ward_id) if entity.target_ward_id else None,
        "confirmed_donors_count": entity.confirmed_donors_count,
        "completed_donations_count": entity.completed_donations_count,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at,
        "expires_at": entity.expires_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── DonationResponse Mappers ───
def map_response_to_entity(doc: dict) -> DonationResponse:
    return DonationResponse(
        id=str(doc["_id"]),
        request_id=str(doc.get("request_id", "")),
        donor_id=str(doc.get("donor_id", "")),
        status=doc.get("status", "pending"),
        eta_minutes=doc.get("eta_minutes"),
        donor_latitude=doc.get("donor_latitude"),
        donor_longitude=doc.get("donor_longitude"),
        distance_km=doc.get("distance_km"),
        notification_sent_at=doc.get("notification_sent_at"),
        responded_at=doc.get("responded_at"),
        rejection_reason=doc.get("rejection_reason", ""),
        arrived_at=doc.get("arrived_at"),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow())
    )

def map_response_to_db(entity: DonationResponse) -> dict:
    data = {
        "request_id": ObjectId(entity.request_id) if entity.request_id else "",
        "donor_id": ObjectId(entity.donor_id) if entity.donor_id else "",
        "status": entity.status,
        "eta_minutes": entity.eta_minutes,
        "donor_latitude": entity.donor_latitude,
        "donor_longitude": entity.donor_longitude,
        "distance_km": entity.distance_km,
        "notification_sent_at": entity.notification_sent_at,
        "responded_at": entity.responded_at,
        "rejection_reason": entity.rejection_reason,
        "arrived_at": entity.arrived_at,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── DonationRecord Mappers ───
def map_record_to_entity(doc: dict) -> DonationRecord:
    return DonationRecord(
        id=str(doc["_id"]),
        donor_id=str(doc.get("donor_id", "")),
        request_id=str(doc.get("request_id")) if doc.get("request_id") else None,
        response_id=str(doc.get("response_id")) if doc.get("response_id") else None,
        blood_group=doc.get("blood_group", ""),
        units_donated=doc.get("units_donated", 1),
        donated_at=doc.get("donated_at", datetime.utcnow()),
        hospital_name=doc.get("hospital_name", ""),
        hospital_city=doc.get("hospital_city", ""),
        cooldown_until=doc.get("cooldown_until"),
        notes=doc.get("notes", ""),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_record_to_db(entity: DonationRecord) -> dict:
    data = {
        "donor_id": ObjectId(entity.donor_id) if entity.donor_id else "",
        "request_id": ObjectId(entity.request_id) if entity.request_id else None,
        "response_id": ObjectId(entity.response_id) if entity.response_id else None,
        "blood_group": entity.blood_group,
        "units_donated": entity.units_donated,
        "donated_at": entity.donated_at,
        "hospital_name": entity.hospital_name,
        "hospital_city": entity.hospital_city,
        "cooldown_until": entity.cooldown_until,
        "notes": entity.notes,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── ChatMessage Mappers ───
def map_chat_to_entity(doc: dict) -> ChatMessage:
    return ChatMessage(
        id=str(doc["_id"]),
        response_id=str(doc.get("response_id", "")),
        sender_id=str(doc.get("sender_id", "")),
        message=doc.get("message", ""),
        is_read=doc.get("is_read", False),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_chat_to_db(entity: ChatMessage) -> dict:
    data = {
        "response_id": ObjectId(entity.response_id) if entity.response_id else "",
        "sender_id": ObjectId(entity.sender_id) if entity.sender_id else "",
        "message": entity.message,
        "is_read": entity.is_read,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── DonorRating Mappers ───
def map_rating_to_entity(doc: dict) -> DonorRating:
    return DonorRating(
        id=str(doc["_id"]),
        record_id=str(doc.get("record_id")) if doc.get("record_id") else None,
        donor_id=str(doc.get("donor_id", "")),
        rated_by=str(doc.get("rated_by", "")),
        stars=doc.get("stars", 5),
        punctuality=doc.get("punctuality", ""),
        fitness=doc.get("fitness", ""),
        feedback=doc.get("feedback", ""),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_rating_to_db(entity: DonorRating) -> dict:
    data = {
        "record_id": ObjectId(entity.record_id) if entity.record_id else None,
        "donor_id": ObjectId(entity.donor_id) if entity.donor_id else "",
        "rated_by": ObjectId(entity.rated_by) if entity.rated_by else "",
        "stars": entity.stars,
        "punctuality": entity.punctuality,
        "fitness": entity.fitness,
        "feedback": entity.feedback,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── DonorBadge Mappers ───
def map_badge_to_entity(doc: dict) -> DonorBadge:
    return DonorBadge(
        id=str(doc["_id"]),
        donor_id=str(doc.get("donor_id", "")),
        badge=doc.get("badge", ""),
        earned_at=doc.get("earned_at", datetime.utcnow())
    )

def map_badge_to_db(entity: DonorBadge) -> dict:
    data = {
        "donor_id": ObjectId(entity.donor_id) if entity.donor_id else "",
        "badge": entity.badge,
        "earned_at": entity.earned_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── BloodCamp Mappers ───
def map_camp_to_entity(doc: dict) -> BloodCamp:
    loc = doc.get("location")
    lat, lng = None, None
    if loc and loc.get("type") == "Point":
        coords = loc.get("coordinates")
        if coords and len(coords) == 2:
            lng, lat = coords[0], coords[1]
            
    # Safely convert scheduled_date
    sched = doc.get("scheduled_date")
    s_date = date.today()
    if sched:
        if isinstance(sched, datetime):
            s_date = sched.date()
        elif isinstance(sched, date):
            s_date = sched
        elif isinstance(sched, str):
            try:
                s_date = datetime.strptime(sched.split("T")[0], "%Y-%m-%d").date()
            except ValueError:
                pass

    return BloodCamp(
        id=str(doc["_id"]),
        hospital_id=str(doc.get("hospital_id", "")),
        title=doc.get("title", ""),
        description=doc.get("description", ""),
        location=doc.get("location_name", ""),
        city=doc.get("city", ""),
        state=doc.get("state", ""),
        latitude=lat,
        longitude=lng,
        scheduled_date=s_date,
        start_time=doc.get("start_time", ""),
        end_time=doc.get("end_time", ""),
        capacity=doc.get("capacity", 50),
        target_blood_groups=doc.get("target_blood_groups", ""),
        is_active=doc.get("is_active", True),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_camp_to_db(entity: BloodCamp) -> dict:
    s_date = entity.scheduled_date
    if s_date and isinstance(s_date, date) and not isinstance(s_date, datetime):
        s_date = datetime(s_date.year, s_date.month, s_date.day)
        
    data = {
        "hospital_id": ObjectId(entity.hospital_id) if entity.hospital_id else "",
        "title": entity.title,
        "description": entity.description,
        "location_name": entity.location,
        "city": entity.city,
        "state": entity.state,
        "scheduled_date": s_date,
        "start_time": entity.start_time,
        "end_time": entity.end_time,
        "capacity": entity.capacity,
        "target_blood_groups": entity.target_blood_groups,
        "is_active": entity.is_active,
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


# ─── CampRegistration Mappers ───
def map_reg_to_entity(doc: dict) -> CampRegistration:
    return CampRegistration(
        id=str(doc["_id"]),
        camp_id=str(doc.get("camp_id", "")),
        donor_id=str(doc.get("donor_id", "")),
        status=doc.get("status", "registered"),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow())
    )

def map_reg_to_db(entity: CampRegistration) -> dict:
    data = {
        "camp_id": ObjectId(entity.camp_id) if entity.camp_id else "",
        "donor_id": ObjectId(entity.donor_id) if entity.donor_id else "",
        "status": entity.status,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── Notification Mappers ───
def map_notification_to_entity(doc: dict) -> Notification:
    return Notification(
        id=str(doc["_id"]),
        recipient_id=str(doc.get("recipient_id", "")),
        request_id=str(doc.get("request_id")) if doc.get("request_id") else None,
        channel=doc.get("channel", "push"),
        subject=doc.get("subject", ""),
        body=doc.get("body", ""),
        status=doc.get("status", "pending"),
        error_message=doc.get("error_message", ""),
        sent_at=doc.get("sent_at"),
        created_at=doc.get("created_at", datetime.utcnow())
    )

def map_notification_to_db(entity: Notification) -> dict:
    data = {
        "recipient_id": ObjectId(entity.recipient_id) if entity.recipient_id else "",
        "request_id": ObjectId(entity.request_id) if entity.request_id else None,
        "channel": entity.channel,
        "subject": entity.subject,
        "body": entity.body,
        "status": entity.status,
        "error_message": entity.error_message,
        "sent_at": entity.sent_at,
        "created_at": entity.created_at
    }
    if entity.id:
        data["_id"] = ObjectId(entity.id)
    return data


# ─── MongoDB Repository Classes ───

class MongoBloodRequestRepository(BloodRequestRepository):
    async def get_by_id(self, request_id: str) -> Optional[BloodRequest]:
        try:
            doc = await db.db.blood_requests.find_one({"_id": ObjectId(request_id)})
            return map_request_to_entity(doc) if doc else None
        except Exception:
            return None

    async def create(self, request: BloodRequest) -> BloodRequest:
        doc = map_request_to_db(request)
        result = await db.db.blood_requests.insert_one(doc)
        request.id = str(result.inserted_id)
        return request

    async def update(self, request: BloodRequest) -> BloodRequest:
        request.updated_at = datetime.utcnow()
        doc = map_request_to_db(request)
        await db.db.blood_requests.replace_one({"_id": ObjectId(request.id)}, doc)
        return request

    async def list_by_hospital(self, hospital_id: str, status: Optional[str] = None) -> List[BloodRequest]:
        query = {"hospital_id": ObjectId(hospital_id)}
        if status:
            query["status"] = status
        docs = await db.db.blood_requests.find(query).sort("created_at", -1).to_list(length=500)
        return [map_request_to_entity(doc) for doc in docs]

    async def delete_completed_or_cancelled(self, hospital_id: str) -> int:
        result = await db.db.blood_requests.delete_many({
            "hospital_id": ObjectId(hospital_id),
            "status": {"$in": ["completed", "cancelled"]}
        })
        return result.deleted_count

    async def clear_hospital_data(self, hospital_id: str) -> int:
        requests = await db.db.blood_requests.find({"hospital_id": ObjectId(hospital_id)}).to_list(length=1000)
        request_ids = [ObjectId(r["_id"]) for r in requests]
        
        # Responses to delete
        responses = await db.db.donation_responses.find({"request_id": {"$in": request_ids}}).to_list(length=5000)
        response_ids = [ObjectId(res["_id"]) for res in responses]
        
        # Delete chats
        if response_ids:
            await db.db.chat_messages.delete_many({"response_id": {"$in": response_ids}})
            
        # Delete ward alerts/notifications linked to these requests
        await db.db.ward_donor_notifications.delete_many({"alert_id": {"$in": request_ids}})
        await db.db.ward_blood_alerts.delete_many({"blood_request_id": {"$in": request_ids}})
        
        # Delete responses
        await db.db.donation_responses.delete_many({"request_id": {"$in": request_ids}})
        
        # Delete records
        await db.db.donation_records.delete_many({"request_id": {"$in": request_ids}})
        
        # Delete requests
        result = await db.db.blood_requests.delete_many({"hospital_id": ObjectId(hospital_id)})
        return result.deleted_count


class MongoDonationResponseRepository(DonationResponseRepository):
    async def get_by_id(self, response_id: str) -> Optional[DonationResponse]:
        try:
            doc = await db.db.donation_responses.find_one({"_id": ObjectId(response_id)})
            return map_response_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_or_create(self, request_id: str, donor_id: str, defaults: dict) -> tuple[DonationResponse, bool]:
        query = {
            "request_id": ObjectId(request_id),
            "donor_id": ObjectId(donor_id)
        }
        doc = await db.db.donation_responses.find_one(query)
        if doc:
            return map_response_to_entity(doc), False
            
        new_data = query.copy()
        new_data.update(defaults)
        
        resp = DonationResponse(
            request_id=request_id,
            donor_id=donor_id,
            status=new_data.get("status", "pending"),
            eta_minutes=new_data.get("eta_minutes"),
            donor_latitude=new_data.get("donor_latitude"),
            donor_longitude=new_data.get("donor_longitude"),
            distance_km=new_data.get("distance_km"),
            notification_sent_at=new_data.get("notification_sent_at"),
            responded_at=new_data.get("responded_at"),
            rejection_reason=new_data.get("rejection_reason", ""),
            arrived_at=new_data.get("arrived_at")
        )
        
        db_doc = map_response_to_db(resp)
        result = await db.db.donation_responses.insert_one(db_doc)
        resp.id = str(result.inserted_id)
        return resp, True

    async def update(self, response: DonationResponse) -> DonationResponse:
        response.updated_at = datetime.utcnow()
        doc = map_response_to_db(response)
        await db.db.donation_responses.replace_one({"_id": ObjectId(response.id)}, doc)
        return response

    async def list_pending_for_donor(self, donor_id: str) -> List[DonationResponse]:
        # Pending responses for active requests
        active_requests = await db.db.blood_requests.find({
            "status": {"$in": ["pending", "active"]}
        }).to_list(length=1000)
        request_ids = [ObjectId(r["_id"]) for r in active_requests]
        
        query = {
            "donor_id": ObjectId(donor_id),
            "status": "pending",
            "request_id": {"$in": request_ids}
        }
        docs = await db.db.donation_responses.find(query).sort("created_at", -1).to_list(length=100)
        return [map_response_to_entity(doc) for doc in docs]

    async def list_by_request(self, request_id: str, status_in: Optional[List[str]] = None) -> List[DonationResponse]:
        query = {"request_id": ObjectId(request_id)}
        if status_in:
            query["status"] = {"$in": status_in}
        docs = await db.db.donation_responses.find(query).sort("created_at", 1).to_list(length=1000)
        return [map_response_to_entity(doc) for doc in docs]

    async def list_history_for_donor(self, donor_id: str) -> List[DonationResponse]:
        docs = await db.db.donation_responses.find({
            "donor_id": ObjectId(donor_id)
        }).sort("created_at", -1).to_list(length=500)
        return [map_response_to_entity(doc) for doc in docs]

    async def update_status_by_query(self, query: dict, new_status: str) -> int:
        mongo_query = {}
        for k, v in query.items():
            if k in ("request_id", "donor_id", "id"):
                if isinstance(v, list):
                    mongo_query[k if k != "id" else "_id"] = {"$in": [ObjectId(x) for x in v]}
                else:
                    mongo_query[k if k != "id" else "_id"] = ObjectId(v)
            else:
                mongo_query[k] = v
                
        result = await db.db.donation_responses.update_many(
            mongo_query,
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count


class MongoDonationRecordRepository(DonationRecordRepository):
    async def create(self, record: DonationRecord) -> DonationRecord:
        doc = map_record_to_db(record)
        result = await db.db.donation_records.insert_one(doc)
        record.id = str(result.inserted_id)
        return record

    async def get_by_id(self, record_id: str) -> Optional[DonationRecord]:
        try:
            doc = await db.db.donation_records.find_one({"_id": ObjectId(record_id)})
            return map_record_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_last_for_donor(self, donor_id: str) -> Optional[DonationRecord]:
        doc = await db.db.donation_records.find_one(
            {"donor_id": ObjectId(donor_id)},
            sort=[("donated_at", -1)]
        )
        return map_record_to_entity(doc) if doc else None

    async def list_by_donor(self, donor_id: str) -> List[DonationRecord]:
        docs = await db.db.donation_records.find({
            "donor_id": ObjectId(donor_id)
        }).sort("donated_at", -1).to_list(length=500)
        return [map_record_to_entity(doc) for doc in docs]

    async def count_by_donor(self, donor_id: str) -> int:
        return await db.db.donation_records.count_documents({"donor_id": ObjectId(donor_id)})

    async def count_by_hospital(self, hospital_id: str, since: Optional[datetime] = None) -> int:
        # Match records linked to requests created by hospital
        reqs = await db.db.blood_requests.find({"hospital_id": ObjectId(hospital_id)}).to_list(length=5000)
        req_ids = [ObjectId(r["_id"]) for r in reqs]
        
        query = {"request_id": {"$in": req_ids}}
        if since:
            query["donated_at"] = {"$gte": since}
            
        return await db.db.donation_records.count_documents(query)

    async def get_success_rate_and_breakdowns(self, hospital_id: str) -> dict:
        req_count = await db.db.blood_requests.count_documents({"hospital_id": ObjectId(hospital_id)})
        
        reqs = await db.db.blood_requests.find({"hospital_id": ObjectId(hospital_id)}).to_list(length=5000)
        req_ids = [ObjectId(r["_id"]) for r in reqs]
        
        rec_count = await db.db.donation_records.count_documents({"request_id": {"$in": req_ids}})
        
        # Blood Group breakdown
        pipeline_bg = [
            {"$match": {"request_id": {"$in": req_ids}}},
            {"$group": {"_id": "$blood_group", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        bg_cursor = db.db.donation_records.aggregate(pipeline_bg)
        bg_list = await bg_cursor.to_list(length=50)
        bg_breakdown = [{"blood_group": x["_id"], "count": x["count"]} for x in bg_list]
        
        # Urgency breakdown
        pipeline_urg = [
            {"$match": {"hospital_id": ObjectId(hospital_id)}},
            {"$group": {"_id": "$urgency", "count": {"$sum": 1}}}
        ]
        urg_cursor = db.db.blood_requests.aggregate(pipeline_urg)
        urg_list = await urg_cursor.to_list(length=10)
        urg_breakdown = [{"urgency": x["_id"], "count": x["count"]} for x in urg_list]
        
        # Status breakdown
        pipeline_stat = [
            {"$match": {"hospital_id": ObjectId(hospital_id)}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        stat_cursor = db.db.blood_requests.aggregate(pipeline_stat)
        stat_list = await stat_cursor.to_list(length=10)
        stat_breakdown = [{"status": x["_id"], "count": x["count"]} for x in stat_list]
        
        return {
            "total_requests": req_count,
            "completed_donations": rec_count,
            "success_rate_percent": round((rec_count / req_count * 100), 1) if req_count else 0,
            "by_blood_group": bg_breakdown,
            "by_urgency": urg_breakdown,
            "by_status": stat_breakdown
        }


class MongoChatMessageRepository(ChatMessageRepository):
    async def create(self, msg: ChatMessage) -> ChatMessage:
        doc = map_chat_to_db(msg)
        result = await db.db.chat_messages.insert_one(doc)
        msg.id = str(result.inserted_id)
        return msg

    async def list_by_response(self, response_id: str) -> List[ChatMessage]:
        docs = await db.db.chat_messages.find({
            "response_id": ObjectId(response_id)
        }).sort("created_at", 1).to_list(length=1000)
        return [map_chat_to_entity(doc) for doc in docs]

    async def mark_incoming_as_read(self, response_id: str, reader_id: str) -> int:
        result = await db.db.chat_messages.update_many(
            {
                "response_id": ObjectId(response_id),
                "sender_id": {"$ne": ObjectId(reader_id)},
                "is_read": False
            },
            {"$set": {"is_read": True}}
        )
        return result.modified_count

    async def get_unread_counts(self, response_ids: List[str], reader_id: str) -> Dict[str, int]:
        obj_ids = [ObjectId(rid) for rid in response_ids]
        pipeline = [
            {
                "$match": {
                    "response_id": {"$in": obj_ids},
                    "sender_id": {"$ne": ObjectId(reader_id)},
                    "is_read": False
                }
            },
            {"$group": {"_id": "$response_id", "unread": {"$sum": 1}}}
        ]
        cursor = db.db.chat_messages.aggregate(pipeline)
        res_list = await cursor.to_list(length=len(response_ids) + 10)
        return {str(x["_id"]): x["unread"] for x in res_list}

    async def delete_by_responses(self, response_ids: List[str]) -> int:
        obj_ids = [ObjectId(rid) for rid in response_ids]
        result = await db.db.chat_messages.delete_many({"response_id": {"$in": obj_ids}})
        return result.deleted_count


class MongoDonorRatingRepository(DonorRatingRepository):
    async def create(self, rating: DonorRating) -> DonorRating:
        doc = map_rating_to_db(rating)
        result = await db.db.donor_ratings.insert_one(doc)
        rating.id = str(result.inserted_id)
        return rating

    async def get_by_record_id(self, record_id: str) -> Optional[DonorRating]:
        try:
            doc = await db.db.donor_ratings.find_one({"record_id": ObjectId(record_id)})
            return map_rating_to_entity(doc) if doc else None
        except Exception:
            return None

    async def get_avg_rating_for_donor(self, donor_id: str) -> Optional[float]:
        pipeline = [
            {"$match": {"donor_id": ObjectId(donor_id)}},
            {"$group": {"_id": None, "avg": {"$avg": "$stars"}}}
        ]
        cursor = db.db.donor_ratings.aggregate(pipeline)
        res = await cursor.to_list(length=1)
        return res[0]["avg"] if res else None

    async def get_avg_rating_given_by_hospital(self, hospital_id: str) -> Optional[float]:
        pipeline = [
            {"$match": {"rated_by": ObjectId(hospital_id)}},
            {"$group": {"_id": None, "avg": {"$avg": "$stars"}}}
        ]
        cursor = db.db.donor_ratings.aggregate(pipeline)
        res = await cursor.to_list(length=1)
        return res[0]["avg"] if res else None


class MongoDonorBadgeRepository(DonorBadgeRepository):
    async def create(self, badge: DonorBadge) -> DonorBadge:
        doc = map_badge_to_db(badge)
        result = await db.db.donor_badges.insert_one(doc)
        badge.id = str(result.inserted_id)
        return badge

    async def get_or_create(self, donor_id: str, badge: str) -> tuple[DonorBadge, bool]:
        query = {
            "donor_id": ObjectId(donor_id),
            "badge": badge
        }
        doc = await db.db.donor_badges.find_one(query)
        if doc:
            return map_badge_to_entity(doc), False
            
        badge_ent = DonorBadge(donor_id=donor_id, badge=badge)
        db_doc = map_badge_to_db(badge_ent)
        result = await db.db.donor_badges.insert_one(db_doc)
        badge_ent.id = str(result.inserted_id)
        return badge_ent, True

    async def list_by_donor(self, donor_id: str) -> List[DonorBadge]:
        docs = await db.db.donor_badges.find({"donor_id": ObjectId(donor_id)}).sort("earned_at", -1).to_list(length=100)
        return [map_badge_to_entity(doc) for doc in docs]


class MongoBloodCampRepository(BloodCampRepository):
    async def create(self, camp: BloodCamp) -> BloodCamp:
        doc = map_camp_to_db(camp)
        result = await db.db.blood_camps.insert_one(doc)
        camp.id = str(result.inserted_id)
        return camp

    async def get_by_id(self, camp_id: str) -> Optional[BloodCamp]:
        try:
            doc = await db.db.blood_camps.find_one({"_id": ObjectId(camp_id)})
            return map_camp_to_entity(doc) if doc else None
        except Exception:
            return None

    async def list_active_camps(self, city: Optional[str] = None, blood_group: Optional[str] = None) -> List[BloodCamp]:
        # Filter active camps scheduled for today or later
        today_dt = datetime.combine(date.today(), datetime.min.time())
        query = {
            "is_active": True,
            "scheduled_date": {"$gte": today_dt}
        }
        if city:
            query["city"] = {"$regex": f"^{city}$", "$options": "i"}
            
        docs = await db.db.blood_camps.find(query).sort("scheduled_date", 1).to_list(length=200)
        camps = [map_camp_to_entity(doc) for doc in docs]
        
        # If target blood group requested, filter by matching target groups (comma separated or empty for all)
        if blood_group:
            bg_lower = blood_group.lower().strip()
            filtered = []
            for c in camps:
                if not c.target_blood_groups:
                    filtered.append(c)
                else:
                    groups = [x.strip().lower() for x in c.target_blood_groups.split(",")]
                    if bg_lower in groups:
                        filtered.append(c)
            return filtered
            
        return camps

    async def list_by_hospital(self, hospital_id: str) -> List[BloodCamp]:
        docs = await db.db.blood_camps.find({"hospital_id": ObjectId(hospital_id)}).sort("scheduled_date", -1).to_list(length=200)
        return [map_camp_to_entity(doc) for doc in docs]


class MongoCampRegistrationRepository(CampRegistrationRepository):
    async def get_or_create(self, camp_id: str, donor_id: str, defaults: dict) -> tuple[CampRegistration, bool]:
        query = {
            "camp_id": ObjectId(camp_id),
            "donor_id": ObjectId(donor_id)
        }
        doc = await db.db.camp_registrations.find_one(query)
        if doc:
            return map_reg_to_entity(doc), False
            
        new_data = query.copy()
        new_data.update(defaults)
        
        reg = CampRegistration(
            camp_id=camp_id,
            donor_id=donor_id,
            status=new_data.get("status", "registered")
        )
        db_doc = map_reg_to_db(reg)
        result = await db.db.camp_registrations.insert_one(db_doc)
        reg.id = str(result.inserted_id)
        return reg, True

    async def get_by_camp_and_donor(self, camp_id: str, donor_id: str) -> Optional[CampRegistration]:
        try:
            doc = await db.db.camp_registrations.find_one({
                "camp_id": ObjectId(camp_id),
                "donor_id": ObjectId(donor_id)
            })
            return map_reg_to_entity(doc) if doc else None
        except Exception:
            return None

    async def update(self, reg: CampRegistration) -> CampRegistration:
        reg.updated_at = datetime.utcnow()
        doc = map_reg_to_db(reg)
        await db.db.camp_registrations.replace_one({"_id": ObjectId(reg.id)}, doc)
        return reg

    async def count_active_by_camp(self, camp_id: str) -> int:
        return await db.db.camp_registrations.count_documents({
            "camp_id": ObjectId(camp_id),
            "status": "registered"
        })

    async def list_by_donor(self, donor_id: str) -> List[CampRegistration]:
        docs = await db.db.camp_registrations.find({
            "donor_id": ObjectId(donor_id)
        }).sort("created_at", -1).to_list(length=100)
        return [map_reg_to_entity(doc) for doc in docs]


class MongoNotificationRepository(NotificationRepository):
    async def create(self, notif: Notification) -> Notification:
        doc = map_notification_to_db(notif)
        result = await db.db.notifications.insert_one(doc)
        notif.id = str(result.inserted_id)
        return notif

    async def list_by_recipient(self, recipient_id: str) -> List[Notification]:
        docs = await db.db.notifications.find({
            "recipient_id": ObjectId(recipient_id)
        }).sort("created_at", -1).to_list(length=500)
        return [map_notification_to_entity(doc) for doc in docs]
