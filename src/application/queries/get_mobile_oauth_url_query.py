from src.application.enums.device_type import DeviceType
from src.application.services.oauth_service import generate_oauth_url
from src.application.dtos.auth_oauth_dtos import MobileOAuthUrlResponseDto

def get_mobile_oauth_url_query() -> MobileOAuthUrlResponseDto:
    oauth_data = generate_oauth_url(auth_type=DeviceType.MOBILE)

    return MobileOAuthUrlResponseDto(
        authorization_url=oauth_data["auth_url"],
        code_verifier=oauth_data["code_verifier"]
    )