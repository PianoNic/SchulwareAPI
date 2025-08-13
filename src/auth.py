import asyncio
import time
import colorlog
import httpx
import hashlib
import base64
import secrets
import string
import os
from urllib.parse import urlparse, parse_qs, urlencode
from typing import Optional
from dotenv import load_dotenv

from playwright.async_api import async_playwright, Page, expect

two_fa_queue = asyncio.Queue()

load_dotenv()

SCHULNETZ_CLIENT_ID = os.getenv("SCHULNETZ_CLIENT_ID")

if not all([SCHULNETZ_CLIENT_ID]):
    raise EnvironmentError("Missing required environment variables.")

logger = colorlog.getLogger("schulware")

def generate_random_string(length):
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
    )

def generate_pkce_challenge():
    code_verifier = generate_random_string(128)
    s256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (base64.urlsafe_b64encode(s256).decode("utf-8").rstrip("="))
    return code_verifier, code_challenge

async def handle_microsoft_login(page: Page, email: str, password: str) -> None:
    async def handle_2fa():
        """Handle 2FA input when required"""
        logger.info("Handling 2FA authentication...")
        logger.info("Please provide 2FA token via /2FA endpoint...")
        two_fa_token = await asyncio.wait_for(two_fa_queue.get(), timeout=120)
        logger.info("Received 2FA token")
        
        two_fa_field = 'input[type="tel"], input[name="otc"]'
        await expect(page.locator(two_fa_field)).to_be_visible(timeout=20000)
        await page.fill(two_fa_field, str(two_fa_token))
        submit_button = page.locator('#idSubmit_SAOTCC_Continue')
        if await submit_button.is_visible(timeout=5000):
            await submit_button.click()

    async def handle_authenticator_code():
        """Handle authenticator app code display"""
        logger.info("Handling authenticator code display...")
        auth_number = page.locator("#idRichContext_DisplaySign")
        number_text = await auth_number.text_content()
        logger.info(f"Authentication number found: {number_text}")
        
        logger.info("Waiting for authentication dialog to close...")
        await auth_number.wait_for(state="hidden", timeout=60000)
        logger.info("Authentication dialog has closed")

    async def handle_security_info_update():
        """Handle security information update dialog"""
        logger.info("Handling security information update...")
        container = page.locator('[data-automation-id="SecurityInfoRegister"]')
        await container.wait_for(state="visible", timeout=5000)
        # DOTO: handle the security info update form

    async def handle_stay_signed_in():
        """Handle stay signed in prompt"""
        logger.info("Handling 'Stay signed in?' prompt...")
        yes_button = page.locator('#idSIButton9')
        await yes_button.wait_for(state="visible", timeout=3000)
        await yes_button.click()

    async def determine_and_handle_next_step():
        """Check what's present on the page and handle accordingly"""
        logger.info("Determining next required step...")
        
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
                logger.info(f"Found: {step_name}")
                
                # Handle each step
                if step_name == 'account_protection':
                    await element.click()
                    await determine_and_handle_next_step()  # Recursively check next step
                    return
                elif step_name == 'authenticator_code':
                    await handle_authenticator_code()
                    await determine_and_handle_next_step()  # Check for next step
                    return
                elif step_name == 'two_fa_input':
                    await handle_2fa()
                    await determine_and_handle_next_step()  # Check for next step
                    return
                elif step_name == 'security_info_update':
                    await handle_security_info_update()
                    await determine_and_handle_next_step()  # Check for next step
                    return
                elif step_name == 'stay_signed_in':
                    await handle_stay_signed_in()
                    return  # This should be the final step
                    
            except Exception:
                continue  # Element not found, try next
        
        # If none of the expected elements are found, we might be done or on an unexpected page
        logger.info("No expected post-login elements found - login may be complete")

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
        
        # Step 3: Handle whatever comes next dynamically
        await determine_and_handle_next_step()

    except Exception as e:
        logger.error(f"Error during Microsoft login interaction: {e}")
        logger.info(f"Current URL: {page.url}")
        logger.info(f"Page content (partial): {(await page.content())[:1000]}")
        raise

    logger.info("Microsoft login completed successfully")

async def authenticate_with_credentials(email: str, password: str) -> dict:
    """
    Authenticate with provided email and password credentials.
    Returns a dictionary with the authentication result and access token.
    """
    try:
        # Run the main authentication flow with provided credentials
        access_token = await main(email, password)
        if access_token:
            return {
                "success": True, 
                "message": "Authentication completed successfully",
                "access_token": access_token
            }
        else:
            return {
                "success": False, 
                "error": "Failed to obtain access token"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def main(email: Optional[str] = None, password: Optional[str] = None):
    """
    Main authentication function that can accept email and password parameters.
    If not provided, will use default values for backward compatibility.
    """    # httpx.AsyncClient will be used for the final token exchange.
    httpx_client = httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    # --- Step 1: Generate PKCE, State, Nonce ---
    code_verifier, code_challenge = generate_pkce_challenge()
    state = generate_random_string(32)  # For CSRF protection
    nonce = generate_random_string(32)  # For replay protection in OpenID Connect    
    logger.info("Generated PKCE and state/nonce:")
    logger.info(f"  Code Verifier: {code_verifier}")
    logger.info(f"  Code Challenge: {code_challenge}")
    logger.info(f"  State: {state}")
    logger.info(f"  Nonce: {nonce}\n")
    
    # --- Step 2: Use Playwright to navigate to schulnetz.bbbaden.ch,
    #             let it redirect to Microsoft, then handle Microsoft login. ---
    auth_code = None
    received_state = None

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        logger.info("\n--- Using Playwright for full login flow ---")
        try:
            # Build the initial authorization URL with proper parameters
            auth_params = {
                "response_type": "code",
                "client_id": SCHULNETZ_CLIENT_ID,
                "state": state,
                "redirect_uri": "",  # Empty as shown in curl commands
                "scope": "openid ",  # Note the trailing space as in curl
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "nonce": nonce
            }
            
            auth_url = "https://schulnetz.bbbaden.ch/authorize.php?" + urlencode(auth_params)
            logger.info(f"Navigating to {auth_url}...")

            # Navigate to the authorization URL which will redirect to Microsoft
            await page.goto(auth_url, wait_until='load', timeout=60000)

            # Confirm we have landed on the Microsoft login page after the redirect
            logger.info(f"Playwright landed on: {page.url}")
            if "login.microsoftonline.com" not in page.url:
                logger.error("ERROR: Did not redirect to Microsoft login page as expected.")
                logger.info(f"Final URL: {page.url}")
                logger.info(f"Page content (partial): {await page.content()[:1000]}")
                await browser.close()
                return            # Now, handle the interactive Microsoft login on the current page
            logger.info("  Starting interactive Microsoft login...")
            await handle_microsoft_login(page, email, password)

            # Add some debug output to see what's happening
            logger.info(f"After Microsoft login, current URL: {page.url}")
            
            # Check if we're already at a page that might have the auth code
            current_url = page.url
            if 'code=' in current_url:
                logger.info("Found authorization code in current URL")
                parsed_url = urlparse(current_url)
                query_params = parse_qs(parsed_url.query)
                auth_code = query_params.get("code", [None])[0]
                received_state = query_params.get("state", [None])[0]
                if auth_code:
                    logger.info(f"Successfully obtained Authorization Code directly: {auth_code[:30]}...")
                    logger.info(f"Received State: {received_state}")
                else:
                    auth_code = None
            if not auth_code:
                logger.info("Waiting for any additional redirects or auth code...")
                
                # Wait a bit longer to see if there are any additional redirects
                await asyncio.sleep(5)
                current_url = page.url
                logger.info(f"After additional wait, current URL: {current_url}")
                
                # Try to extract code from current URL again
                if 'code=' in current_url:
                    parsed_url = urlparse(current_url)
                    query_params = parse_qs(parsed_url.query)
                    auth_code = query_params.get("code", [None])[0]
                    received_state = query_params.get("state", [None])[0]
                    
                    if auth_code:
                        logger.info(f"Successfully obtained Authorization Code from delayed URL: {auth_code[:30]}...")
                        logger.info(f"Received State: {received_state}")
                
                if not auth_code:
                    logger.warning("Still no authorization code found after additional wait.")
                    logger.info(f"Final URL: {page.url}")
                    logger.info("Will attempt to proceed anyway...")
            
                logger.info("Auth code extraction completed.")      

        except Exception as e:
            logger.error(f"Error during Playwright automation: {e}")
            # Uncomment the line below to save a screenshot for debugging on error
            # await page.screenshot(path="playwright_error_screenshot.png")
            # logger.info(f"Screenshot saved to playwright_error_screenshot.png")
        finally:
            await browser.close()

        if not auth_code:
            logger.error("Authorization code was not obtained. Cannot proceed to token exchange.")
            await httpx_client.aclose()
            return None

    # Validate state parameter
    if received_state and received_state != state:
        logger.warning(f"WARNING: State mismatch!")
        logger.info(f"  Expected: {state}")
        logger.info(f"  Received: {received_state}")
        logger.info(f"  This could indicate a security issue, but we'll continue...")
    elif received_state == state:
        logger.info("State validation passed.")
    else:
        logger.info("Note: State validation skipped - no state received or comparison not possible.")

    # --- Step 3: Exchange Authorization Code for Access Token (using httpx) ---
    # This step uses the 'code' obtained by Playwright.
    token_url = "https://schulnetz.bbbaden.ch/token.php"
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": "",  # Must match the one used throughout the flow (empty in curl commands)
        "code_verifier": code_verifier, # The one generated at the start of the script
        "client_id": SCHULNETZ_CLIENT_ID,
    }

    # Set headers for the token exchange request to match the working curl command exactly
    headers_for_token_exchange = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://schulnetz.web.app/",
        "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    logger.info(f"\nExchanging authorization code for token at {token_url}...")
    try:
        # httpx client automatically handles cookies if it acquired any relevant ones.
        token_response = await httpx_client.post(
            token_url, data=token_data, headers=headers_for_token_exchange
        )
        token_response.raise_for_status()
        token_json = token_response.json()

        logger.info("\nToken Exchange Successful!")
        logger.info("Received Token Data:")
        logger.info(token_json)

        access_token = token_json.get("access_token")
        if access_token:
            logger.info(f"\nAccess Token: {access_token}")
            return access_token
        else:
            logger.error("Access token not found in response.")
            return None

    except httpx.RequestError as e:
        logger.error(f"An HTTP error occurred during token exchange: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Status Error during token exchange: {e.response.status_code} - {e.response.text}")
        logger.info(f"Response content: {e.response.text}")
        return None
    finally:
        await httpx_client.aclose()