import firebase_admin
from firebase_admin import credentials, messaging
import os

def init_firebase():
    """
    Initialize Firebase Admin SDK using service account JSON
    """
    try:
        if not firebase_admin._apps:
            # Root folder path for firebase-service-account.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cred_path = os.path.join(base_dir, 'firebase-service-account.json')
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("[SUCCESS] Firebase Admin SDK Initialized.")
            else:
                print(f"[WARNING] '{cred_path}' not found. Push notifications will be logged in console.")
    except Exception as e:
        print("[ERROR] Firebase Initialization Error:", e)

# Auto-initialize on module load
init_firebase()


def send_push_notification(fcm_token, title, body, data_payload=None):
    """
    Sends Push Notification to specific technician's FCM token
    """
    if not fcm_token:
        print("[INFO] No FCM token available for this technician. Notification skipped.")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data_payload or {},
            token=fcm_token
        )

        response = messaging.send(message)
        print(f"[SUCCESS] Push Notification sent! Message ID: {response}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to send Push Notification: {e}")
        return False