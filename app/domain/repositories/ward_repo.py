from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from app.domain.entities.ward import Ward, WardMember, WardBloodAlert, WardDonorNotification

class WardRepository(ABC):
    @abstractmethod
    async def get_by_id(self, ward_id: str) -> Optional[Ward]:
        pass

    @abstractmethod
    async def get_or_create(
        self,
        ward_number: str,
        local_body_name: str,
        state: str,
        defaults: dict
    ) -> tuple[Ward, bool]:
        pass

    @abstractmethod
    async def search_wards(self, filters: dict, has_member: bool = False) -> List[Ward]:
        pass

    @abstractmethod
    async def list_all(self) -> List[Ward]:
        pass


class WardMemberRepository(ABC):
    @abstractmethod
    async def get_by_id(self, member_id: str) -> Optional[WardMember]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[WardMember]:
        pass

    @abstractmethod
    async def create(self, member: WardMember) -> WardMember:
        pass

    @abstractmethod
    async def update(self, member: WardMember) -> WardMember:
        pass

    @abstractmethod
    async def get_verified_members_by_ward(self, ward_id: str) -> List[WardMember]:
        pass

    @abstractmethod
    async def search_members(self, filters: dict, limit: int = 10) -> List[WardMember]:
        pass

    @abstractmethod
    async def list_all(self) -> List[WardMember]:
        pass

    @abstractmethod
    async def get_members_by_ward(self, ward_id: str) -> List[WardMember]:
        pass


class WardBloodAlertRepository(ABC):
    @abstractmethod
    async def get_by_id(self, alert_id: str) -> Optional[WardBloodAlert]:
        pass

    @abstractmethod
    async def create(self, alert: WardBloodAlert) -> WardBloodAlert:
        pass

    @abstractmethod
    async def update(self, alert: WardBloodAlert) -> WardBloodAlert:
        pass

    @abstractmethod
    async def get_or_create(self, ward_member_id: str, blood_request_id: str, defaults: dict) -> tuple[WardBloodAlert, bool]:
        pass

    @abstractmethod
    async def list_by_member(self, ward_member_id: str, status: Optional[str] = None) -> List[WardBloodAlert]:
        pass

    @abstractmethod
    async def get_by_blood_request_id(self, request_id: str) -> Optional[WardBloodAlert]:
        pass


class WardDonorNotificationRepository(ABC):
    @abstractmethod
    async def get_or_create(self, alert_id: str, donor_id: str, defaults: dict) -> tuple[WardDonorNotification, bool]:
        pass

    @abstractmethod
    async def list_by_alert(self, alert_id: str) -> List[WardDonorNotification]:
        pass
