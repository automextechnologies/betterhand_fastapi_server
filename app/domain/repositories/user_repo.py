from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities.user import User, HospitalProfile, DonorProfile

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_phone(self, phone: str) -> Optional[User]:
        pass

    @abstractmethod
    async def create(self, user: User) -> User:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        pass

    @abstractmethod
    async def get_by_role(self, role: str) -> List[User]:
        pass

    @abstractmethod
    async def list_all(self) -> List[User]:
        pass

    @abstractmethod
    async def get_users_with_fcm_token(self) -> List[User]:
        pass


class HospitalProfileRepository(ABC):
    @abstractmethod
    async def get_by_id(self, profile_id: str) -> Optional[HospitalProfile]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[HospitalProfile]:
        pass

    @abstractmethod
    async def create(self, profile: HospitalProfile) -> HospitalProfile:
        pass

    @abstractmethod
    async def update(self, profile: HospitalProfile) -> HospitalProfile:
        pass

    @abstractmethod
    async def list_all(self) -> List[HospitalProfile]:
        pass


class DonorProfileRepository(ABC):
    @abstractmethod
    async def get_by_id(self, profile_id: str) -> Optional[DonorProfile]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[DonorProfile]:
        pass

    @abstractmethod
    async def create(self, profile: DonorProfile) -> DonorProfile:
        pass

    @abstractmethod
    async def update(self, profile: DonorProfile) -> DonorProfile:
        pass

    @abstractmethod
    async def search_donors(
        self,
        blood_group: str,
        longitude: float,
        latitude: float,
        radius_km: float,
        cooldown_cutoff_date: Optional[str] = None
    ) -> List[DonorProfile]:
        pass

    @abstractmethod
    async def get_distinct_colleges(self, district: Optional[str] = None) -> List[dict]:
        pass

    @abstractmethod
    async def list_all(self) -> List[DonorProfile]:
        pass

    @abstractmethod
    async def list_by_ward(
        self,
        state: str,
        local_body_name: str,
        ward_number: str,
        is_available: Optional[bool] = None,
        user_ids: Optional[List[str]] = None,
        blood_group: Optional[str] = None
    ) -> List[DonorProfile]:
        pass

    @abstractmethod
    async def count_by_ward(
        self,
        state: str,
        local_body_name: str,
        ward_number: str,
        is_available: Optional[bool] = None
    ) -> int:
        pass
