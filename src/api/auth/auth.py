import asyncio
import time
import colorlog
from fastapi import logger
import httpx
import hashlib
import base64
import secrets
import string
import os
from urllib.parse import urlparse, parse_qs, urlencode
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

from playwright.async_api import async_playwright, Page, expect

two_fa_queue = asyncio.Queue()

load_dotenv()

SCHULNETZ_CLIENT_ID = os.getenv("SCHULNETZ_CLIENT_ID")

if not all([SCHULNETZ_CLIENT_ID]):
    raise EnvironmentError("Missing required environment variables.")

log = logger.logger

# --- Robust logger configuration for colorlog and console output ---
import logging

# Set up colorlog handler if not already present
if not getattr(log, '_colorlog_configured', False):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
    ))
    log.handlers = []  # Remove any existing handlers
    log.addHandler(handler)
    log.setLevel(logging.INFO)  # Set to INFO or DEBUG as needed
    log._colorlog_configured = True
# --- End logger configuration ---


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
    log.info("Handling 2FA authentication...")
    log.info("Please provide 2FA token via /2FA endpoint...")
    two_fa_token = await asyncio.wait_for(two_fa_queue.get(), timeout=120)
    log.info("Received 2FA token")
    
    two_fa_field = 'input[type="tel"], input[name="otc"]'
    await expect(page.locator(two_fa_field)).to_be_visible(timeout=20000)
    await page.fill(two_fa_field, str(two_fa_token))
    submit_button = page.locator('#idSubmit_SAOTCC_Continue')
    if await submit_button.is_visible(timeout=5000):
        await submit_button.click()


async def handle_authenticator_code_display(page: Page) -> None:
    """Handle authenticator app code display."""
    log.info("Handling authenticator code display...")
    auth_number = page.locator("#idRichContext_DisplaySign")
    number_text = await auth_number.text_content()
    log.info(f"Authentication number found: {number_text}")
    
    log.info("Waiting for authentication dialog to close...")
    await auth_number.wait_for(state="hidden", timeout=60000)
    log.info("Authentication dialog has closed")


async def handle_security_info_update(page: Page) -> None:
    """Handle security information update dialog."""
    log.info("Handling security information update...")
    container = page.locator('[data-automation-id="SecurityInfoRegister"]')
    await container.wait_for(state="visible", timeout=5000)
    # TODO: handle the security info update form


async def handle_stay_signed_in(page: Page) -> None:
    """Handle stay signed in prompt."""
    log.info("Handling 'Stay signed in?' prompt...")
    yes_button = page.locator('#idSIButton9')
    await yes_button.wait_for(state="visible", timeout=3000)
    await yes_button.click()


async def handle_post_login_flow(page: Page) -> None:
    """Handle all post-login Microsoft authentication steps dynamically."""
    
    async def determine_and_handle_next_step():
        """Check what's present on the page and handle accordingly."""
        log.info("Determining next required step...")
        
        # Define all possible elements we might encounter
        selectors = {
            'account_protection': "#idSubmit_ProofUp_Redirect",
            'authenticator_code': "#idRichContext_DisplaySign", 
            'two_fa_input': 'input[type="tel"], input[name="otc"]',
            'security_info_update': '[data-automation-id="SecurityInfoRegister"]',
            'stay_signed_in': '#idSIButton9'
        }
        
        # Wait for any of these elements to appear (short timeout)
        for step_name, selector in selectors.items():
            try:
                element = page.locator(selector)
                await element.wait_for(state="visible", timeout=1000)
                log.info(f"Found: {step_name}")
                
                # Handle each step
                if step_name == 'account_protection':
                    await element.click()
                    await determine_and_handle_next_step()  # Recursively check next step
                    return
                elif step_name == 'authenticator_code':
                    await handle_authenticator_code_display()
                    await determine_and_handle_next_step()  # Check for next step
                    return
                elif step_name == 'two_fa_input':
                    await handle_2fa_input(page)
                    await determine_and_handle_next_step()  # Check for next step
                    return
                elif step_name == 'security_info_update':
                    await handle_security_info_update(page)
                    await determine_and_handle_next_step()  # Check for next step
                    return
                elif step_name == 'stay_signed_in':
                    await handle_stay_signed_in(page)
                    return  # This should be the final step
                    
            except Exception:
                continue  # Element not found, try next
        
        # If none of the expected elements are found, we might be done or on an unexpected page
        log.info("No expected post-login elements found - login may be complete")

    await determine_and_handle_next_step()


async def perform_microsoft_login(page: Page, email: str, password: str) -> None:
    """Handle the basic Microsoft login form (email and password entry)."""
    try:
        # Step 1: Enter email
        log.info("Entering Microsoft email...")
        email_input_selector = 'input[type="email"], input[name="loginfmt"]'
        await expect(page.locator(email_input_selector)).to_be_visible(timeout=20000)
        await page.fill(email_input_selector, email)
        email_button = page.locator('#idSIButton9')
        if await email_button.is_visible(timeout=5000):
            await email_button.click()

        # Step 2: Enter password
        log.info("Entering Microsoft password...")
        password_input_selector = 'input[type="password"], input[name="passwd"]'
        await expect(page.locator(password_input_selector)).to_be_visible(timeout=20000)
        await page.fill(password_input_selector, password)
        password_button = page.locator('#idSIButton9')
        if await password_button.is_visible(timeout=5000):
            await password_button.click()

        log.info("Basic Microsoft login form completed")

    except Exception as e:
        log.error(f"Error during Microsoft login form interaction: {e}")
        log.info(f"Current URL: {page.url}")
        log.info(f"Page content (partial): {(await page.content())[:1000]}")
        raise


def extract_auth_code_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract authorization code and state from URL parameters."""
    if 'code=' not in url:
        return None, None
    
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    auth_code = query_params.get("code", [None])[0]
    received_state = query_params.get("state", [None])[0]
    
    return auth_code, received_state


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
    
    log.info(f"Starting Microsoft authentication flow...")
    log.info(f"Navigating to {auth_url}...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to the authorization URL which will redirect to Microsoft
            await page.goto(auth_url, wait_until='load', timeout=60000)

            # Confirm we have landed on the Microsoft login page after the redirect
            log.info(f"Playwright landed on: {page.url}")
            if "login.microsoftonline.com" not in page.url:
                log.error("ERROR: Did not redirect to Microsoft login page as expected.")
                log.info(f"Final URL: {page.url}")
                log.info(f"Page content (partial): {(await page.content())[:1000]}")
                return None, None

            # Handle the interactive Microsoft login
            log.info("Starting interactive Microsoft login...")
            await perform_microsoft_login(page, email, password)
            
            # Handle any post-login flow (2FA, security updates, etc.)
            await handle_post_login_flow(page)

            # Extract authorization code from the final URL
            log.info(f"After Microsoft login flow, current URL: {page.url}")
            auth_code, received_state = extract_auth_code_from_url(page.url)
            
            if not auth_code:
                log.info("No auth code found immediately, waiting for additional redirects...")
                await asyncio.sleep(5)
                current_url = page.url
                log.info(f"After additional wait, current URL: {current_url}")
                auth_code, received_state = extract_auth_code_from_url(current_url)
            
            if auth_code:
                log.info(f"Successfully obtained Authorization Code: {auth_code[:30]}...")
                log.info(f"Received State: {received_state}")
            else:
                log.warning("No authorization code found after Microsoft authentication")
                
            return auth_code, received_state

        except Exception as e:
            log.error(f"Error during Microsoft authentication flow: {e}")
            # Uncomment the line below to save a screenshot for debugging on error
            # await page.screenshot(path="microsoft_auth_error.png")
            return None, None
        finally:
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

    log.info(f"Exchanging authorization code for tokens at {token_url}...")
    
    try:
        token_response = await httpx_client.post(
            token_url, data=token_data, headers=headers_for_token_exchange
        )
        token_response.raise_for_status()
        token_json = token_response.json()

        log.info("Token Exchange Successful!")
        log.info("Received Token Data:")
        log.info(token_json)

        access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")
        
        if access_token:
            log.info(f"Access Token obtained: {access_token[:30]}...")
            return access_token, refresh_token
        else:
            log.error("Access token not found in response.")
            return None, None

    except httpx.RequestError as e:
        log.error(f"HTTP error during token exchange: {e}")
        return None, None
    except httpx.HTTPStatusError as e:
        log.error(f"HTTP Status Error during token exchange: {e.response.status_code} - {e.response.text}")
        log.info(f"Response content: {e.response.text}")
        return None, None
    finally:
        await httpx_client.aclose()


def validate_state_parameter(expected_state: str, received_state: Optional[str]) -> bool:
    """Validate OAuth2 state parameter for CSRF protection."""
    if received_state and received_state != expected_state:
        log.warning("WARNING: State mismatch!")
        log.info(f"  Expected: {expected_state}")
        log.info(f"  Received: {received_state}")
        log.info("  This could indicate a security issue, but we'll continue...")
        return False
    elif received_state == expected_state:
        log.info("State validation passed.")
        return True
    else:
        log.info("Note: State validation skipped - no state received")
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
    log.info("Starting web authentication flow...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Step 1: Navigate to schulnetz.bbbaden.ch (will redirect to Microsoft)
            log.info("Navigating to https://schulnetz.bbbaden.ch/...")
            await page.goto("https://schulnetz.bbbaden.ch/", wait_until='load', timeout=60000)

            # Step 2: Handle Microsoft authentication
            log.info(f"Current URL after redirect: {page.url}")
            if "login.microsoftonline.com" in page.url:
                log.info("Handling Microsoft authentication...")
                await perform_microsoft_login(page, email, password)
                await handle_post_login_flow(page)
            else:
                log.warning("Expected Microsoft login redirect, but got different URL")

            # Step 3: Wait for final redirect back to schulnetz.bbbaden.ch with auth code
            log.info("Waiting for redirect back to schulnetz.bbbaden.ch...")
            await page.wait_for_url("https://schulnetz.bbbaden.ch/*", timeout=30000)
            
            current_url = page.url
            log.info(f"Final URL: {current_url}")

            # Step 4: Extract auth code from URL
            auth_code, _ = extract_auth_code_from_url(current_url)
            if not auth_code:
                log.error("No authorization code found in final URL")
                return None, None

            log.info(f"Successfully obtained auth code: {auth_code[:30]}...")

            # Step 5: Extract all cookies for session management
            cookies = await context.cookies()
            session_cookies = {}
            
            for cookie in cookies:
                # Store cookies as key-value pairs for easy use with httpx
                session_cookies[cookie['name']] = cookie['value']
                log.info(f"Captured cookie: {cookie['name']} (domain: {cookie['domain']})")

            log.info(f"Captured {len(session_cookies)} session cookies")
            
            return session_cookies, auth_code

        except Exception as e:
            log.error(f"Error during web authentication flow: {e}")
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
            "session_type": "web"
        }

    except Exception as e:
        log.error(f"Web authentication error: {e}")
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
            # Generate PKCE parameters and state/nonce
            code_verifier, code_challenge = generate_pkce_challenge()
            state = generate_random_string(32)
            nonce = generate_random_string(32)
            
            log.info("Generated OAuth2 parameters:")
            log.info(f"  Code Verifier: {code_verifier}")
            log.info(f"  Code Challenge: {code_challenge}")
            log.info(f"  State: {state}")
            log.info(f"  Nonce: {nonce}")

            # Step 1: Get authorization code from Microsoft
            auth_code, received_state = await get_microsoft_redirect_code(
                email, password, state, code_challenge, nonce
            )

            if not auth_code:
                return {
                    "success": False, 
                    "error": "Failed to obtain authorization code from Microsoft"
                }

            # Step 2: Validate state parameter
            validate_state_parameter(state, received_state)

            # Step 3: Exchange authorization code for tokens
            access_token, refresh_token = await exchange_code_for_tokens(auth_code, code_verifier)

            if access_token:
                return {
                    "success": True, 
                    "message": "Authentication completed successfully",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "session_type": "mobile"
                }
            else:
                return {
                    "success": False, 
                    "error": "Failed to exchange authorization code for tokens"
                }

        except Exception as e:
            log.error(f"Authentication error: {e}")
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
        log.error("Email and password are required")
        return None, None

    result = await authenticate_with_credentials(email, password, auth_type)
    
    if result["success"]:
        if auth_type == "mobile":
            return result["access_token"], result["refresh_token"]
        elif auth_type == "web":
            return result["session_cookies"], result["auth_code"]
    else:
        log.error(f"Authentication failed: {result['error']}")
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
        log.error(f"Authentication failed: {auth_result['error']}")
        return None
    
    session_cookies = auth_result["session_cookies"]
    
    # Step 2: Make the authenticated request
    url = f"https://schulnetz.bbbaden.ch/index.php?pageid={page_id}&id={resource_id}&transid={trans_id}"
    
    try:
        response = await make_authenticated_web_request(url, session_cookies)
        log.info(f"Request successful: {response.status_code}")
        log.info(f"Response length: {len(response.content)} bytes")
        return response.text
    
    except Exception as e:
        log.error(f"Request failed: {e}")
        return None


async def example_mobile_authenticated_request(email: str, password: str):
    """
    Example function showing how to make authenticated API requests with OAuth2 tokens.
    """
    # Step 1: Authenticate and get tokens
    auth_result = await authenticate_with_credentials(email, password, "mobile")
    
    if not auth_result["success"]:
        log.error(f"Authentication failed: {auth_result['error']}")
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
            log.info(f"API request successful: {response.status_code}")
            return response.json()
        except Exception as e:
            log.error(f"API request failed: {e}")
            return None


# Legacy function name mapping for backward compatibility
async def handle_microsoft_login(page: Page, email: str, password: str) -> None:
    """Legacy function - use perform_microsoft_login and handle_post_login_flow instead."""
    await perform_microsoft_login(page, email, password)
    await handle_post_login_flow(page)