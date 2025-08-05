import json
import os
import httpx
import asyncio
import concurrent.futures
from fastapi import FastAPI, Request, HTTPException, Response, Form
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Environment Variable Retrieval
# This function helps ensure that required environment variables are present.
def get_env_variable(var_name: str) -> str:
    """Retrieves an environment variable or raises an error if not found."""
    value = os.environ.get(var_name)
    if value is None:
        raise EnvironmentError(
            f"Required environment variable '{var_name}' is not set."
        )
    return value


# Load environment variables early to fail fast if missing
try:
    SCHULNETZ_API_BASE_URL = get_env_variable("SCHULNETZ_API_BASE_URL")
    SCHULNETZ_WEB_BASE_URL = get_env_variable("SCHULNETZ_WEB_BASE_URL")
    SCHULNETZ_API_KEY = get_env_variable("SCHULNETZ_API_KEY")
    SCHULNETZ_CLIENT_ID = get_env_variable("SCHULNETZ_CLIENT_ID")
    REDIRECT_URI = get_env_variable("REDIRECT_URI")
except EnvironmentError as e:
    print(f"Configuration Error: {e}")
    # Exit or handle the error gracefully, e.g., by not starting the app
    exit(1)


# 2. Load Endpoints from JSON
def load_endpoints(file_path: str) -> List[Dict[str, Any]]:
    """Loads API endpoint configurations from a JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {file_path} not found. "
              "Please create the endpoints.json file.")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {file_path}. "
              "Please check its format.")
        exit(1)


endpoints = load_endpoints("endpoints.json")

app = FastAPI(
    title="Schulnetz API Wrapper",
    description="A FastAPI application to wrap Schulnetz API endpoints.",
    version="1.0.0",
    redoc_url=None,
    docs_url="/"
)

# Store the current access token (in a real app, use proper storage like Redis)
current_access_token = None

# Health check endpoint for Docker monitoring
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring the service status."""
    return {"status": "healthy", "service": "SchulwareAPI"}

# Login endpoint
@app.post("/authorize", tags=["Authorization"])
async def login_and_get_token(email: str = Form(...), password: str = Form(...)):
    """Login with email and password to get access token."""
    global current_access_token
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    try:
        # Import auth functions
        from .auth import authenticate_with_credentials
        
        # Run authentication in a separate thread to avoid blocking the asyncio loop
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor, 
                authenticate_with_credentials, 
                email, 
                password
            )
        
        if result.get("success") and result.get("access_token"):
            current_access_token = result["access_token"]
            return {
                "message": "Login successful", 
                "access_token": current_access_token,
                "token_length": len(current_access_token)
            }
        else:
            raise HTTPException(
                status_code=401, 
                detail=result.get("error", "Authentication failed")
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

# Get current token status
@app.get("/status", tags=["Authorization"])
async def get_token_status():
    """Get the current authorization status."""
    return {
        "has_token": current_access_token is not None,
        "token_length": len(current_access_token) if current_access_token else 0,
        "token_preview": current_access_token[:10] + "..." if current_access_token else None
    }

# Clear access token
@app.delete("/authorize/clear", tags=["Authorization"])
async def clear_access_token():
    """Clear the current access token."""
    global current_access_token
    current_access_token = None
    return {"message": "Access token cleared successfully"}


# HTTPX client for making async requests
@app.on_event("startup")
async def startup_event():
    """Initializes the HTTPX client when the application starts."""
    app.state.httpx_client = httpx.AsyncClient(timeout=30.0)


@app.on_event("shutdown")
async def shutdown_event():
    """Closes the HTTPX client when the application shuts down."""
    await app.state.httpx_client.close()


# 3. Dynamically create API routes
for endpoint_config in endpoints:
    name = endpoint_config["name"]
    path = endpoint_config["path"]
    method = endpoint_config["method"].lower()
    url_path_suffix = endpoint_config["url_path"]
    allowed_query_params = endpoint_config.get("query_params", [])    # Define the handler function as a closure
    def create_handler(current_endpoint_config: Dict[str, Any]):
        async def handler(request: Request):
            target_url_path = current_endpoint_config["url_path"]
            target_base_url = None
            request_headers = {}            # Determine base URL and headers based on the target_url_path
            if target_url_path.startswith("/rest/v1/"):
                target_base_url = SCHULNETZ_API_BASE_URL
                # Use stored access token if available, otherwise fall back to API key
                auth_token = current_access_token if current_access_token else SCHULNETZ_API_KEY
                request_headers = {
                    "Referer": "https://schulnetz.web.app/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
                    "Accept": "application/json",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", '
                    '"Chromium";v="135"',
                    "sec-ch-ua-mobile": "?0",
                    "Authorization": f"Bearer {auth_token}",
                }
            elif target_url_path.startswith("/ngsw.json"):
                target_base_url = SCHULNETZ_WEB_BASE_URL
                request_headers = {
                    "accept": "*/*",
                    "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                    "priority": "u=1, i",
                    "referer": "https://schulnetz.web.app/main-sw.js",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Configuration error: Cannot determine base URL "
                    f"for path '{target_url_path}'."
                )

            target_url = f"{target_base_url}{target_url_path}"

            # Collect query parameters to forward
            params_to_forward = {}
            for param in current_endpoint_config.get(
                "query_params", []
            ):
                if param in request.query_params:
                    params_to_forward[param] = request.query_params[
                        param
                    ]

            try:
                print(
                    f"Proxying {current_endpoint_config['name']}: "
                    f"{current_endpoint_config['method']} {target_url} "
                    f"with params {params_to_forward}"
                )
                response = await app.state.httpx_client.request(
                    current_endpoint_config["method"],
                    target_url,
                    headers=request_headers,
                    params=params_to_forward,
                    content=await request.body()
                    if request.method
                    in ["POST", "PUT", "PATCH"]
                    else None,
                )
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    return JSONResponse(
                        content=response.json(),
                        status_code=response.status_code,
                        headers={"Content-Type": content_type},
                    )
                else:
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers={"Content-Type": content_type},
                    )

            except httpx.HTTPStatusError as e:
                print(f"HTTP Error from upstream for {name}: "
                      f"Status {e.response.status_code}, "
                      f"Detail: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Upstream API error "
                    f"({e.response.status_code}): {e.response.text}",
                )
            except httpx.RequestError as e:
                print(f"Network Error for {name}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Network error or upstream service unavailable: {e}",
                )
            except json.JSONDecodeError:
                print(
                    f"Warning: Upstream API for {name} returned "
                    "non-JSON where JSON was expected."
                )
                raise HTTPException(
                    status_code=500,
                    detail="Upstream API returned malformed or non-JSON "
                    "response.",
                )
            except Exception as e:
                print(f"An unexpected error occurred for {name}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"An unexpected error occurred: {e}",
                )

        return handler

    app.add_api_route(
        path,
        endpoint=create_handler(endpoint_config),
        methods=[method.upper()],
        tags=["Schulnetz API"],
        summary=f"Proxy for {name}",
    )