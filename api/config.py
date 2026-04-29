from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI
    openai_api_key: str = ""

    # ElevenLabs
    elevenlabs_api_key: str = ""

    # Suno (cookie-based)
    suno_cookie: str = ""

    # Video lip-sync (choose one)
    sync_so_api_key: str = ""
    fal_api_key: str = ""

    # Video animation - Google Veo 3.1
    google_veo_api_key: str = ""

    # Reddit (optional)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "agente_contenido/1.0"

    # Facebook Graph API (optional)
    facebook_access_token: str = ""
    facebook_page_id: str = ""

    # Storage
    database_url: str = "sqlite+aiosqlite:///./agente_contenido.db"
    outputs_dir: str = "./outputs"
    brands_dir: str = "./brands"

    # CORS
    dashboard_url: str = "http://localhost:3000"

    # OpenAI model names
    text_model: str = "gpt-4o-mini"
    image_model: str = "dall-e-3"
    whisper_model: str = "whisper-1"


settings = Settings()
