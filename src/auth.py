import time
import httpx
import hashlib
import base64
import secrets
import string
import os
from urllib.parse import urlparse, parse_qs, urlencode
from typing import Optional
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright, Page, expect

# Load environment variables from .env file
load_dotenv()

# --- Configuration from Environment Variables (non-sensitive only) ---
SCHULNETZ_CLIENT_ID = os.getenv("SCHULNETZ_CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Validate required environment variables
if not all([SCHULNETZ_CLIENT_ID, REDIRECT_URI]):
    raise EnvironmentError("Missing required environment variables. Please check your .env file.")


# --- Helper Functions (mostly unchanged) ---
def generate_random_string(length):
    """Generate a random alphanumeric string."""
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def generate_pkce_challenge():
    """Generate code_verifier and code_challenge for PKCE."""
    code_verifier = generate_random_string(128)  # PKCE recommends 43-128 chars
    s256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    # base64url encoding (RFC 4648 section 5)
    code_challenge = (
        base64.urlsafe_b64encode(s256).decode("utf-8").rstrip("=")
    )
    return code_verifier, code_challenge


def handle_microsoft_login(page: Page, email: str, password: str) -> None:
    """
    Handles the interactive Microsoft login process within Playwright.
    This function contains common Microsoft login steps.
    Selectors might vary slightly depending on your tenant's configuration or updates.
    """
    print("  Entering Microsoft email...")
    try:
        # Wait for the email input field and fill it
        email_input_selector = 'input[type="email"], input[name="loginfmt"]'
        expect(page.locator(email_input_selector)).to_be_visible(timeout=20000)
        page.fill(email_input_selector, email)
        page.press(email_input_selector, "Enter") # Simulate pressing Enter after filling
        # Alternatively, click the 'Next' button if present
        # page.click('input[type="submit"][value="Next"], button#idSIButton9')

        print("  Entering Microsoft password...")
        # Wait for the password input field to appear after email submission
        password_input_selector = 'input[type="password"], input[name="passwd"]'
        expect(page.locator(password_input_selector)).to_be_visible(timeout=20000)
        page.fill(password_input_selector, password)
        page.press(password_input_selector, "Enter")
        # Alternatively, click the 'Sign in' button
        # page.click('input[type="submit"][value="Sign in"], button#idSIButton9')        print("  Checking for 'Stay signed in?' prompt...")
        # Handle "Stay signed in?" prompt if it appears
  
        try:
            # Wait for either 'Yes' or 'No' button, and click 'Yes' (Ja)
            # Based on your HTML: #idSIButton9 is "Ja" (Yes), #idBtn_Back is "Nein" (No)
            stay_signed_in_button_yes = page.locator('#idSIButton9')
            stay_signed_in_button_no = page.locator('#idBtn_Back')



            # Wait for at least one of them to appear, but don't fail if neither does (it might skip this)
            if stay_signed_in_button_yes.is_visible(timeout=5000):
                print("  Clicking 'Ja' (Yes) to stay signed in...")
                stay_signed_in_button_yes.click()
            elif stay_signed_in_button_no.is_visible(timeout=5000):
                print("  Clicking 'Nein' (No) to not stay signed in...")
                stay_signed_in_button_no.click()
            else:
                print("  'Stay signed in?' prompt not found or skipped.")
        except Exception:
            print("  'Stay signed in?' prompt handling timed out or failed, proceeding...")

        # Try up to 3 times to find and click the "Stay signed in?" buttons
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"  Attempt {attempt + 1}/{max_attempts} to find 'Stay signed in?' prompt...")
                
                # Wait for either button to appear
                stay_signed_in_button_yes = page.locator('#idSIButton9')
                stay_signed_in_button_no = page.locator('#idBtn_Back')
                
                # Use Playwright's wait_for method to wait until one of the buttons is visible
                try:
                    # Wait for either button to become visible
                    page.wait_for_selector('#idSIButton9, #idBtn_Back', timeout=5000)
                    
                    if stay_signed_in_button_yes.is_visible():
                        print("  Clicking 'Ja' (Yes) to stay signed in...")
                        stay_signed_in_button_yes.click()
                        break  # Exit the loop if successful
                    elif stay_signed_in_button_no.is_visible():
                        print("  Clicking 'Nein' (No) to not stay signed in...")
                        stay_signed_in_button_no.click()
                        break  # Exit the loop if successful
                    
                except Exception:
                    print(f"  Buttons not found on attempt {attempt + 1}")
                    
                # If this is not the last attempt, wait 1 second before trying again
                if attempt < max_attempts - 1:
                    print("  Waiting 1 second before next attempt...")
                    time.sleep(1)
                
            except Exception as e:
                print(f"  Error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(1)
        else:
            print("  'Stay signed in?' prompt not found after 3 attempts, proceeding...")

    except Exception as e:
        print(f"Error during Microsoft login interaction: {e}")
        print(f"  Current URL: {page.url}")
        print(f"  Page content (partial): {page.content()[:1000]}")
        raise # Re-raise to stop execution if login failed

    print("  Microsoft login steps completed.")


def authenticate_with_credentials(email: str, password: str) -> dict:
    """
    Authenticate with provided email and password credentials.
    Returns a dictionary with the authentication result and access token.
    """
    try:
        # Run the main authentication flow with provided credentials
        access_token = main(email, password)
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


def main(email: Optional[str] = None, password: Optional[str] = None):
    """
    Main authentication function that can accept email and password parameters.
    If not provided, will use default values for backward compatibility.
    """
    # httpx.Client will be used for the final token exchange.
    httpx_client = httpx.Client(
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

    print("Generated PKCE and state/nonce:")
    print(f"  Code Verifier: {code_verifier}")
    print(f"  Code Challenge: {code_challenge}")
    print(f"  State: {state}")
    print(f"  Nonce: {nonce}\n")    # --- Step 2: Use Playwright to navigate to schulnetz.bbbaden.ch,
    #             let it redirect to Microsoft, then handle Microsoft login. ---
    auth_code = None
    received_state = None

    # We'll wait for redirect to schulnetz.web.app/callback instead of parsing REDIRECT_URI
    # since that's where the final code ends up according to the curl commands

    with sync_playwright() as p:        # Launch a browser instance in headless mode for background execution
        # Set headless=False for debugging to see what the browser is doing
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n--- Using Playwright for full login flow ---")
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
            print(f"Navigating to {auth_url}...")

            # Navigate to the authorization URL which will redirect to Microsoft
            page.goto(auth_url, wait_until='load', timeout=60000)

            # Confirm we have landed on the Microsoft login page after the redirect
            print(f"Playwright landed on: {page.url}")
            if "login.microsoftonline.com" not in page.url:
                print("ERROR: Did not redirect to Microsoft login page as expected.")
                print(f"Final URL: {page.url}")
                print(f"Page content (partial): {page.content()[:1000]}")
                browser.close()
                return            # Now, handle the interactive Microsoft login on the current page
            print("  Starting interactive Microsoft login...")
            handle_microsoft_login(page, email, password)

            # Add some debug output to see what's happening
            print(f"After Microsoft login, current URL: {page.url}")
            
            # Wait a moment for any additional redirects
            time.sleep(3)
            print(f"After waiting 3 seconds, current URL: {page.url}")
            
            # Check if we're already at a page that might have the auth code
            current_url = page.url
            if 'code=' in current_url:
                print("Found authorization code in current URL immediately after login")
                parsed_url = urlparse(current_url)
                query_params = parse_qs(parsed_url.query)
                auth_code = query_params.get("code", [None])[0]
                received_state = query_params.get("state", [None])[0]
                if auth_code:
                    print(f"Successfully obtained Authorization Code directly: {auth_code[:30]}...")
                    print(f"Received State: {received_state}")
                else:
                    auth_code = None            # Since we already have the auth code, we can proceed directly to token exchange
            # But let's also handle the case where the browser might do additional redirects
            if not auth_code:
                print("Waiting for any additional redirects or auth code...")
                
                # Wait a bit longer to see if there are any additional redirects
                time.sleep(5)
                current_url = page.url
                print(f"After additional wait, current URL: {current_url}")
                
                # Try to extract code from current URL again
                if 'code=' in current_url:
                    parsed_url = urlparse(current_url)
                    query_params = parse_qs(parsed_url.query)
                    auth_code = query_params.get("code", [None])[0]
                    received_state = query_params.get("state", [None])[0]
                    
                    if auth_code:
                        print(f"Successfully obtained Authorization Code from delayed URL: {auth_code[:30]}...")
                        print(f"Received State: {received_state}")
                
                if not auth_code:
                    print("Still no authorization code found after additional wait.")
                    print(f"Final URL: {page.url}")
                    print("Will attempt to proceed anyway...")
            
                print("Auth code extraction completed.")      

        except Exception as e:
            print(f"Error during Playwright automation: {e}")
            # Uncomment the line below to save a screenshot for debugging on error
            # page.screenshot(path="playwright_error_screenshot.png")
            # print(f"Screenshot saved to playwright_error_screenshot.png")
        finally:
            browser.close() 
            
    if not auth_code:
        print("Authorization code was not obtained. Cannot proceed to token exchange.")
        httpx_client.close()
        return None

    # Validate state parameter
    if received_state and received_state != state:
        print(f"WARNING: State mismatch!")
        print(f"  Expected: {state}")
        print(f"  Received: {received_state}")
        print(f"  This could indicate a security issue, but we'll continue...")
    elif received_state == state:
        print("State validation passed.")
    else:
        print("Note: State validation skipped - no state received or comparison not possible.")

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://schulnetz.web.app/",
        "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    print(f"\nExchanging authorization code for token at {token_url}...")
    try:
        # httpx client automatically handles cookies if it acquired any relevant ones.
        token_response = httpx_client.post(
            token_url, data=token_data, headers=headers_for_token_exchange
        )
        token_response.raise_for_status()
        token_json = token_response.json()

        print("\nToken Exchange Successful!")
        print("Received Token Data:")
        print(token_json)

        access_token = token_json.get("access_token")
        if access_token:
            print(f"\nAccess Token: {access_token}")
            return access_token
        else:
            print("Access token not found in response.")
            return None

    except httpx.RequestError as e:
        print(f"An HTTP error occurred during token exchange: {e}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"HTTP Status Error during token exchange: {e.response.status_code} - {e.response.text}")
        print(f"Response content: {e.response.text}")
        return None
    finally:
        httpx_client.close()


if __name__ == "__main__":
    main()