from src.application.services.app_config_service import app_config
import datetime

async def get_app_info_query_async():
    return {
        "version": app_config.get_version(),
        "environment": app_config.get_environment(), 
        "is_production": app_config.is_production(),
        "build_timestamp": datetime.datetime.now().isoformat()
    }