import asyncio
from datetime import datetime
import re
from fastapi import APIRouter, Form, HTTPException, logger, Query
from src.api.auth.auth import authenticate_with_credentials, example_web_authenticated_request, make_authenticated_web_request, two_fa_queue
from src.application.services.token_service import token_service, ApplicationType
from bs4 import BeautifulSoup

log = logger.logger
router = APIRouter()
router_tag = ["Authorization"]

@router.post("/api/authenticate/mobile", tags=router_tag)
async def authenticate_mobile_api(email: str = Form(...), password: str = Form(...)):
    """
    Authenticate user for mobile API access.
    Returns tokens for REST API calls.
    """
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        log.info(f"Performing full mobile authentication for user: {email}")
        result = await authenticate_with_credentials(email, password, "mobile")
        
        if result.get("access_token") and result.get("refresh_token"):
            return {
                "success": True,
                "message": "Mobile API authentication successful with full login",
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": "Bearer",
                "expires_in": 3600,
                "app_type": ApplicationType.MOBILE_API,
                "source": "full_login"
            }
        else:
            raise HTTPException(
                status_code=401,
                detail=result.get("error", "Mobile authentication failed")
            )
            
    except Exception as e:
        log.error(f"Mobile authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mobile authentication error: {str(e)}")

@router.post("/api/authenticate/web", tags=router_tag)
async def authenticate_web_interface(email: str = Form(...), password: str = Form(...)):
    """
    Authenticate user for web interface access.
    Returns session information and navigation URLs including "Noten" URL.
    """
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        log.info(f"Performing full web authentication for user: {email}")
        auth_result = await authenticate_with_credentials(email, password, "web")
        
        session_cookies = auth_result["session_cookies"]
        auth_code = auth_result.get("auth_code")
        
        # Step 2: Process the auth code by visiting the callback URL to establish proper session
        if auth_code:
            try:
                # The URL we get from authenticate_with_credentials should contain the auth code
                # We need to visit this URL to let the server process the auth code and set proper session cookies
                callback_url = f"https://schulnetz.bbbaden.ch/?code={auth_code}"
                log.info(f"Processing auth code by visiting callback URL: {callback_url}")
                
                # Visit the callback URL to process the auth code
                callback_response = await make_authenticated_web_request(
                    callback_url, 
                    session_cookies,
                    follow_redirects=True  # Allow following redirects
                )
                
                # Update cookies from the callback response if any new ones were set
                if hasattr(callback_response, 'cookies'):
                    for cookie_name, cookie_value in callback_response.cookies.items():
                        session_cookies[cookie_name] = cookie_value
                        log.info(f"Updated session cookie: {cookie_name}")
                
            except Exception as e:
                log.warning(f"Error processing auth code callback: {e}")
                # Continue with existing cookies
        
        # Step 3: Now try to access the main page to get navigation menu
        try:
            main_page_response = await make_authenticated_web_request(
                "https://schulnetz.bbbaden.ch/index.php", 
                session_cookies,
                follow_redirects=True
            )
            
            # If we still get a redirect to login, try visiting the main page without index.php
            if main_page_response.status_code == 302:
                log.info("Got redirect, trying main domain...")
                main_page_response = await make_authenticated_web_request(
                    "https://schulnetz.bbbaden.ch/", 
                    session_cookies,
                    follow_redirects=True
                )
            
            main_page_response.raise_for_status()
            main_page_html = main_page_response.text
            
            log.info("Successfully retrieved main page HTML")
            
            # Step 4: Extract navigation URLs from HTML
            navigation_urls = extract_navigation_urls(main_page_html)
            
            # Step 5: Get the Noten URL specifically
            noten_url = navigation_urls.get("Noten")
            
            if noten_url:
                log.info(f"Successfully extracted Noten URL: {noten_url}")
            else:
                log.warning("Could not find Noten URL in navigation menu")
            
            return {
                "success": True,
                "message": "Web interface authentication successful",
                "session_cookies": session_cookies,
                "navigation_urls": navigation_urls,
                "noten_url": noten_url,
                "auth_code": auth_code,
                "app_type": ApplicationType.WEB_INTERFACE,
                "source": "full_login",
                "extracted_at": str(datetime.now())
            }
            
        except Exception as e:
            log.error(f"Error retrieving main page or extracting URLs: {e}")
            # Return authentication success even if URL extraction fails
            return {
                "success": True,
                "message": "Web interface authentication successful (URL extraction failed)",
                "session_cookies": session_cookies,
                "auth_code": auth_code,
                "app_type": ApplicationType.WEB_INTERFACE,
                "source": "full_login",
                "error": f"URL extraction failed: {str(e)}"
            }
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        log.error(f"Web authentication error for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Web authentication error: {str(e)}")


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
        
        # Find the main navigation menu
        nav_menu = soup.find('nav', {'class': 'mdl-navigation', 'id': 'nav-main-menu'})
        
        if not nav_menu:
            log.warning("Could not find main navigation menu in HTML")
            return navigation_urls
        
        # Find all navigation links
        nav_links = nav_menu.find_all('a', {'class': 'mdl-navigation__link'})
        
        for link in nav_links:
            try:
                # Get the href attribute
                href = link.get('href', '')
                
                # Find the menu title
                title_div = link.find('div', {'class': 'cls-page--mainmenu-subtitle'})
                if title_div:
                    menu_name = title_div.get_text(strip=True)
                    
                    # Convert relative URL to absolute URL if needed
                    if href.startswith('index.php'):
                        full_url = f"https://schulnetz.bbbaden.ch/{href}"
                    else:
                        full_url = href
                    
                    navigation_urls[menu_name] = full_url
                    log.info(f"Extracted navigation link: {menu_name} -> {href}")
                
            except Exception as e:
                log.warning(f"Error processing navigation link: {e}")
                continue
        
        log.info(f"Successfully extracted {len(navigation_urls)} navigation URLs")
        return navigation_urls
        
    except Exception as e:
        log.error(f"Error parsing HTML for navigation URLs: {e}")
        return {}

@router.post("/api/2FA", tags=router_tag)
async def pass_2fa_token(two_fa: int = Form(...)):
    try:
        await two_fa_queue.put(two_fa)
        log.info(f"2FA token {two_fa} received and put in queue.")
        return {"message": "2FA token received. Processing authentication."}
    except Exception as e:
        log.error(f"Error processing 2FA token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing 2FA token: {str(e)}")