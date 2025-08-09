"""Configuration class to handle env variables and settings
to be replaced by SQLAlcehmy and databases variables once mulit-user"""

from pydantic_settings import BaseSettings, SettingsConfigDict

#https://medium.com/@jayanthsarma8/config-management-with-pydantic-base-settings-de22b79fd191

class Settings(BaseSettings):
    """
    Configuration class for managing environment variables and settings.
    This class utilizes pydantic's BaseSettings to handle configuration settings
    from environment variables. It is designed to be flexible and easy to use,
    making it suitable for a wide range of applications. ".env" automatically loaded
    """
    model_config = SettingsConfigDict(
        env_file='backend/python-service/.env',
        env_file_encoding='utf-8'
    )
    FINNHUB_API_KEY : str
    FINNHUB_BASE_URL : str
    ALPHA_VANTAGE_API_KEY : str
    POSTGRESQL_KEY : str = "TEMP VAL"
    SUPABASE_URL : str
    SUPABASE_KEY : str
    GOCARDLESS_KEY : str
    GOCARDLESS_ID  : str
