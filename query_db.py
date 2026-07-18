import asyncio
from app.infrastructure.database.mongodb import db, connect_to_mongo, close_mongo_connection
from app.application.use_cases.ward_use_cases import WardUseCases
from app.dependencies.db_repos import (
    get_ward_repository, get_ward_member_repository, get_ward_alert_repository,
    get_ward_notif_repository, get_request_repository, get_response_repository,
    get_record_repository, get_rating_repository, get_badge_repository
)
from app.utils.websocket import ws_broadcast

async def main():
    await connect_to_mongo()
    
    ward_repo = get_ward_repository()
    ward_member_repo = get_ward_member_repository()
    ward_alert_repo = get_ward_alert_repository()
    ward_notif_repo = get_ward_notif_repository()
    request_repo = get_request_repository()
    response_repo = get_response_repository()
    record_repo = get_record_repository()
    rating_repo = get_rating_repository()
    badge_repo = get_badge_repository()
    
    ward_use_cases = WardUseCases(
        user_repo=None,
        donor_repo=None,
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
    
    filters = {
        "state": "Kerala",
        "district": "Malappuram",
        "local_body_name": "valanchery",
        "ward_number": "6"
    }
    
    print("calling list_wards_formatted with has_member=True:")
    res = await ward_use_cases.list_wards_formatted(filters, has_member=True)
    import json
    print(json.dumps(res, indent=2))
    
    print("\ncalling list_wards_formatted with has_member=False:")
    res_false = await ward_use_cases.list_wards_formatted(filters, has_member=False)
    print(json.dumps(res_false, indent=2))
    
    await close_mongo_connection()

if __name__ == '__main__':
    asyncio.run(main())
