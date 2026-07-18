from fastapi import Depends
from app.utils.websocket import ws_broadcast

# Repositories
from app.infrastructure.repositories.mongo_user_repo import (
    MongoUserRepository, MongoHospitalProfileRepository, MongoDonorProfileRepository
)
from app.infrastructure.repositories.mongo_ward_repo import (
    MongoWardRepository, MongoWardMemberRepository, MongoWardBloodAlertRepository, MongoWardDonorNotificationRepository
)
from app.infrastructure.repositories.mongo_donation_repo import (
    MongoBloodRequestRepository, MongoDonationResponseRepository, MongoDonationRecordRepository,
    MongoDonorRatingRepository, MongoDonorBadgeRepository,
    MongoBloodCampRepository, MongoCampRegistrationRepository, MongoNotificationRepository
)

# Use Cases
from app.application.use_cases.auth_use_cases import AuthUseCases
from app.application.use_cases.donation_use_cases import DonationUseCases
from app.application.use_cases.ward_use_cases import WardUseCases
from app.application.use_cases.admin_use_cases import AdminUseCases

# Repository Dependencies
def get_user_repository() -> MongoUserRepository:
    return MongoUserRepository()

def get_hospital_repository() -> MongoHospitalProfileRepository:
    return MongoHospitalProfileRepository()

def get_donor_repository() -> MongoDonorProfileRepository:
    return MongoDonorProfileRepository()

def get_ward_repository() -> MongoWardRepository:
    return MongoWardRepository()

def get_ward_member_repository() -> MongoWardMemberRepository:
    return MongoWardMemberRepository()

def get_ward_alert_repository() -> MongoWardBloodAlertRepository:
    return MongoWardBloodAlertRepository()

def get_ward_notif_repository() -> MongoWardDonorNotificationRepository:
    return MongoWardDonorNotificationRepository()

def get_request_repository() -> MongoBloodRequestRepository:
    return MongoBloodRequestRepository()

def get_response_repository() -> MongoDonationResponseRepository:
    return MongoDonationResponseRepository()

def get_record_repository() -> MongoDonationRecordRepository:
    return MongoDonationRecordRepository()


def get_rating_repository() -> MongoDonorRatingRepository:
    return MongoDonorRatingRepository()

def get_badge_repository() -> MongoDonorBadgeRepository:
    return MongoDonorBadgeRepository()

def get_camp_repository() -> MongoBloodCampRepository:
    return MongoBloodCampRepository()

def get_camp_reg_repository() -> MongoCampRegistrationRepository:
    return MongoCampRegistrationRepository()

def get_notif_repository() -> MongoNotificationRepository:
    return MongoNotificationRepository()


# Use Case Dependencies
def get_auth_use_cases(
    user_repo: MongoUserRepository = Depends(get_user_repository),
    hospital_repo: MongoHospitalProfileRepository = Depends(get_hospital_repository),
    donor_repo: MongoDonorProfileRepository = Depends(get_donor_repository),
    request_repo: MongoBloodRequestRepository = Depends(get_request_repository),
    response_repo: MongoDonationResponseRepository = Depends(get_response_repository),
    ward_repo: MongoWardRepository = Depends(get_ward_repository),
    ward_member_repo: MongoWardMemberRepository = Depends(get_ward_member_repository)
) -> AuthUseCases:
    return AuthUseCases(
        user_repo=user_repo,
        hospital_repo=hospital_repo,
        donor_repo=donor_repo,
        request_repo=request_repo,
        response_repo=response_repo,
        ward_repo=ward_repo,
        ward_member_repo=ward_member_repo
    )

def get_donation_use_cases(
    user_repo: MongoUserRepository = Depends(get_user_repository),
    hospital_repo: MongoHospitalProfileRepository = Depends(get_hospital_repository),
    donor_repo: MongoDonorProfileRepository = Depends(get_donor_repository),
    ward_repo: MongoWardRepository = Depends(get_ward_repository),
    ward_member_repo: MongoWardMemberRepository = Depends(get_ward_member_repository),
    ward_alert_repo: MongoWardBloodAlertRepository = Depends(get_ward_alert_repository),
    ward_notif_repo: MongoWardDonorNotificationRepository = Depends(get_ward_notif_repository),
    request_repo: MongoBloodRequestRepository = Depends(get_request_repository),
    response_repo: MongoDonationResponseRepository = Depends(get_response_repository),
    record_repo: MongoDonationRecordRepository = Depends(get_record_repository),
    rating_repo: MongoDonorRatingRepository = Depends(get_rating_repository),
    badge_repo: MongoDonorBadgeRepository = Depends(get_badge_repository),
    camp_repo: MongoBloodCampRepository = Depends(get_camp_repository),
    camp_reg_repo: MongoCampRegistrationRepository = Depends(get_camp_reg_repository),
    notif_repo: MongoNotificationRepository = Depends(get_notif_repository)
) -> DonationUseCases:
    return DonationUseCases(
        user_repo=user_repo,
        hospital_repo=hospital_repo,
        donor_repo=donor_repo,
        ward_repo=ward_repo,
        ward_member_repo=ward_member_repo,
        ward_alert_repo=ward_alert_repo,
        ward_notif_repo=ward_notif_repo,
        request_repo=request_repo,
        response_repo=response_repo,
        record_repo=record_repo,
        rating_repo=rating_repo,
        badge_repo=badge_repo,
        camp_repo=camp_repo,
        camp_reg_repo=camp_reg_repo,
        notif_repo=notif_repo,
        ws_broadcast_func=ws_broadcast
    )

def get_ward_use_cases(
    user_repo: MongoUserRepository = Depends(get_user_repository),
    donor_repo: MongoDonorProfileRepository = Depends(get_donor_repository),
    ward_repo: MongoWardRepository = Depends(get_ward_repository),
    ward_member_repo: MongoWardMemberRepository = Depends(get_ward_member_repository),
    ward_alert_repo: MongoWardBloodAlertRepository = Depends(get_ward_alert_repository),
    ward_notif_repo: MongoWardDonorNotificationRepository = Depends(get_ward_notif_repository),
    request_repo: MongoBloodRequestRepository = Depends(get_request_repository),
    response_repo: MongoDonationResponseRepository = Depends(get_response_repository),
    record_repo: MongoDonationRecordRepository = Depends(get_record_repository),
    rating_repo: MongoDonorRatingRepository = Depends(get_rating_repository),
    badge_repo: MongoDonorBadgeRepository = Depends(get_badge_repository)
) -> WardUseCases:
    return WardUseCases(
        user_repo=user_repo,
        donor_repo=donor_repo,
        ward_repo=ward_repo,
        ward_member_repo=ward_member_repo,
        ward_alert_repo=ward_alert_repo,
        ward_notif_repo=ward_notif_repo,
        request_repo=request_repo,
        response_repo=response_repo,
        record_repo=record_repo,
        rating_repo=rating_repo,
        badge_repo=badge_repo,
        ws_broadcast_func=ws_broadcast
    )

def get_admin_use_cases(
    user_repo: MongoUserRepository = Depends(get_user_repository),
    hospital_repo: MongoHospitalProfileRepository = Depends(get_hospital_repository),
    donor_repo: MongoDonorProfileRepository = Depends(get_donor_repository),
    ward_member_repo: MongoWardMemberRepository = Depends(get_ward_member_repository),
    ward_repo: MongoWardRepository = Depends(get_ward_repository)
) -> AdminUseCases:
    return AdminUseCases(
        user_repo=user_repo,
        hospital_repo=hospital_repo,
        donor_repo=donor_repo,
        ward_member_repo=ward_member_repo,
        ward_repo=ward_repo
    )
