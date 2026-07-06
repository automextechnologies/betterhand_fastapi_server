from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass
class Ward:
    id: Optional[str] = None
    ward_number: str = ""
    local_body_name: str = ""
    local_body_type: str = "Gram Panchayat"
    district: str = ""
    state: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class WardMember:
    id: Optional[str] = None
    user_id: str = ""
    ward_id: str = ""
    full_name: str = ""
    phone: str = ""
    designation: str = ""
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class WardBloodAlert:
    id: Optional[str] = None
    ward_member_id: str = ""
    blood_request_id: Optional[str] = None
    blood_group: str = ""
    urgency: str = "normal"  # "normal", "urgent", "critical"
    patient_name: str = ""
    patient_condition: str = ""
    hospital_name: str = ""
    hospital_phone: str = ""
    hospital_whatsapp: str = ""
    hospital_latitude: Optional[float] = None
    hospital_longitude: Optional[float] = None
    hospital_message: str = ""
    bystander_phone: str = ""
    status: str = "pending"  # "pending", "notified", "resolved"
    resolved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class WardDonorNotification:
    id: Optional[str] = None
    alert_id: str = ""
    donor_id: str = ""
    status: str = "pending"  # "pending", "contacted", "interested", "not_available", "donated"
    notes: str = ""
    contacted_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
