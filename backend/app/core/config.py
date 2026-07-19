from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "stock-hanaro API"
    app_env: str = "development"
    app_version: str = "0.1.0"
    git_sha: str = "local"
    database_url: str = "sqlite:///./stock_hanaro.db"
    cors_origins: str = "http://localhost:3000"
    internal_job_secret: str = ""
    news_collect_limit: int = 40
    news_request_timeout_seconds: float = 15.0
    news_user_agent: str = "stock-hanaro/0.2 (+https://stock-hanaro.com)"
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_is_mock: bool = True
    dart_api_key: str = ""
    dart_page_count: int = 100
    dart_max_pages_per_market: int = 20
    kis_us_symbols: str = "AAPL,MSFT,NVDA,GOOGL,META,AMZN,TSLA,AVGO,AMD,JPM,V,LLY,UNH,XOM,CVX,WMT,COST,HD,GE,CAT"
    kis_request_interval_seconds: float = 0.12
    kis_realtime_enabled: bool = False
    kis_kr_symbols: str = "005930,000660,005380,373220"
    kis_max_realtime_stocks: int = 37
    bok_ecos_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"
    openai_timeout_seconds: float = 60.0

    @property
    def kis_base_url(self) -> str:
        return "https://openapivts.koreainvestment.com:29443" if self.kis_is_mock else "https://openapi.koreainvestment.com:9443"

    @property
    def us_symbols(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.kis_us_symbols.split(",") if symbol.strip()]

    @property
    def kr_symbols(self) -> list[str]:
        return [symbol.strip() for symbol in self.kis_kr_symbols.split(",") if symbol.strip()]

    @property
    def kis_ws_url(self) -> str:
        port = "31000" if self.kis_is_mock else "21000"
        return f"ws://ops.koreainvestment.com:{port}/tryitout"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
