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
    async def create(self, user: User) -> User:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
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
