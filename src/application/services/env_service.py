import os
from dotenv import load_dotenv

def load_env():
    load_dotenv()

def get_env_variable(var_name: str, default: str | None = None) -> str:
    value = os.environ.get(var_name, default)
    if value is None:
        raise EnvironmentError(f"Required environment variable '{var_name}' is not set.")
    return value