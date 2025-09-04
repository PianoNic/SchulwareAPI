import os

async def get_app_info_query_async():
    environment = os.environ.get('APP_ENVIRONMENT', 'unknown environment')
    version = os.environ.get('APP_VERSION', 'unknown version')
    return {
        "environment": environment, 
        "version": version
    }