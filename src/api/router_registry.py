import importlib
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, APIRouter
from fastapi.logger import logger


class RouterRegistry:
    def __init__(self, controllers_path: str = "src.api.controllers"):
        self.controllers_path = controllers_path
        self.registered_count = 0
    
    def auto_register(self, app: FastAPI, controllers_dir: Optional[Path] = None) -> int:
        if controllers_dir is None:
            # Get the directory where this registry file is located
            registry_file = Path(__file__).resolve()
            # This file is in /api/router_registry.py, controllers are in /api/controllers/
            controllers_dir = registry_file.parent / "controllers"
        
        logger.info(f"Scanning controllers directory: {controllers_dir}")
        
        if not controllers_dir.exists():
            logger.warning(f"Controllers directory not found: {controllers_dir}")
            return 0
        
        self.registered_count = 0
        
        for file_path in controllers_dir.glob("*.py"):
            if file_path.name.startswith("__") or file_path.name.startswith("."):
                continue
            
            module_name = f"{self.controllers_path}.{file_path.stem}"
            
            try:
                module = importlib.import_module(module_name)
                
                if hasattr(module, 'router') and isinstance(module.router, APIRouter):
                    app.include_router(module.router)
                    logger.info(f"Registered: {file_path.stem}")
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