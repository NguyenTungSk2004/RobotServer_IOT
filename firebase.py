import firebase_admin
from firebase_admin import credentials, auth
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load .env
load_dotenv()

def _initialize_firebase():
    """Khởi tạo Firebase Admin SDK nếu chưa được khởi tạo"""
    if not firebase_admin._apps:
        # Tạo dict cho service account từ env
        service_account_info = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
        }

        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)

def verify_firebase_token(id_token: str) -> Dict[str, Any]:
    try:
        _initialize_firebase()
        decoded_token = auth.verify_id_token(id_token)
        return {
            'success': True,
            'uid': decoded_token.get('uid'),
            'email': decoded_token.get('email'),
            'email_verified': decoded_token.get('email_verified', False),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
            'auth_time': decoded_token.get('auth_time'),
            'exp': decoded_token.get('exp'),
            'firebase': decoded_token.get('firebase', {})
        }
    except auth.InvalidIdTokenError:
        return {'success': False, 'error': 'Token không hợp lệ hoặc đã hết hạn', 'error_code': 'INVALID_TOKEN'}
    except auth.ExpiredIdTokenError:
        return {'success': False, 'error': 'Token đã hết hạn', 'error_code': 'EXPIRED_TOKEN'}
    except auth.RevokedIdTokenError:
        return {'success': False, 'error': 'Token đã bị thu hồi', 'error_code': 'REVOKED_TOKEN'}
    except auth.CertificateFetchError:
        return {'success': False, 'error': 'Lỗi khi lấy certificate từ Firebase', 'error_code': 'CERTIFICATE_ERROR'}
    except Exception as e:
        return {'success': False, 'error': f'Lỗi không xác định: {str(e)}', 'error_code': 'UNKNOWN_ERROR'}
