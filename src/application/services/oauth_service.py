import base64
import hashlib
import logging
import secrets
import string
from typing import Dict, Tuple
from urllib.parse import urlencode, urljoin
from src.application.services.env_service import get_env_variable
from src.application.enums.device_type import DeviceType

logger = logging.getLogger(__name__)
schulnetz_client_id = get_env_variable("SCHULNETZ_CLIENT_ID")

def generate_oauth_url(auth_type: DeviceType, base_url: str) -> Dict[str, str]:
    """
    Generate OAuth authorization URL for Microsoft login.

    Args:
        auth_type: Type of authentication - DeviceType.MOBILE or DeviceType.WEB
        base_url: Base Schulnetz url

    Returns:
        Dictionary containing:
        - auth_url: The authorization URL to redirect to
        - code_verifier: PKCE code verifier (mobile only, client must store this)
        - state: The state parameter for CSRF protection
    """
    
    if auth_type == DeviceType.MOBILE:

        # Generate PKCE parameters for mobile flow
        code_verifier, code_challenge = _gen_pkce_challenge()
        state = _gen_rnd_str(32)
        nonce = _gen_rnd_str(32)

        # Generate authorization parameters
        auth_params = {
            "response_type": "code",
            "client_id": schulnetz_client_id,
            "state": state,
            "redirect_uri": "",
            "scope": "openid ",  # Note the trailing space as in original
            "nonce": nonce
        }

        # Add PKCE parameters for mobile flow
        if auth_type == "mobile" and code_challenge:
            auth_params["code_challenge"] = code_challenge
            auth_params["code_challenge_method"] = "S256"

        # Build authorization URL
        auth_url = urljoin(base_url, "/authorize.php?") + urlencode(auth_params)

        logger.info(f"Generated OAuth URL for {auth_type} authentication")
        logger.info(f"Auth URL: {auth_url[:100]}...")

        result = {
            "auth_url": auth_url,
            "state": state,
            "code_verifier": code_verifier
        }

        return result

def _gen_rnd_str(length: int) -> str:
    """Generate a cryptographically secure random string."""
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

def _gen_pkce_challenge() -> Tuple[str, str]:
    """Generate PKCE code verifier and code challenge."""
    code_verifier = _gen_rnd_str(128)
    s256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (base64.urlsafe_b64encode(s256).decode("utf-8").rstrip("="))
    return code_verifier, code_challenge