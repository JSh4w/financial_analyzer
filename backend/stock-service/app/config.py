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
        env_file='.env',
        env_file_encoding='utf-8',
        env_ignore_empty=True
    )
    FINNHUB_API_KEY : str = "demo_key"
    FINNHUB_BASE_URL : str = "https://finnhub.io/api/v1"
    ALPHA_VANTAGE_API_KEY : str = "demo_key"
    POSTGRESQL_KEY : str = "TEMP VAL"
    SUPABASE_URL : str = "demo_url"
    SUPABASE_KEY : str = "demo_key"
    ALPACA_TEST_URL: str = "wss://stream.data.alpaca.markets/v2/test"
    ALPACA_API_KEY : str =  "demo_key"
    ALPACA_API_SECRET : str = "demo_secret"
