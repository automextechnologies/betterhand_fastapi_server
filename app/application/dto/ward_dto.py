from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date

class WardMemberBasicResponse(BaseModel):
    id: str
    full_name: str
    phone: str
    designation: str
    is_verified: bool

class WardResponse(BaseModel):
    id: str
    ward_number: str
    local_body_name: str
    local_body_type: str
    district: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    members: List[WardMemberBasicResponse] = []

class WardMemberRegisterDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    phone: str
    designation: Optional[str] = ""
    ward_id: Optional[str] = None
    state: Optional[str] = ""
    district: Optional[str] = ""
    local_body_type: Optional[str] = ""
    local_body_name: Optional[str] = ""
    ward_number: Optional[str] = ""

class WardMemberProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str
    designation: str
    is_verified: bool
    ward: Optional[WardResponse] = None

class WardBloodAlertResponse(BaseModel):
    id: str
    blood_group: str
    urgency: str
    patient_name: str
    patient_condition: str
    hospital_name: str
    hospital_phone: str
    hospital_whatsapp: str
    bystander_phone: str
    hospital_latitude: Optional[float] = None
    hospital_longitude: Optional[float] = None
    hospital_message: str
    status: str
    ward_name: str
    ward_number: str
    member_name: str
    member_phone: str
    blood_request_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

class WardTopDonorDTO(BaseModel):
    donor_id: str
    full_name: str
    phone: str
    blood_group: str
    district: str
    local_body_name: str
    ward_number: str
    distance_km: float
    is_available: bool
    last_donated: Optional[date] = None
    on_cooldown: bool
    avg_rating: Optional[float] = None
    donation_count: int
    badges: List[str] = []
    whatsapp_link: Optional[str] = None

class WardDonorNotificationResponse(BaseModel):
    id: str
    donor_name: str
    donor_phone: str
    status: str
    notes: str
    contacted_at: Optional[datetime] = None
    created_at: datetime
