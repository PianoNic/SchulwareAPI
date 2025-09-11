import os
from typing import Dict, Optional
from pathlib import Path

class AppConfigService:
    """Service to load application configuration from properties file"""
    
    def __init__(self):
        self._config: Dict[str, str] = {}
        self._load_properties()
    
    def _load_properties(self):
        """Load properties from application.properties file"""
        # Look for application.properties in project root
        project_root = Path(__file__).parent.parent.parent.parent
        properties_file = project_root / "application.properties"
        
        if properties_file.exists():
            with open(properties_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self._config[key.strip()] = value.strip()
    
    def get_version(self) -> str:
        """Get application version"""
        return self._config.get('APP_VERSION', 'unknown')
    
    def get_environment(self) -> str:
        """Get application environment (development/production)"""
        return self._config.get('APP_ENVIRONMENT', 'development')
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.get_environment().lower() == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.get_environment().lower() == 'development'
    
    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get any configuration value"""
        return self._config.get(key, default)

# Global instance
app_config = AppConfigService()