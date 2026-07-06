from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List

@dataclass
class BloodRequest:
    id: Optional[str] = None
    hospital_id: str = ""
    blood_group: str = ""
    units_needed: int = 1
    urgency: str = "normal"  # "normal", "urgent", "critical"
    note: str = ""
    
    # Patient details
    patient_name: str = ""
    patient_age: Optional[int] = None
    patient_condition: str = ""
    patient_ward: str = ""
    patient_room: str = ""
    patient_bed: str = ""
    ward_contact_person: str = ""
    ward_contact_phone: str = ""
    bystander_name: str = ""
    bystander_phone: str = ""
    
    # Patient HOME area
    patient_state: str = ""
    patient_district: str = ""
    patient_local_body_type: str = ""
    patient_local_body_name: str = ""
    patient_ward_number: str = ""
    
    # Hospital GPS snapshot
    hospital_latitude: Optional[float] = None
    hospital_longitude: Optional[float] = None
    
    # Settings
    status: str = "pending"  # "pending", "active", "confirmed", "completed", "cancelled", "expired"
    search_radius_km: int = 50
    is_emergency_broadcast: bool = False
    
    # Ward Mobilization
    notify_ward_members: bool = False
    ward_member_message: str = ""
    target_ward_id: Optional[str] = None
    
    # Completion tracking
    confirmed_donors_count: int = 0
    completed_donations_count: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

@dataclass
class DonationResponse:
    id: Optional[str] = None
    request_id: str = ""
    donor_id: str = ""
    status: str = "pending"  # "pending", "accepted", "rejected", "confirmed", "completed", "missed", "not_needed", "arrived_no_donation"
    eta_minutes: Optional[int] = None
    donor_latitude: Optional[float] = None
    donor_longitude: Optional[float] = None
    distance_km: Optional[float] = None
    notification_sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    rejection_reason: str = ""
    arrived_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DonationRecord:
    id: Optional[str] = None
    donor_id: str = ""
    request_id: Optional[str] = None
    response_id: Optional[str] = None
    blood_group: str = ""
    units_donated: int = 1
    donated_at: datetime = field(default_factory=datetime.utcnow)
    hospital_name: str = ""
    hospital_city: str = ""
    cooldown_until: Optional[datetime] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ChatMessage:
    id: Optional[str] = None
    response_id: str = ""
    sender_id: str = ""
    message: str = ""
    is_read: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DonorRating:
    id: Optional[str] = None
    record_id: Optional[str] = None
    donor_id: str = ""
    rated_by: str = ""  # Hospital User ID
    stars: int = 5
    punctuality: str = ""
    fitness: str = ""
    feedback: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DonorBadge:
    id: Optional[str] = None
    donor_id: str = ""
    badge: str = ""  # "first_drop", "lifesaver", "hero", "legend", "guardian", "top_rated"
    earned_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class BloodCamp:
    id: Optional[str] = None
    hospital_id: str = ""
    title: str = ""
    description: str = ""
    location: str = ""
    city: str = ""
    state: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scheduled_date: date = field(default_factory=date.today)
    start_time: str = "" # e.g. "09:00"
    end_time: str = ""   # e.g. "17:00"
    capacity: int = 50
    target_blood_groups: str = "" # e.g. "O+,O-,A+"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CampRegistration:
    id: Optional[str] = None
    camp_id: str = ""
    donor_id: str = ""
    status: str = "registered"  # "registered", "cancelled", "attended"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Notification:
    id: Optional[str] = None
    recipient_id: str = ""
    request_id: Optional[str] = None
    channel: str = "push"  # "push", "email", "both"
    subject: str = ""
    body: str = ""
    status: str = "pending"  # "sent", "failed", "pending"
    error_message: str = ""
    sent_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
