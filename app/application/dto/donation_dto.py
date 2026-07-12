from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime, date

# ─── Target Ward Info DTO ───
class TargetWardInfoDTO(BaseModel):
    ward_id: str
    ward_number: str
    local_body_name: str
    district: str
    state: str
    member_name: Optional[str] = None
    member_phone: Optional[str] = None

# ─── BloodRequest Creation & Responses ───
class BloodRequestCreateDTO(BaseModel):
    blood_group: str
    units_needed: int = 1
    urgency: str = "normal"  # "normal", "urgent", "critical"
    note: Optional[str] = ""
    patient_name: str
    patient_age: Optional[int] = None
    patient_condition: Optional[str] = ""
    patient_ward: Optional[str] = ""
    patient_room: Optional[str] = ""
    patient_bed: Optional[str] = ""
    ward_contact_person: Optional[str] = ""
    ward_contact_phone: Optional[str] = ""
    bystander_name: Optional[str] = ""
    bystander_phone: Optional[str] = ""
    patient_state: Optional[str] = ""
    patient_district: Optional[str] = ""
    patient_local_body_type: Optional[str] = ""
    patient_local_body_name: Optional[str] = ""
    patient_ward_number: Optional[str] = ""
    search_radius_km: Optional[int] = 50
    notify_ward_members: Optional[bool] = False
    ward_member_message: Optional[str] = ""
    ward_id: Optional[str] = None

class BloodRequestListResponse(BaseModel):
    id: str
    blood_group: str
    units_needed: int
    urgency: str
    status: str
    patient_name: str
    patient_age: Optional[int] = None
    patient_condition: str
    patient_ward: str
    patient_room: str
    patient_bed: str
    patient_state: str
    patient_district: str
    patient_local_body_type: str
    patient_local_body_name: str
    patient_ward_number: str
    bystander_name: str = ""
    bystander_phone: str = ""
    hospital_latitude: Optional[float] = None
    hospital_longitude: Optional[float] = None
    hospital_name: str
    confirmed_donors_count: int
    completed_donations_count: int
    accepted_count: int
    confirmed_count: int
    target_ward_info: Optional[TargetWardInfoDTO] = None
    search_radius_km: int
    notify_ward_members: bool
    ward_member_message: str
    created_at: datetime
    expires_at: Optional[datetime] = None

class DonationResponseSummary(BaseModel):
    id: str
    donor_name: str
    donor_phone: str
    donor_whatsapp: str
    blood_group: str
    donor_district: str
    donor_ward: str
    status: str
    eta_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    donor_latitude: Optional[float] = None
    donor_longitude: Optional[float] = None
    responded_at: Optional[datetime] = None
    avg_rating: Optional[float] = None
    total_donations: int
    acceptance_rate: Optional[float] = None

class BloodRequestDetailResponse(BloodRequestListResponse):
    responses: List[DonationResponseSummary] = []

class DonationResponseDonorView(BaseModel):
    id: str
    status: str
    eta_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    hospital_name: str
    hospital_phone: str
    hospital_whatsapp: str
    hospital_latitude: Optional[float] = None
    hospital_longitude: Optional[float] = None
    blood_group: str
    units_needed: int
    urgency: str
    patient_name: str
    patient_condition: str
    bystander_name: str
    bystander_phone: str
    via_ward: bool
    ward_member_name: Optional[str] = None
    ward_member_phone: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime

class DonationResponseCreateDTO(BaseModel):
    status: str  # "accepted" or "rejected"
    donor_latitude: Optional[float] = None
    donor_longitude: Optional[float] = None
    rejection_reason: Optional[str] = ""

# ─── DonationRecord DTOs ───
class DonorRatingResponse(BaseModel):
    id: str
    stars: int
    punctuality: str
    fitness: str
    feedback: str
    created_at: datetime

class DonationRecordDTO(BaseModel):
    id: str
    blood_group: str
    units_donated: int
    donated_at: datetime
    hospital_name: str
    hospital_city: str
    cooldown_until: Optional[datetime] = None
    is_on_cooldown: bool
    hospital_rating: Optional[DonorRatingResponse] = None
    notes: str

class DonationRecordCreateDTO(BaseModel):
    units_donated: Optional[int] = 1
    notes: Optional[str] = ""

class CompleteWithoutDonationDTO(BaseModel):
    reason: str = "Blood no longer needed"


# ─── Rating and Badges DTOs ───
class DonorRatingCreateDTO(BaseModel):
    stars: int = Field(5, ge=1, le=5)
    punctuality: Optional[str] = ""
    fitness: Optional[str] = ""
    feedback: Optional[str] = ""

class DonorBadgeDTO(BaseModel):
    badge: str
    earned_at: datetime

# ─── Blood Camp DTOs ───
class BloodCampCreateDTO(BaseModel):
    title: str
    description: Optional[str] = ""
    location: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scheduled_date: date
    start_time: str
    end_time: str
    capacity: Optional[int] = 50
    target_blood_groups: Optional[str] = "" # e.g. "O+,O-,A+"

class BloodCampResponse(BaseModel):
    id: str
    title: str
    description: str
    location: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scheduled_date: date
    start_time: str
    end_time: str
    capacity: int
    target_blood_groups: str
    is_active: bool
    hospital_name: str
    hospital_phone: str
    registered_count: int
    is_full: bool
    created_at: datetime

class CampRegistrationResponse(BaseModel):
    id: str
    camp_id: str
    camp_title: str
    camp_date: date
    camp_location: str
    status: str
    created_at: datetime

# ─── Dashboard Stats DTOs ───
class HospitalDashboardActiveItem(BaseModel):
    request: BloodRequestListResponse
    top_3: List[DonationResponseSummary]
    total_notified: int
    accepted_count: int
    rejected_count: int
    pending_count: int
    confirmed_donors: List[DonationResponseSummary]

class HospitalDashboardStats(BaseModel):
    total_requests: int
    active_requests: int
    completed_donations: int
    donations_this_month: int

class HospitalDashboardResponse(BaseModel):
    stats: HospitalDashboardStats
    active_requests: List[HospitalDashboardActiveItem]

class TVScreenHospitalInfo(BaseModel):
    name: str
    latitude: str
    longitude: str

class TVScreenDonorItem(BaseModel):
    response_id: str
    donor_name: str
    donor_phone: str
    donor_whatsapp: str
    eta_minutes: Optional[int] = None
    status: str
    donor_latitude: str
    donor_longitude: str

class TVScreenDataResponse(BaseModel):
    hospital: Optional[TVScreenHospitalInfo] = None
    active_request: Optional[BloodRequestListResponse] = None
    confirmed_donors: List[TVScreenDonorItem] = []

class AnalyticsMonthlyItem(BaseModel):
    month: str
    count: int

class AnalyticsDashboardResponse(BaseModel):
    total_requests: int
    completed_donations: int
    donations_this_month: int
    success_rate_percent: float
    by_blood_group: List[dict]
    by_urgency: List[dict]
    by_status: List[dict]
    monthly_donations: List[AnalyticsMonthlyItem]
    avg_donor_rating: float

class NotificationResponseDTO(BaseModel):
    id: str
    channel: str
    subject: str
    body: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime
