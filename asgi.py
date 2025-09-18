import uvicorn
from src.api.app import app
from src.infrastructure.logging_config import setup_colored_logging

if __name__ == "__main__":
    setup_colored_logging()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None, access_log=True, server_header=False)