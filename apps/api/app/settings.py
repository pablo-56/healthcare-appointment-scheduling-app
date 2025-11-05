from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    
    database_url: str = Field(default="postgresql+psycopg2://health:health@postgres:5432/health", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    jwt_secret: str = Field(default="dev-secret-change-me", alias="JWT_SECRET")
    otp_ttl_seconds: int = Field(default=300, alias="OTP_TTL_SECONDS")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    ehr_base: str = Field(default="http://ehr-connector:8100")
    
    s3_endpoint: str = Field(default="http://minio:9001", alias="S3_ENDPOINT")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_access_key: str = Field(default="minio", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minio12345", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="docs", alias="S3_BUCKET")
    s3_bucket_docs: str = "docs"
    signature_adapter_base: str = "http://signature-adapter:9000"
    signature_webhook_secret: str = "dev-signature-secret"  # HMAC secret for webhook
    billing_adapter_base: str = Field(default="http://billing-adapter:9200", alias="BILLING_ADAPTER_BASE")

    otlp_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    
    class Config: env_file = ".env"; extra = "ignore"
    
settings = Settings()
