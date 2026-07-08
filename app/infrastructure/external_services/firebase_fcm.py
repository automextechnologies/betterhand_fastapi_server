import logging
import os
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

def initialize_firebase_app() -> bool:
    import firebase_admin
    from firebase_admin import credentials
    
    if not firebase_admin._apps:
        # 1. Try to load from environment variable FIREBASE_CREDENTIALS_JSON directly
        cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if cred_json:
            try:
                cred_info = json.loads(cred_json)
                cred = credentials.Certificate(cred_info)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin successfully initialized from FIREBASE_CREDENTIALS_JSON env var.")
                return True
            except Exception as json_err:
                logger.error(f"Failed to parse or initialize Firebase from FIREBASE_CREDENTIALS_JSON: {json_err}")
        
        # 2. Fallback to path-based configuration
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if not os.path.isabs(cred_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            cred_path = os.path.join(base_dir, cred_path)
            
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Firebase Admin successfully initialized from file: {cred_path}")
                return True
            except Exception as file_err:
                logger.error(f"Failed to initialize Firebase from file path {cred_path}: {file_err}")
                return False
        else:
            logger.warning(f"Firebase credentials not found (no raw JSON env, and file not found at {cred_path}). Push notifications will not send.")
            return False
            
    return True

def send_push_notification(fcm_token: str, title: str, body: str, data: dict = None) -> bool:
    if not fcm_token:
        logger.warning("No FCM token provided — skipping push.")
        return False
        
    try:
        import firebase_admin
        from firebase_admin import messaging
        
        if not initialize_firebase_app():
            return False
            
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            token=fcm_token,
            android=messaging.AndroidConfig(priority="high"),
        )
        response = messaging.send(message)
        logger.info(f"FCM sent: {response}")
        return True
    except Exception as exc:
        logger.error(f"FCM error: {exc}")
        return False

def send_push_to_many(fcm_tokens: list[str], title: str, body: str, data: dict = None):
    tokens = [t for t in fcm_tokens if t]
    if not tokens:
        return
        
    try:
        import firebase_admin
        from firebase_admin import messaging
        
        if not initialize_firebase_app():
            return
            
        messages = [
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={str(k): str(v) for k, v in (data or {}).items()},
                token=token,
                android=messaging.AndroidConfig(priority="high"),
            )
            for token in tokens
        ]
        response = messaging.send_each(messages)
        logger.info(f"FCM batch sent to {len(tokens)} tokens.")
        return response
    except Exception as exc:
        logger.error(f"FCM batch error: {exc}")
