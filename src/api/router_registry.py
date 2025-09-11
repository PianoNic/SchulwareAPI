import importlib
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, APIRouter, Request
from fastapi.logger import logger
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def get_client_ip(request: Request) -> str:
    """Get the real client IP address, handling reverse proxy scenarios."""
    # Check X-Forwarded-For header (most common)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP from comma-separated list
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip
    
    # Check X-Real-IP header (common with Nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct connection
    return get_remote_address(request)

# Shared limiter instance with reverse proxy support
shared_limiter = Limiter(key_func=get_client_ip)

# Shared rate limit exception handler
def shared_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


class SchulwareAPIRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_tag = None
        self._pending_routes = []  # Store routes that need path generation
    
    def _get_path_prefix_from_tag(self, tag: str):
        """Get the path prefix based on the tag"""
        tag_name = tag.lower().replace(" ", "")
        # Map specific tag names to path prefixes
        tag_to_path = {
            "app": "app",
            "auth": "authenticate", 
            "mobileproxy": "mobile",
            "webapi": "web"
        }
        return tag_to_path.get(tag_name, tag_name)
    
    def get(self, endpoint: str, **kwargs):
        """GET endpoint with auto-generated path: /api/{tag_prefix}/{endpoint}"""
        # If endpoint starts with '/' it's a full path, use original behavior
        if endpoint.startswith('/'):
            return super().get(endpoint, **kwargs)
        
        # Store the endpoint info for later path generation
        route_info = {
            'method': 'GET',
            'endpoint': endpoint.lstrip('/'),
            'kwargs': kwargs,
            'decorator_func': super().get
        }
        self._pending_routes.append(route_info)
        
        # Return a placeholder decorator that will be replaced during registration
        def decorator(func):
            route_info['func'] = func
            return func
        return decorator
    
    def post(self, endpoint: str, **kwargs):
        """POST endpoint with auto-generated path: /api/{tag_prefix}/{endpoint}"""
        # If endpoint starts with '/' it's a full path, use original behavior
        if endpoint.startswith('/'):
            return super().post(endpoint, **kwargs)
            
        route_info = {
            'method': 'POST',
            'endpoint': endpoint.lstrip('/'),
            'kwargs': kwargs,
            'decorator_func': super().post
        }
        self._pending_routes.append(route_info)
        
        def decorator(func):
            route_info['func'] = func
            return func
        return decorator
    
    def put(self, endpoint: str, **kwargs):
        """PUT endpoint with auto-generated path: /api/{tag_prefix}/{endpoint}"""
        # If endpoint starts with '/' it's a full path, use original behavior
        if endpoint.startswith('/'):
            return super().put(endpoint, **kwargs)
            
        route_info = {
            'method': 'PUT',
            'endpoint': endpoint.lstrip('/'),
            'kwargs': kwargs,
            'decorator_func': super().put
        }
        self._pending_routes.append(route_info)
        
        def decorator(func):
            route_info['func'] = func
            return func
        return decorator
    
    def delete(self, endpoint: str, **kwargs):
        """DELETE endpoint with auto-generated path: /api/{tag_prefix}/{endpoint}"""
        # If endpoint starts with '/' it's a full path, use original behavior
        if endpoint.startswith('/'):
            return super().delete(endpoint, **kwargs)
            
        route_info = {
            'method': 'DELETE',
            'endpoint': endpoint.lstrip('/'),
            'kwargs': kwargs,
            'decorator_func': super().delete
        }
        self._pending_routes.append(route_info)
        
        def decorator(func):
            route_info['func'] = func
            return func
        return decorator
    
    def patch(self, endpoint: str, **kwargs):
        """PATCH endpoint with auto-generated path: /api/{tag_prefix}/{endpoint}"""
        # If endpoint starts with '/' it's a full path, use original behavior
        if endpoint.startswith('/'):
            return super().patch(endpoint, **kwargs)
            
        route_info = {
            'method': 'PATCH',
            'endpoint': endpoint.lstrip('/'),
            'kwargs': kwargs,
            'decorator_func': super().patch
        }
        self._pending_routes.append(route_info)
        
        def decorator(func):
            route_info['func'] = func
            return func
        return decorator
    
    def _finalize_auto_routes(self):
        """Called after auto_tag is set to create the actual routes"""
        if not self.auto_tag or len(self.auto_tag) == 0:
            return
            
        path_prefix = self._get_path_prefix_from_tag(self.auto_tag[0])
        
        for route_info in self._pending_routes:
            full_path = f"/api/{path_prefix}/{route_info['endpoint']}"
            # Apply the actual decorator with the generated path
            route_info['decorator_func'](full_path, **route_info['kwargs'])(route_info['func'])
        
        # Clear pending routes
        self._pending_routes = []
    
    # Keep auto_* methods for backward compatibility
    def auto_get(self, endpoint: str, **kwargs):
        """Alias for get() - kept for backward compatibility"""
        return self.get(endpoint, **kwargs)
    
    def auto_post(self, endpoint: str, **kwargs):
        """Alias for post() - kept for backward compatibility"""
        return self.post(endpoint, **kwargs)
    
    def auto_put(self, endpoint: str, **kwargs):
        """Alias for put() - kept for backward compatibility"""
        return self.put(endpoint, **kwargs)
    
    def auto_delete(self, endpoint: str, **kwargs):
        """Alias for delete() - kept for backward compatibility"""
        return self.delete(endpoint, **kwargs)
    
    def auto_patch(self, endpoint: str, **kwargs):
        """Alias for patch() - kept for backward compatibility"""
        return self.patch(endpoint, **kwargs)


class RouterRegistry:
    def __init__(self, controllers_path: str = "src.api.controllers"):
        self.controllers_path = controllers_path
        self.registered_count = 0
    
    def _generate_tag_from_filename(self, filename: str) -> str:
        """Generate a router tag from the controller filename.
        
        Examples:
        - app_controller.py -> App
        - auth_controller.py -> Auth
        - mobile_proxy_controller.py -> Mobile Proxy
        - web_api_controller.py -> Web API
        """
        # Remove _controller.py suffix and split by underscores
        name = filename.replace("_controller", "").replace(".py", "")
        words = name.split("_")
        
        # Handle special cases and capitalize each word
        formatted_words = []
        for word in words:
            if word.lower() == "api":
                formatted_words.append("API")
            else:
                formatted_words.append(word.capitalize())
        
        return " ".join(formatted_words)
    
    def _generate_operation_id_from_path(self, path: str, method: str = "") -> str:
        """Generate an operationId from the endpoint path.
        
        Examples:
        - /api/app-info -> app-info
        - /api/authenticate/unified -> authenticate-unified
        - /api/mobile/userInfo -> mobile-userInfo
        - /api/web/unterricht -> web-unterricht
        """
        # Remove leading/trailing slashes and split by '/'
        clean_path = path.strip("/")
        parts = clean_path.split("/")
        
        # Remove 'api' prefix if present
        if parts and parts[0].lower() == "api":
            parts = parts[1:]
        
        # Join remaining parts with hyphens, preserving original casing
        if parts:
            return "-".join(parts)
        else:
            return "root"

    def auto_register(self, app: FastAPI, controllers_dir: Optional[Path] = None) -> int:
        if controllers_dir is None:
            registry_file = Path(__file__).resolve()
            controllers_dir = registry_file.parent / "controllers"
        
        logger.info(f"Scanning controllers directory: {controllers_dir}")
        
        if not controllers_dir.exists():
            logger.warning(f"Controllers directory not found: {controllers_dir}")
            return 0
        
        self.registered_count = 0
        
        # Add exception handler and limiter state once for the entire app
        app.add_exception_handler(RateLimitExceeded, shared_rate_limit_exceeded_handler)
        app.state.limiter = shared_limiter
        
        for file_path in controllers_dir.glob("*.py"):
            if file_path.name.startswith("__") or file_path.name.startswith("."):
                continue
            
            module_name = f"{self.controllers_path}.{file_path.stem}"
            
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, 'router') and isinstance(module.router, APIRouter):
                    # Generate and set auto tag
                    auto_tag = self._generate_tag_from_filename(file_path.name)
                    
                    # Set auto_tag on SchulwareAPIRouter instances and update route tags
                    if isinstance(module.router, SchulwareAPIRouter):
                        module.router.auto_tag = [auto_tag]
                        # Set router_tag in module namespace for backward compatibility
                        setattr(module, 'router_tag', [auto_tag])
                        
                        # Finalize any auto routes that were defined with auto_get, auto_post, etc.
                        module.router._finalize_auto_routes()
                        
                        # Update tags and names on all existing routes
                        for route in module.router.routes:
                            # Auto-generate tags if not present
                            if hasattr(route, 'tags') and (not route.tags or route.tags == []):
                                route.tags = [auto_tag]
                            
                            # Auto-generate operationId based on path
                            if hasattr(route, 'path') and hasattr(route, 'operation_id'):
                                # Only set operationId if not already explicitly set
                                if not route.operation_id:
                                    # Get the HTTP method from the route
                                    method = getattr(route, 'methods', set())
                                    method_str = list(method)[0] if method else ""
                                    route.operation_id = self._generate_operation_id_from_path(route.path, method_str)
                    
                    app.include_router(module.router)
                    logger.info(f"Registered: {file_path.stem} with tag '{auto_tag}'")
                    self.registered_count += 1
                else:
                    logger.debug(f"No router found in: {module_name}")
                    
            except ImportError as e:
                logger.error(f"Import failed: {module_name} - {e}")
            except Exception as e:
                logger.error(f"Registration error: {module_name} - {e}")
        
        logger.info(f"Successfully registered {self.registered_count} controller(s)")
        return self.registered_count

# Global instance for easy use
router_registry = RouterRegistry()