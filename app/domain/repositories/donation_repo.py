from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from datetime import datetime
from app.domain.entities.donation import (
    BloodRequest, DonationResponse, DonationRecord,
    DonorRating, DonorBadge, BloodCamp,
    CampRegistration, Notification
)


class BloodRequestRepository(ABC):
    @abstractmethod
    async def get_by_id(self, request_id: str) -> Optional[BloodRequest]:
        pass

    @abstractmethod
    async def create(self, request: BloodRequest) -> BloodRequest:
        pass

    @abstractmethod
    async def update(self, request: BloodRequest) -> BloodRequest:
        pass

    @abstractmethod
    async def list_by_hospital(self, hospital_id: str, status: Optional[str] = None) -> List[BloodRequest]:
        pass

    @abstractmethod
    async def delete_completed_or_cancelled(self, hospital_id: str) -> int:
        pass

    @abstractmethod
    async def clear_hospital_data(self, hospital_id: str) -> int:
        pass


class DonationResponseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, response_id: str) -> Optional[DonationResponse]:
        pass

    @abstractmethod
    async def get_or_create(self, request_id: str, donor_id: str, defaults: dict) -> tuple[DonationResponse, bool]:
        pass

    @abstractmethod
    async def update(self, response: DonationResponse) -> DonationResponse:
        pass

    @abstractmethod
    async def list_pending_for_donor(self, donor_id: str) -> List[DonationResponse]:
        pass

    @abstractmethod
    async def list_by_request(self, request_id: str, status_in: Optional[List[str]] = None) -> List[DonationResponse]:
        pass

    @abstractmethod
    async def list_history_for_donor(self, donor_id: str) -> List[DonationResponse]:
        pass

    @abstractmethod
    async def get_by_request_and_donor(self, request_id: str, donor_id: str) -> Optional[DonationResponse]:
        pass

    @abstractmethod
    async def update_status_by_query(self, query: dict, new_status: str) -> int:
        pass




class DonationRecordRepository(ABC):
    @abstractmethod
    async def create(self, record: DonationRecord) -> DonationRecord:
        pass

    @abstractmethod
    async def get_by_id(self, record_id: str) -> Optional[DonationRecord]:
        pass

    @abstractmethod
    async def get_last_for_donor(self, donor_id: str) -> Optional[DonationRecord]:
        pass

    @abstractmethod
    async def list_by_donor(self, donor_id: str) -> List[DonationRecord]:
        pass

    @abstractmethod
    async def count_by_donor(self, donor_id: str) -> int:
        pass

    @abstractmethod
    async def count_by_hospital(self, hospital_id: str, since: Optional[datetime] = None) -> int:
        pass

    @abstractmethod
    async def get_success_rate_and_breakdowns(self, hospital_id: str) -> dict:
        pass

    @abstractmethod
    async def get_monthly_counts_past_90_days(self) -> List[dict]:
        pass

class DonorRatingRepository(ABC):
    @abstractmethod
    async def create(self, rating: DonorRating) -> DonorRating:
        pass

    @abstractmethod
    async def get_by_record_id(self, record_id: str) -> Optional[DonorRating]:
        pass

    @abstractmethod
    async def get_avg_rating_for_donor(self, donor_id: str) -> Optional[float]:
        pass

    @abstractmethod
    async def get_avg_rating_given_by_hospital(self, hospital_id: str) -> Optional[float]:
        pass


class DonorBadgeRepository(ABC):
    @abstractmethod
    async def create(self, badge: DonorBadge) -> DonorBadge:
        pass

    @abstractmethod
    async def get_or_create(self, donor_id: str, badge: str) -> tuple[DonorBadge, bool]:
        pass

    @abstractmethod
    async def list_by_donor(self, donor_id: str) -> List[DonorBadge]:
        pass


class BloodCampRepository(ABC):
    @abstractmethod
    async def create(self, camp: BloodCamp) -> BloodCamp:
        pass

    @abstractmethod
    async def get_by_id(self, camp_id: str) -> Optional[BloodCamp]:
        pass

    @abstractmethod
    async def list_active_camps(self, city: Optional[str] = None, blood_group: Optional[str] = None) -> List[BloodCamp]:
        pass

    @abstractmethod
    async def list_by_hospital(self, hospital_id: str) -> List[BloodCamp]:
        pass


class CampRegistrationRepository(ABC):
    @abstractmethod
    async def get_or_create(self, camp_id: str, donor_id: str, defaults: dict) -> tuple[CampRegistration, bool]:
        pass

    @abstractmethod
    async def get_by_camp_and_donor(self, camp_id: str, donor_id: str) -> Optional[CampRegistration]:
        pass

    @abstractmethod
    async def update(self, reg: CampRegistration) -> CampRegistration:
        pass

    @abstractmethod
    async def count_active_by_camp(self, camp_id: str) -> int:
        pass

    @abstractmethod
    async def list_by_donor(self, donor_id: str) -> List[CampRegistration]:
        pass


class NotificationRepository(ABC):
    @abstractmethod
    async def create(self, notif: Notification) -> Notification:
        pass

    @abstractmethod
    async def list_by_recipient(self, recipient_id: str) -> List[Notification]:
        pass
