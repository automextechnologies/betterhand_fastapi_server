from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from datetime import datetime

class HospitalRegisterDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str
    registration_number: str
    phone: str
    address: Optional[str] = ""
    city: Optional[str] = ""
    state: str
    district: Optional[str] = ""
    local_body_type: Optional[str] = ""
    local_body_name: Optional[str] = ""
    ward_number: Optional[str] = ""
    pincode: Optional[str] = ""
    whatsapp_number: Optional[str] = ""
    fcm_token: Optional[str] = ""

class DonorRegisterDTO(BaseModel):
    password: str = Field(..., min_length=8)
    full_name: str
    blood_group: str
    phone: str
    age: Optional[int] = None
    gender: Optional[str] = ""
    state: Optional[str] = ""
    district: Optional[str] = ""
    local_body_type: Optional[str] = ""
    local_body_name: Optional[str] = ""
    ward_number: Optional[str] = ""
    city: Optional[str] = ""
    pincode: Optional[str] = ""
    is_student: Optional[bool] = False
    college_name: Optional[str] = ""
    college_district: Optional[str] = ""
    fcm_token: Optional[str] = ""

class LoginDTO(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str
    fcm_token: Optional[str] = ""

class TokenResponse(BaseModel):
    access: str
    refresh: str

class TokenRefreshDTO(BaseModel):
    refresh: str

class ChangePasswordDTO(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

class UpdateLocationDTO(BaseModel):
    latitude: float
    longitude: float

class UpdateFCMTokenDTO(BaseModel):
    fcm_token: str

class HospitalProfileResponse(BaseModel):
    id: str
    user_id: str
    name: str
    registration_number: str
    phone: str
    address: str
    city: str
    state: str
    district: str
    local_body_type: str
    local_body_name: str
    ward_number: str
    pincode: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    whatsapp_number: str
    logo: Optional[str] = None
    is_verified: bool

class DonorQuestionnaireDTO(BaseModel):
    questionnaire_completed: bool = False
    q_weight_ok: bool = False
    q_age_ok: bool = False
    q_no_illness: bool = False
    q_no_medication: bool = False
    q_no_recent_donation: bool = False
    q_no_tattoo: bool = False
    q_no_alcohol: bool = False
    q_last_donation_date: Optional[str] = None # format YYYY-MM-DD
    q_chronic_conditions: Optional[str] = ""
    consent_given: bool = False

class DonorProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    blood_group: str
    phone: str
    age: Optional[int] = None
    gender: str
    state: str
    district: str
    local_body_type: str
    local_body_name: str
    ward_number: str
    city: str
    pincode: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: bool
    whatsapp_number: str
    is_student: bool
    college_name: str
    college_district: str
    questionnaire: DonorQuestionnaireDTO

class UserMeResponse(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    date_joined: datetime
    profile: Optional[Any] = None
