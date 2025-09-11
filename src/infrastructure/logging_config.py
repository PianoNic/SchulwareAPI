import logging
import colorlog

class CustomFormatter(colorlog.ColoredFormatter):
    def format(self, record):
        # Map logger names to more user-friendly names
        name_mappings = {
            'uvicorn.error': 'server',
            'uvicorn.access': 'access',
            'uvicorn': 'server'
        }
        
        # Store original name and replace temporarily
        original_name = record.name
        record.name = name_mappings.get(record.name, record.name)
        
        # Format the message
        formatted = super().format(record)
        
        # Restore original name
        record.name = original_name
        
        return formatted

def setup_colored_logging():
    handler = colorlog.StreamHandler()
    formatter = CustomFormatter(
        '%(log_color)s%(levelname)s%(reset)s:%(white)s %(asctime)s - [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green', 
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
    )
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False
    
    # Configure Uvicorn loggers specifically
    uvicorn_loggers = [
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.access"),
        logging.getLogger("uvicorn.error")
    ]
    
    for uvicorn_logger in uvicorn_loggers:
        uvicorn_logger.handlers = []
        uvicorn_logger.addHandler(handler)
        uvicorn_logger.setLevel(logging.INFO)
        uvicorn_logger.propagate = False
    
    return root_logger

def get_logger(name: str = None):
    """Get a logger instance."""
    if name is None:
        name = "unknown"
    return logging.getLogger(name)