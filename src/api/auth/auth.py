import asyncio
import time
from datetime import datetime
from bs4 import BeautifulSoup
import httpx
import hashlib
import base64
import secrets
import string
import os
from urllib.parse import urlparse, parse_qs, urlencode
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from src.infrastructure.logging_config import get_logger
from src.infrastructure.monitoring import monitor_performance, add_breadcrumb, capture_exception
from playwright.async_api import async_playwright, Page, expect

# Logger for this module
logger = get_logger("authentication")

two_fa_queue = asyncio.Queue()

load_dotenv()

SCHULNETZ_CLIENT_ID = os.getenv("SCHULNETZ_CLIENT_ID")

if not all([SCHULNETZ_CLIENT_ID]):
    raise EnvironmentError("Missing required environment variables.")



def generate_random_string(length: int) -> str:
    """Generate a cryptographically secure random string."""
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def generate_pkce_challenge() -> Tuple[str, str]:
    """Generate PKCE code verifier and code challenge."""
    code_verifier = generate_random_string(128)
    s256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (base64.urlsafe_b64encode(s256).decode("utf-8").rstrip("="))
    return code_verifier, code_challenge


def generate_auth_params(state: str, code_challenge: str, nonce: str) -> Dict[str, str]:
    """Generate OAuth2 authorization parameters."""
    return {
        "response_type": "code",
        "client_id": SCHULNETZ_CLIENT_ID,
        "state": state,
        "redirect_uri": "",  # Empty as shown in curl commands
        "scope": "openid ",  # Note the trailing space as in curl
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "nonce": nonce
    }


async def handle_2fa_input(page: Page) -> None:
    """Handle 2FA token input when required."""
    logger.info("Handling 2FA authentication...")
    add_breadcrumb(message="Starting 2FA authentication", category="auth.2fa", level="info")
    logger.info("Please provide 2FA token via /2FA endpoint...")
    two_fa_token = await asyncio.wait_for(two_fa_queue.get(), timeout=120)
    logger.info("Received 2FA token")
    add_breadcrumb(message="2FA token received", category="auth.2fa", level="info")
    
    two_fa_field = 'input[type="tel"], input[name="otc"]'
    await expect(page.locator(two_fa_field)).to_be_visible(timeout=20000)
    await page.fill(two_fa_field, str(two_fa_token))
    submit_button = page.locator('#idSubmit_SAOTCC_Continue')
    if await submit_button.is_visible(timeout=5000):
        await submit_button.click()


async def handle_authenticator_code_display(page: Page) -> None:
    """Handle authenticator app code display."""
    logger.info("Handling authenticator code display...")
    auth_number = page.locator("#idRichContext_DisplaySign")
    number_text = await auth_number.text_content()
    logger.info(f"Authentication number found: {number_text}")
    
    logger.info("Waiting for authentication dialog to close...")
    await auth_number.wait_for(state="hidden", timeout=60000)
    logger.info("Authentication dialog has closed")


async def handle_security_info_update(page: Page) -> None:
    """Handle security information update dialogger."""
    logger.info("Handling security information update...")
    container = page.locator('[data-automation-id="SecurityInfoRegister"]')
    await container.wait_for(state="visible", timeout=5000)
    # TODO: handle the security info update form


async def handle_stay_signed_in(page: Page) -> None:
    """Handle stay signed in prompt."""
    logger.info("Handling 'Stay signed in?' prompt...")
    yes_button = page.locator('#idSIButton9')
    await yes_button.wait_for(state="visible", timeout=3000)
    await yes_button.click()


async def handle_post_login_flow(page: Page) -> None:
    """Handle all post-login Microsoft authentication steps dynamically."""
    
    async def determine_and_handle_next_step():
        """Check what's present on the page and handle accordingly."""
        logger.info("Determining next required step...")
        
        # Define all possible elements we might encounter
        selectors = {
            'account_protection': "#idSubmit_ProofUp_Redirect",
            'authenticator_code': "#idRichContext_DisplaySign", 
            'two_fa_input': 'input[type="tel"], input[name="otc"]',
            'security_info_update': '[data-automation-id="SecurityInfoRegister"]',
            'stay_signed_in': '#idSIButton9'
        }
        
        # Check which elements are immediately visible (no waiting)
        found_element = None
        found_step = None
        
        for step_name, selector in selectors.items():
            try:
                element = page.locator(selector)
                if await element.is_visible(timeout=100):  # Very short timeout - just check if visible now
                    found_element = element
                    found_step = step_name
                    logger.info(f"Found: {step_name}")
                    break
            except Exception:
                continue  # Element not found, try next
        
        if not found_element:
            # If nothing is immediately visible, wait a bit for page to load and try once more
            logger.info("No elements immediately visible, waiting for page to load...")
            await page.wait_for_load_state('domcontentloaded', timeout=3000)
            
            # Try again with slightly longer timeout
            for step_name, selector in selectors.items():
                try:
                    element = page.locator(selector)
                    if await element.is_visible(timeout=500):
                        found_element = element
                        found_step = step_name
                        logger.info(f"Found after wait: {step_name}")
                        break
                except Exception:
                    continue
        
        # Handle the found element
        if found_element and found_step:
            if found_step == 'account_protection':
                await found_element.click()
                await determine_and_handle_next_step()  # Recursively check next step
                return
            elif found_step == 'authenticator_code':
                await handle_authenticator_code_display(page)
                await determine_and_handle_next_step()  # Check for next step
                return
            elif found_step == 'two_fa_input':
                await handle_2fa_input(page)
                await determine_and_handle_next_step()  # Check for next step
                return
            elif found_step == 'security_info_update':
                await handle_security_info_update(page)
                await determine_and_handle_next_step()  # Check for next step
                return
            elif found_step == 'stay_signed_in':
                await handle_stay_signed_in(page)
                return  # This should be the final step
        else:
            # If none of the expected elements are found, we might be done or on an unexpected page
            logger.info("No expected post-login elements found - login may be complete")

    await determine_and_handle_next_step()


async def perform_microsoft_login(page: Page, email: str, password: str) -> None:
    """Handle the basic Microsoft login form (email and password entry)."""
    try:
        # Step 1: Enter email
        logger.info("Entering Microsoft email...")
        email_input_selector = 'input[type="email"], input[name="loginfmt"]'
        await expect(page.locator(email_input_selector)).to_be_visible(timeout=20000)
        await page.fill(email_input_selector, email)
        email_button = page.locator('#idSIButton9')
        if await email_button.is_visible(timeout=5000):
            await email_button.click()

        # Step 2: Enter password
        logger.info("Entering Microsoft password...")
        password_input_selector = 'input[type="password"], input[name="passwd"]'
        await expect(page.locator(password_input_selector)).to_be_visible(timeout=20000)
        await page.fill(password_input_selector, password)
        password_button = page.locator('#idSIButton9')
        if await password_button.is_visible(timeout=5000):
            await password_button.click()

        logger.info("Basic Microsoft login form completed")

    except Exception as e:
        logger.error(f"Error during Microsoft login form interaction: {e}")
        logger.info(f"Current URL: {page.url}")
        logger.info(f"Page content (partial): {(await page.content())[:1000]}")
        raise


def extract_auth_code_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract authorization code and state from URL parameters."""
    if 'code=' not in url:
        return None, None
    
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query, keep_blank_values=True)
        auth_code = query_params.get("code", [None])[0]
        received_state = query_params.get("state", [None])[0]
        
        # Log the extraction for debugging
        if auth_code:
            logger.info(f"Extracted auth code: {auth_code[:50]}... (length: {len(auth_code)})")
        if received_state:
            logger.info(f"Extracted state: {received_state[:50]}... (length: {len(received_state)})")
        
        # Log the full URL for debugging (with sensitive parts truncated)
        safe_url = url.replace(auth_code, f"{auth_code[:20]}...TRUNCATED") if auth_code else url
        logger.info(f"Auth code extraction from URL: {safe_url[:200]}...")
        
        return auth_code, received_state
    except Exception as e:
        logger.error(f"Error extracting auth code from URL: {e}")
        return None, None


async def get_microsoft_redirect_code(email: str, password: str, state: str, code_challenge: str, nonce: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Navigate through Microsoft authentication flow and extract the authorization code.

    Args:
        email: Microsoft account email
        password: Microsoft account password
        state: OAuth2 state parameter for CSRF protection
        code_challenge: PKCE code challenge
        nonce: OpenID Connect nonce for replay protection

    Returns:
        Tuple of (auth_code, received_state) or (None, None) if failed
    """
    auth_params = generate_auth_params(state, code_challenge, nonce)
    auth_url = "https://schulnetz.bbbaden.ch/authorize.php?" + urlencode(auth_params)
    
    logger.info(f"Starting Microsoft authentication flow...")

    start_time = time.time()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Track all URLs visited during the authentication flow
        visited_urls = []

        def track_navigation(frame):
            url = frame.url
            timestamp = datetime.now().isoformat()
            visit_info = f"[{timestamp}] {url}"
            visited_urls.append(visit_info)

            # Keep normal console logging unchanged
            if "microsoft" not in url.lower():
                logger.info(f"Navigation: {url}")

        page.on("framenavigated", track_navigation)

        auth_code, received_state = None, None
        authentication_failed = False
        error_message = ""

        try:
            # Navigate to the authorization URL which will redirect to Microsoft
            await page.goto(auth_url, wait_until='load', timeout=60000)

            # Confirm we have landed on the Microsoft login page after the redirect
            logger.info(f"Playwright landed on: {page.url}")
            if "login.microsoftonline.com" not in page.url:
                error_message = f"Did not redirect to Microsoft login page as expected. Final URL: {page.url}"
                logger.error(f"ERROR: {error_message}")
                page_content = await page.content()
                logger.info(f"Page content (partial): {page_content[:1000]}")
                authentication_failed = True
                return None, None

            # Handle the interactive Microsoft login and post-login flow
            logger.info("Processing Microsoft login and post-login steps...")

            await perform_microsoft_login(page, email, password)
            await handle_post_login_flow(page)

            # Search through all visited URLs to find one with authorization code
            for url in visited_urls:
                if 'code=' in url:
                    auth_code, received_state = extract_auth_code_from_url(url)
                    if auth_code:
                        break
            
            if not auth_code:
                error_message = f"No auth code found in {len(visited_urls)} visited URLs. Final: {page.url}"
                logger.warning(error_message)
                authentication_failed = True
                return None, None
            
            return auth_code, received_state

        except Exception as e: 
            logger.error(f"Error during Microsoft authentication flow: {e}")
            # Uncomment the line below to save a screenshot for debugging on error
            # await page.screenshot(path="microsoft_auth_error.png")
            return None, None
        finally:
            await page.close()
            await context.close()
            await browser.close()


async def exchange_code_for_tokens(auth_code: str, code_verifier: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        auth_code: Authorization code obtained from Microsoft
        code_verifier: PKCE code verifier used in the initial request

    Returns:
        Tuple of (access_token, refresh_token) or (None, None) if failed
    """
    httpx_client = httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    token_url = "https://schulnetz.bbbaden.ch/token.php"
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": "",  # Must match the one used throughout the flow (empty in curl commands)
        "code_verifier": code_verifier,
        "client_id": SCHULNETZ_CLIENT_ID,
    }

    # Set headers for the token exchange request to match the working curl command exactly
    headers_for_token_exchange = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://schulnetz.web.app/",
        "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    logger.info("Exchanging authorization code for tokens...")
    logger.info(f"Token exchange URL: {token_url}")
    logger.info(f"Auth code length: {len(auth_code)}")
    logger.info(f"Auth code (first 50 chars): {auth_code[:50]}...")
    logger.info(f"Code verifier length: {len(code_verifier)}")
    logger.info(f"Client ID: {SCHULNETZ_CLIENT_ID}")

    try:
        token_response = await httpx_client.post(
            token_url, data=token_data, headers=headers_for_token_exchange
        )
        token_response.raise_for_status()
        token_json = token_response.json()

        access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")

        if access_token:
            logger.info("Token exchange successful")
            return access_token, refresh_token
        else:
            logger.error("Access token not found in response")
            return None, None

    except httpx.RequestError as e:
        logger.error(f"HTTP error during token exchange: {e}")
        return None, None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Status Error during token exchange: {e.response.status_code} - {e.response.text}")
        logger.info(f"Response content: {e.response.text}")
        return None, None
    finally:
        await httpx_client.aclose()


@monitor_performance("auth.exchange_code")
async def exchange_authorization_code_direct(auth_code: str, code_verifier: Optional[str] = None, auth_type: str = "mobile") -> Dict[str, Any]:
    """
    Exchange authorization code for tokens without using Playwright.
    This function is used when the authorization code is already obtained through external means.

    Args:
        auth_code: Authorization code from Microsoft OAuth callback
        code_verifier: PKCE code verifier (required for mobile flow)
        auth_type: Type of authentication - "mobile" or "web"

    Returns:
        Dictionary with authentication result
    """
    try:
        logger.info(f"Direct token exchange for {auth_type} authentication")
        logger.info(f"Auth code received: {auth_code[:30]}... (length: {len(auth_code)})")

        if auth_type == "mobile":
            # Mobile flow requires PKCE code verifier
            if not code_verifier:
                return {
                    "success": False,
                    "error": "Code verifier is required for mobile authentication"
                }

            # Exchange authorization code for tokens
            access_token, refresh_token = await exchange_code_for_tokens(auth_code, code_verifier)

            if access_token:
                logger.info("Successfully exchanged authorization code for mobile tokens")
                return {
                    "success": True,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "session_type": "mobile",
                    "message": "Mobile authentication successful"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to exchange authorization code for tokens"
                }

        elif auth_type == "web":
            # Web flow - simpler, mainly for verification
            # In a real web flow, cookies would be handled by the browser
            logger.info("Web authentication callback processed")

            # We can still try to exchange if a code_verifier is somehow available
            # But typically web flow doesn't use PKCE
            if code_verifier:
                access_token, refresh_token = await exchange_code_for_tokens(auth_code, code_verifier)
                if access_token:
                    return {
                        "success": True,
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "session_type": "web",
                        "message": "Web authentication successful with tokens"
                    }

            # For web flow without PKCE, we just acknowledge the code
            return {
                "success": True,
                "auth_code": auth_code,
                "session_type": "web",
                "message": "Web authentication code received",
                "note": "Session cookies should be handled by the browser"
            }

        else:
            return {
                "success": False,
                "error": f"Unknown authentication type: {auth_type}"
            }

    except Exception as e:
        logger.error(f"Error in direct authorization code exchange: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def validate_state_parameter(expected_state: str, received_state: Optional[str]) -> bool:
    """Validate OAuth2 state parameter for CSRF protection."""
    if not received_state:
        logger.info("Note: State validation skipped - no state received")
        return False
        
    # Direct match - ideal case
    if received_state == expected_state:
        logger.info("State validation passed (direct match).")
        return True
    
    # Handle Microsoft's composite state format
    # Microsoft sometimes returns: {hash}{base64_encoded_original_params}
    # Extract original state from base64 encoded parameters
    try:
        # Check if the received state contains base64 encoded data
        # Typically formatted as: hash + base64_encoded_params
        if len(received_state) > 64:  # Longer than a typical hash
            # Try to find where the hash ends and base64 begins
            # Look for common base64 patterns after initial hash part
            for split_point in range(32, min(64, len(received_state))):
                hash_part = received_state[:split_point]
                potential_b64 = received_state[split_point:]
                
                try:
                    # Attempt to decode as base64
                    decoded = base64.b64decode(potential_b64, validate=True).decode('utf-8')
                    
                    # Parse as URL parameters
                    if 'state=' in decoded:
                        from urllib.parse import parse_qs
                        params = parse_qs(decoded)
                        extracted_state = params.get('state', [None])[0]
                        
                        if extracted_state == expected_state:
                            logger.info("State validation passed (extracted from Microsoft composite format).")
                            logger.info(f"  Original composite state: {received_state[:50]}...")
                            logger.info(f"  Extracted state: {extracted_state}")
                            return True
                            
                except (Exception):
                    # Not valid base64 or doesn't contain expected format
                    continue
                    
    except Exception as e:
        logger.debug(f"Error parsing composite state: {e}")
    
    # If we get here, state validation failed
    logger.warning("WARNING: State mismatch!")
    logger.info(f"  Expected: {expected_state}")
    logger.info(f"  Received: {received_state}")
    logger.info("  This could indicate a security issue, but we'll continue...")
    return False


async def get_web_session_cookies(email: str, password: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """
    Authenticate via web flow and extract session cookies and auth code.
    
    Args:
        email: Microsoft account email
        password: Microsoft account password
        
    Returns:
        Tuple of (session_cookies_dict, auth_code) or (None, None) if failed
    """
    logger.info("Starting web authentication flow...")
    start_time = time.time()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Step 1: Navigate to schulnetz.bbbaden.ch (will redirect to Microsoft)
            logger.info("Navigating to https://schulnetz.bbbaden.ch/...")
            await page.goto("https://schulnetz.bbbaden.ch/", wait_until='load', timeout=60000)

            # Step 2: Handle Microsoft authentication
            logger.info(f"Current URL after redirect: {page.url}")
            if "login.microsoftonline.com" in page.url:
                logger.info("Handling Microsoft authentication...")
                await perform_microsoft_login(page, email, password)
                await handle_post_login_flow(page)
            else:
                logger.warning("Expected Microsoft login redirect, but got different URL")

            # Step 3: Wait for final redirect back to schulnetz.bbbaden.ch with auth code
            logger.info("Waiting for redirect back to schulnetz.bbbaden.ch...")
            await page.wait_for_url("https://schulnetz.bbbaden.ch/*", timeout=30000)
            
            current_url = page.url
            logger.info(f"Final URL: {current_url}")

            # Step 4: Extract auth code from URL
            auth_code, _ = extract_auth_code_from_url(current_url)
            if not auth_code:
                logger.error("No authorization code found in final URL")
                return None, None

            logger.info(f"Successfully obtained auth code: {auth_code[:30]}...")

            # Step 5: Extract all cookies for session management
            cookies = await context.cookies()
            session_cookies = {}
            
            for cookie in cookies:
                # Store cookies as key-value pairs for easy use with httpx
                session_cookies[cookie['name']] = cookie['value']

            logger.info(f"Captured {len(session_cookies)} session cookies")
            return session_cookies, auth_code

        except Exception as e:
            logger.error(f"Error during web authentication flow: {e}")
            return None, None
        finally:
            await browser.close()


async def authenticate_with_web_session(email: str, password: str) -> Dict[str, Any]:
    """
    Web authentication function that maintains session cookies instead of OAuth tokens.
    
    Args:
        email: Microsoft account email
        password: Microsoft account password
        
    Returns:
        Dictionary with authentication result and session cookies
    """
    try:
        # Get session cookies and auth code via web flow
        session_cookies, auth_code = await get_web_session_cookies(email, password)

        if not session_cookies or not auth_code:
            return {
                "success": False, 
                "error": "Failed to obtain web session cookies or auth code"
            }

        return {
            "success": True, 
            "message": "Web authentication completed successfully",
            "session_cookies": session_cookies,
            "auth_code": auth_code,
            "session_type": "web",
        }

    except Exception as e:
        logger.error(f"Web authentication error: {e}")
        return {"success": False, "error": str(e)}


async def make_authenticated_web_request(url: str, session_cookies: Dict[str, str], method: str = "GET", follow_redirects: bool = False, **kwargs) -> httpx.Response:
    """
    Make an authenticated request using web session cookies.
    
    Args:
        url: The URL to request
        session_cookies: Session cookies obtained from web authentication
        method: HTTP method (GET, POST, etc.)
        follow_redirects: Whether to follow redirects automatically
        **kwargs: Additional arguments to pass to httpx request
        
    Returns:
        httpx.Response object
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://schulnetz.bbbaden.ch/",
        "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
    }

    async with httpx.AsyncClient(
        cookies=session_cookies, 
        headers=headers, 
        follow_redirects=follow_redirects,
        timeout=30.0
    ) as client:
        if method.upper() == "GET":
            response = await client.get(url, **kwargs)
        elif method.upper() == "POST":
            response = await client.post(url, **kwargs)
        else:
            response = await client.request(method, url, **kwargs)
        
        return response

async def authenticate_with_credentials(email: str, password: str, auth_type: str = "mobile") -> Dict[str, Any]:
    """
    High-level authentication function with provided credentials.
    
    Args:
        email: Microsoft account email
        password: Microsoft account password
        auth_type: "mobile" for OAuth2 tokens or "web" for session cookies
        
    Returns:
        Dictionary with authentication result and auth data
    """
    if auth_type == "web":
        return await authenticate_with_web_session(email, password)
    elif auth_type == "mobile":
        # Original OAuth2 mobile flow
        try:
            # Start benchmark timer
            start_time = time.time()
            
            # Generate PKCE parameters and state/nonce
            code_verifier, code_challenge = generate_pkce_challenge()
            state = generate_random_string(32)
            nonce = generate_random_string(32)
            
            logger.info("Starting OAuth2 flow with generated parameters")

            # Step 1: Get authorization code from Microsoft
            auth_code, received_state = await get_microsoft_redirect_code(
                email, password, state, code_challenge, nonce
            )

            if not auth_code:
                # Auth code failure already handled in get_microsoft_redirect_code
                return {
                    "success": False, 
                    "error": "Failed to obtain authorization code from Microsoft"
                }

            # Step 2: Validate state parameter (non-fatal)
            state_valid = validate_state_parameter(state, received_state)
            if not state_valid:
                logger.warning("State validation failed, but continuing with authentication...")
            else:
                logger.info("State parameter validation successful")

            # Step 3: Exchange authorization code for tokens
            access_token, refresh_token = await exchange_code_for_tokens(auth_code, code_verifier)

            # Calculate and log benchmark results
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"Complete OAuth2 flow finished in {duration:.2f}s")

            if access_token:
                return {
                    "success": True, 
                    "message": "Authentication completed successfully",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "auth_code": auth_code,
                    "session_type": "mobile",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to exchange authorization code for tokens"
                }

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {"success": False, "error": str(e)}
    else:
        return {"success": False, "error": f"Unknown auth_type: {auth_type}. Use 'mobile' or 'web'."}


async def main(email: Optional[str] = None, password: Optional[str] = None, auth_type: str = "mobile") -> Tuple[Optional[str], Optional[str]]:
    """
    Main authentication function for backward compatibility.
    
    Args:
        email: Microsoft account email
        password: Microsoft account password
        auth_type: "mobile" for OAuth2 tokens or "web" for session cookies
        
    Returns:
        For mobile: Tuple of (access_token, refresh_token) or (None, None) if failed
        For web: Tuple of (session_cookies_dict, auth_code) or (None, None) if failed
    """
    if not email or not password:
        logger.error("Email and password are required")
        return None, None

    result = await authenticate_with_credentials(email, password, auth_type)
    
    if result["success"]:
        if auth_type == "mobile":
            return result["access_token"], result["refresh_token"]
        elif auth_type == "web":
            return result["session_cookies"], result["auth_code"]
    else:
        logger.error(f"Authentication failed: {result['error']}")
        return None, None


# Example usage functions
async def example_web_authenticated_request(email: str, password: str, page_id: str, resource_id: str, trans_id: str):
    """
    Example function showing how to make authenticated web requests like the one in your logs.
    
    Args:
        email: Microsoft account email
        password: Microsoft account password  
        page_id: The pageid parameter
        resource_id: The id parameter
        trans_id: The transid parameter
    """
    # Step 1: Authenticate and get session cookies
    auth_result = await authenticate_with_credentials(email, password, "web")
    
    if not auth_result["success"]:
        logger.error(f"Authentication failed: {auth_result['error']}")
        return None
    
    session_cookies = auth_result["session_cookies"]
    
    # Step 2: Make the authenticated request
    url = f"https://schulnetz.bbbaden.ch/index.php?pageid={page_id}&id={resource_id}&transid={trans_id}"
    
    try:
        response = await make_authenticated_web_request(url, session_cookies)
        logger.info(f"Request successful: {response.status_code}")
        logger.info(f"Response length: {len(response.content)} bytes")
        return response.text
    
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None


async def example_mobile_authenticated_request(email: str, password: str):
    """
    Example function showing how to make authenticated API requests with OAuth2 tokens.
    """
    # Step 1: Authenticate and get tokens
    auth_result = await authenticate_with_credentials(email, password, "mobile")
    
    if not auth_result["success"]:
        logger.error(f"Authentication failed: {auth_result['error']}")
        return None
    
    access_token = auth_result["access_token"]
    
    # Step 2: Make API request with bearer token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        try:
            # Example API endpoint - replace with actual endpoint
            response = await client.get("https://schulnetz.bbbaden.ch/api/some-endpoint")
            logger.info(f"API request successful: {response.status_code}")
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None

@monitor_performance("browser.authenticate.webapp_flow")
async def authenticate_unified_webapp_flow(email: str, password: str) -> Dict[str, Any]:
    """
    Alternative unified authentication that properly handles the schulnetz.web.app redirect flow.
    
    Args:
        email: Microsoft account email
        password: Microsoft account password
        
    Returns:
        Dictionary with both web session cookies and mobile OAuth2 tokens
    """
    logger.info("Starting unified authentication flow with web.app handling...")
    start_time = time.time()

    # Generate PKCE parameters for mobile OAuth2 flow
    code_verifier, code_challenge = generate_pkce_challenge()
    state = generate_random_string(32)
    nonce = generate_random_string(32)
    
    logger.info("Generated OAuth2 parameters for mobile flow:")
    logger.info(f"  Code Verifier: {code_verifier}")
    logger.info(f"  Code Challenge: {code_challenge}")
    logger.info(f"  State: {state}")
    logger.info(f"  Nonce: {nonce}")

    # Initialize variables for cleanup
    context = None
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Variables to capture auth code during redirect
        auth_code = None
        received_state = None
        redirect_domain = None

        # Set up response listener to capture auth code from intermediate redirects
        async def handle_response(response):
            nonlocal auth_code, received_state, redirect_domain
            if auth_code:  # Already found, skip
                return
                
            url = response.url
            logger.info(f"Response URL: {url}")
            
            # Check if this is a callback URL with auth code
            if ("schulnetz.web.app/callback" in url or "schulnetz.bbbaden.ch" in url) and "code=" in url:
                logger.info(f"Found callback URL with auth code: {url}")
                code, state = extract_auth_code_from_url(url)
                if code:
                    auth_code = code
                    received_state = state
                    redirect_domain = "schulnetz.web.app" if "web.app" in url else "schulnetz.bbbaden.ch"
                    logger.info(f"Captured auth code: {code[:30]}...")

        page.on("response", handle_response)

        try:
            # Step 1: Start with OAuth2 authorization URL (for mobile tokens)
            auth_params = generate_auth_params(state, code_challenge, nonce)
            auth_url = "https://schulnetz.bbbaden.ch/authorize.php?" + urlencode(auth_params)
            
            logger.info(f"Navigating to OAuth2 authorization URL: {auth_url}")
            await page.goto(auth_url, wait_until='load', timeout=60000)

            # Step 2: Handle Microsoft authentication
            logger.info(f"Current URL after redirect: {page.url}")
            if "login.microsoftonline.com" in page.url:
                logger.info("Handling Microsoft authentication...")
                await perform_microsoft_login(page, email, password)
                await handle_post_login_flow(page)
            else:
                logger.warning("Expected Microsoft login redirect, but got different URL")

            # Step 3: Wait for auth code to be captured by response handler
            logger.info("Waiting for OAuth2 callback with auth code...")
            
            # Wait up to 30 seconds for auth code to be captured
            for i in range(60):  # 60 * 0.5 = 30 seconds
                if auth_code:
                    logger.info(f"Auth code captured successfully: {auth_code[:30]}...")
                    break
                await asyncio.sleep(0.5)
            
            # Also check current URL as fallback
            current_url = page.url
            logger.info(f"Current URL after auth: {current_url}")
            
            if not auth_code:
                # Fallback: try to extract from current URL
                auth_code, received_state = extract_auth_code_from_url(current_url)
                redirect_domain = "schulnetz.web.app" if "web.app" in current_url else "schulnetz.bbbaden.ch"

            if not auth_code:
                logger.error(f"No authorization code found. Final URL: {current_url}")
                return {
                    "success": False, 
                    "error": f"Failed to obtain authorization code. Final URL: {current_url}"
                }

            logger.info(f"Successfully obtained OAuth2 auth code: {auth_code[:30]}...")
            state_valid = validate_state_parameter(state, received_state)
            if not state_valid:
                logger.warning("State validation failed, but continuing with authentication...")
            else:
                logger.info("State parameter validation successful")

            # Step 4: Extract session cookies from current browser context
            cookies = await context.cookies()
            session_cookies = {}
            
            for cookie in cookies:
                session_cookies[cookie['name']] = cookie['value']
                logger.info(f"Captured cookie: {cookie['name']} (domain: {cookie['domain']})")

            logger.info(f"Captured {len(session_cookies)} session cookies")

            # Step 5: Try to establish web session on schulnetz.bbbaden.ch
            logger.info("Attempting to establish web interface session...")
            navigation_urls = {}
            noten_url = None
            
            try:
                # Navigate to the main domain using existing session
                await page.goto("https://schulnetz.bbbaden.ch/", wait_until='load', timeout=30000)
                
                # Check if we're logged in or redirected back to Microsoft
                if "login.microsoftonline.com" not in page.url:
                    logger.info("Successfully accessed web interface")
                    
                    # Update cookies after accessing main domain
                    updated_cookies = await context.cookies()
                    for cookie in updated_cookies:
                        if cookie['name'] not in session_cookies:
                            session_cookies[cookie['name']] = cookie['value']
                            logger.info(f"Added new web session cookie: {cookie['name']}")

                    # Extract navigation URLs
                    try:
                        current_html = await page.content()
                        navigation_urls = extract_navigation_urls(current_html)
                        noten_url = navigation_urls.get("Noten")
                        logger.info(f"Extracted {len(navigation_urls)} navigation URLs")
                    except Exception as e:
                        logger.warning(f"Could not extract navigation URLs: {e}")
                else:
                    logger.warning("Still redirected to Microsoft login, web session may not be fully established")
                    
            except Exception as e:
                logger.warning(f"Could not access web interface: {e}")

        except Exception as e:
            logger.error(f"Error during unified authentication flow: {e}")
            
            return {
                "success": False,
                "error": f"Unified authentication failed: {str(e)}"
            }
        finally:
            await browser.close()

    # Step 6: Exchange auth code for OAuth2 tokens (outside browser context)
    try:
        logger.info("Exchanging authorization code for OAuth2 tokens...")
        access_token, refresh_token = await exchange_code_for_tokens(auth_code, code_verifier)
        
        if not access_token:
            return {
                "success": False,
                "error": "Failed to exchange authorization code for OAuth2 tokens"
            }

        logger.info(f"Successfully obtained access token: {access_token[:30]}...")

    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return {
            "success": False,
            "error": f"Token exchange failed: {str(e)}"
        }

    return {
        "success": True,
        "message": "Unified authentication completed successfully",
        # Mobile OAuth2 data
        "access_token": access_token,
        "refresh_token": refresh_token,
        # Web session data
        "session_cookies": session_cookies,
        "auth_code": auth_code,
        "navigation_urls": navigation_urls,
        "noten_url": noten_url,
        # Metadata
        "session_types": ["mobile", "web"],
        "authenticated_at": str(datetime.now()),
        "redirect_domain": redirect_domain or "unknown"
    }

@monitor_performance("browser.authenticate.unified")
async def authenticate_unified(email: str, password: str) -> Dict[str, Any]:
    """
    Unified authentication using navigation listener to capture auth code during redirects.
    
    Args:
        email: Microsoft account email
        password: Microsoft account password
        
    Returns:
        Dictionary with both web session cookies and mobile OAuth2 tokens
    """
    logger.info("Starting unified authentication with navigation listener...")
    start_time = time.time()
    
    # Generate PKCE parameters for mobile OAuth2 flow
    code_verifier, code_challenge = generate_pkce_challenge()
    state = generate_random_string(32)
    nonce = generate_random_string(32)
    
    logger.info("Generated OAuth2 parameters for mobile flow:")
    logger.info(f"  Code Verifier: {code_verifier}")
    logger.info(f"  Code Challenge: {code_challenge}")
    logger.info(f"  State: {state}")
    logger.info(f"  Nonce: {nonce}")


    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Variables to capture auth code during navigation
        auth_code = None
        received_state = None
        redirect_domain = None
        visited_urls = []
        authentication_failed = False
        error_message = ""

        # Set up frame navigation listener
        def handle_frame_navigated(frame):
            nonlocal auth_code, received_state, redirect_domain

            url = frame.url
            timestamp = datetime.now().isoformat()
            visit_info = f"[{timestamp}] {url}"
            visited_urls.append(visit_info)

            if auth_code:  # Already found
                return

            # Check if this URL contains the auth code
            if "code=" in url and ("schulnetz" in url):
                logger.info(f"Found URL with auth code: {url}")
                code, state = extract_auth_code_from_url(url)
                if code:
                    auth_code = code
                    received_state = state
                    redirect_domain = "schulnetz.web.app" if "web.app" in url else "schulnetz.bbbaden.ch"
                    logger.info(f"Captured auth code from navigation: {code[:30]}...")

        page.on("framenavigated", handle_frame_navigated)

        try:
            # Step 1: Start with OAuth2 authorization URL
            auth_params = generate_auth_params(state, code_challenge, nonce)
            auth_url = "https://schulnetz.bbbaden.ch/authorize.php?" + urlencode(auth_params)
            
            logger.info(f"Navigating to OAuth2 authorization URL: {auth_url}")
            await page.goto(auth_url, wait_until='load', timeout=60000)

            # Step 2: Handle Microsoft authentication
            logger.info(f"Current URL after redirect: {page.url}")
            if "login.microsoftonline.com" in page.url:
                logger.info("Handling Microsoft authentication...")
                await perform_microsoft_login(page, email, password)
                await handle_post_login_flow(page)

            # Step 3: Wait for auth code to be captured
            logger.info("Waiting for navigation to capture auth code...")
            
            # Wait up to 30 seconds for auth code
            for i in range(60):
                if auth_code:
                    break
                await asyncio.sleep(0.5)
            
            # Also check the current URL as backup
            if not auth_code:
                current_url = page.url
                logger.info(f"Checking current URL for auth code: {current_url}")
                auth_code, received_state = extract_auth_code_from_url(current_url)
                redirect_domain = "schulnetz.web.app" if "web.app" in current_url else "schulnetz.bbbaden.ch"

            if not auth_code:
                error_message = f"No authorization code captured. Final URL: {page.url}"
                authentication_failed = True
                return {
                    "success": False,
                    "error": error_message
                }

            logger.info(f"Successfully obtained auth code: {auth_code[:30]}...")
            state_valid = validate_state_parameter(state, received_state)
            if not state_valid:
                logger.warning("State validation failed, but continuing with authentication...")
            else:
                logger.info("State parameter validation successful")

            # Step 4: Extract session cookies
            cookies = await context.cookies()
            session_cookies = {}
            
            for cookie in cookies:
                session_cookies[cookie['name']] = cookie['value']
                # logger.info(f"Captured cookie: {cookie['name']} (domain: {cookie['domain']})")

            # Step 5: Try to establish web session
            navigation_urls = {}
            noten_url = None
            
            try:
                await page.goto("https://schulnetz.bbbaden.ch/", wait_until='load', timeout=30000)
                
                if "login.microsoftonline.com" not in page.url:
                    # Update cookies
                    updated_cookies = await context.cookies()
                    for cookie in updated_cookies:
                        if cookie['name'] not in session_cookies:
                            session_cookies[cookie['name']] = cookie['value']

                    # Extract navigation
                    current_html = await page.content()
                    navigation_urls = extract_navigation_urls(current_html)
                    noten_url = navigation_urls.get("Noten")
                    
            except Exception as e:
                logger.warning(f"Could not establish web session: {e}")

        except Exception as e:
            logger.error(f"Error during unified authentication: {e}")
            return {"success": False, "error": f"Authentication failed: {str(e)}"}
        finally:
            await page.close()
            await context.close()
            await browser.close()

    # Step 6: Exchange for tokens
    try:
        access_token, refresh_token = await exchange_code_for_tokens(auth_code, code_verifier)
        
        if not access_token:
            return {"success": False, "error": "Token exchange failed"}

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        return {"success": False, "error": f"Token exchange failed: {str(e)}"}

    return {
        "success": True,
        "message": "Unified authentication completed successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_cookies": session_cookies,
        "auth_code": auth_code,
        "navigation_urls": navigation_urls,
        "noten_url": noten_url,
        "session_types": ["mobile", "web"],
        "authenticated_at": str(datetime.now()),
        "redirect_domain": redirect_domain or "unknown"
    }

async def authenticate_with_existing_session(session_cookies: Dict[str, str], auth_type: str) -> Dict[str, Any]:
    """
    Attempt authentication using existing session cookies without full Microsoft login.
    
    Args:
        session_cookies: Existing session cookies from previous authentication
        auth_type: "mobile" or "web" or "unified"
        
    Returns:
        Authentication result dictionary
    """
    try:
        logger.info(f"Attempting {auth_type} authentication with existing session cookies...")
        
        if auth_type == "web" or auth_type == "unified":
            # Test web session by accessing main page
            try:
                response = await make_authenticated_web_request(
                    "https://schulnetz.bbbaden.ch/index.php", 
                    session_cookies,
                    follow_redirects=False  # Don't follow redirects to detect if session is invalid
                )
                
                if response.status_code == 200:
                    logger.info("Web session is still valid")
                    
                    # Extract navigation URLs if requested
                    if auth_type == "unified":
                        navigation_urls = extract_navigation_urls(response.text)
                        noten_url = navigation_urls.get("Noten")
                    else:
                        navigation_urls = {}
                        noten_url = None
                    
                    return {
                        "success": True,
                        "message": "Existing web session is valid",
                        "session_cookies": session_cookies,
                        "navigation_urls": navigation_urls,
                        "noten_url": noten_url,
                        "session_type": auth_type,
                        "source": "existing_session",
                    }
                else:
                    logger.info(f"Web session invalid (status: {response.status_code})")
                    
            except Exception as e:
                logger.info(f"Web session test failed: {e}")

        # For mobile or if web session is invalid, we'd need to do full auth
        # since mobile tokens can't be refreshed from session cookies alone
        if auth_type == "mobile":
            return {
                "success": False,
                "error": "Mobile token refresh from session cookies not supported. Use full authentication.",
                "requires_full_auth": True
            }
            
        return {
            "success": False,
            "error": "Session validation failed",
            "requires_full_auth": True
        }
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return {
            "success": False,
            "error": f"Session validation error: {str(e)}",
            "requires_full_auth": True
        }

def generate_oauth_url(auth_type: str = "mobile", redirect_uri: str = "") -> Dict[str, str]:
    """
    Generate OAuth authorization URL for Microsoft login.

    Args:
        auth_type: Type of authentication - "mobile" or "web"
        redirect_uri: Redirect URI for OAuth callback (empty string for Schulnetz default)

    Returns:
        Dictionary containing:
        - auth_url: The authorization URL to redirect to
        - code_verifier: PKCE code verifier (mobile only, client must store this)
        - state: The state parameter for CSRF protection
    """
    # Generate PKCE parameters for mobile flow
    code_verifier, code_challenge = generate_pkce_challenge() if auth_type == "mobile" else (None, None)
    state = generate_random_string(32)
    nonce = generate_random_string(32)

    # Generate authorization parameters
    auth_params = {
        "response_type": "code",
        "client_id": SCHULNETZ_CLIENT_ID,
        "state": state,
        "redirect_uri": redirect_uri,
        "scope": "openid ",  # Note the trailing space as in original
        "nonce": nonce
    }

    # Add PKCE parameters for mobile flow
    if auth_type == "mobile" and code_challenge:
        auth_params["code_challenge"] = code_challenge
        auth_params["code_challenge_method"] = "S256"

    # Build authorization URL
    auth_url = "https://schulnetz.bbbaden.ch/authorize.php?" + urlencode(auth_params)

    logger.info(f"Generated OAuth URL for {auth_type} authentication")
    logger.info(f"Auth URL: {auth_url[:100]}...")

    result = {
        "auth_url": auth_url,
        "state": state
    }

    # Include code_verifier for mobile (client must store this)
    if auth_type == "mobile" and code_verifier:
        result["code_verifier"] = code_verifier

    return result


def extract_navigation_urls(html_content: str) -> dict:
    """
    Extract navigation URLs from the schulnetz main page HTML.
    
    Args:
        html_content: HTML content of the main page
        
    Returns:
        Dictionary mapping menu names to their URLs
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        navigation_urls = {}
        # Find the main navigation menu by id
        nav_menu = soup.find('nav', {'id': 'nav-main-menu'})
        if not nav_menu:
            logger.warning("Could not find main navigation menu in HTML")
            return navigation_urls

        # Find all <a> elements inside the navigation menu
        nav_links = nav_menu.find_all('a', class_='mdl-navigation__link')
        for link in nav_links:
            href = link.get('href', '')
            # Try to get the menu name from the subtitle div
            title_div = link.find('div', class_='cls-page--mainmenu-subtitle')
            if title_div:
                menu_name = title_div.get_text(strip=True)
            else:
                # Fallback: use aria-label or text
                menu_name = link.get('aria-label', link.text.strip())
            # Only use the relative URL (do not prepend domain)
            navigation_urls[menu_name] = href
            logger.info(f"Extracted navigation link: {menu_name} -> {href}")

        logger.info(f"Successfully extracted {len(navigation_urls)} navigation URLs")
        return navigation_urls

    except Exception as e:
        logger.error(f"Error parsing HTML for navigation URLs: {e}")
        return {}


# Legacy function name mapping for backward compatibility
async def handle_microsoft_login(page: Page, email: str, password: str) -> None:
    """Legacy function - use perform_microsoft_login and handle_post_login_flow instead."""
    await perform_microsoft_login(page, email, password)
    await handle_post_login_flow(page)