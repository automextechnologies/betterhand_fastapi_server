from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any

@dataclass
class User:
    id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    hashed_password: str = ""
    role: str = "" # "hospital", "donor", "ward_member"
    is_active: bool = True
    is_staff: bool = False
    date_joined: datetime = field(default_factory=datetime.utcnow)
    fcm_token: Optional[str] = None

@dataclass
class HospitalProfile:
    id: Optional[str] = None
    user_id: str = ""
    name: str = ""
    registration_number: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    district: str = ""
    local_body_type: str = ""
    local_body_name: str = ""
    ward_number: str = ""
    pincode: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    whatsapp_number: str = ""
    logo: Optional[str] = None
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DonorQuestionnaire:
    questionnaire_completed: bool = False
    q_weight_ok: bool = False
    q_age_ok: bool = False
    q_no_illness: bool = False
    q_no_medication: bool = False
    q_no_recent_donation: bool = False
    q_no_tattoo: bool = False
    q_no_alcohol: bool = False
    q_last_donation_date: Optional[date] = None
    q_chronic_conditions: str = ""
    consent_given: bool = False
    consent_date: Optional[datetime] = None

@dataclass
class DonorProfile:
    id: Optional[str] = None
    user_id: str = ""
    full_name: str = ""
    blood_group: str = ""
    phone: str = ""
    age: Optional[int] = None
    gender: str = ""
    address: str = ""
    state: str = ""
    district: str = ""
    local_body_type: str = ""
    local_body_name: str = ""
    ward_number: str = ""
    city: str = ""
    pincode: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: bool = True
    whatsapp_number: str = ""
    is_student: bool = False
    college_name: str = ""
    college_district: str = ""
    questionnaire: DonorQuestionnaire = field(default_factory=DonorQuestionnaire)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def priority_score(self) -> int:
        score = 0
        if self.questionnaire.questionnaire_completed:
            score += 50
        if self.questionnaire.consent_given:
            score += 30
        if self.is_available:
            score += 10
        return score
