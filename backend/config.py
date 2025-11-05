"""
Configuration management for promoter form feature
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    supabase_metrics_bucket: str = os.getenv("SUPABASE_METRICS_BUCKET", "promoter-metrics")
    supabase_pdfs_bucket: str = os.getenv("SUPABASE_PDFS_BUCKET", "promoter-pdfs")
    
    # Auto-quote threshold (default £20,000)
    auto_quote_threshold: float = float(os.getenv("AUTO_QUOTE_THRESHOLD", "20000.0"))
    
    # Email settings
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "quotes@wildcapital.co.uk")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "Wild Capital BNG Quotes")
    
    # Reviewer emails (comma-separated)
    reviewer_emails_str: str = os.getenv("REVIEWER_EMAILS", "")
    
    @property
    def reviewer_emails(self) -> List[str]:
        """Parse reviewer emails from comma-separated string"""
        if not self.reviewer_emails_str:
            return []
        return [email.strip() for email in self.reviewer_emails_str.split(",") if email.strip()]
    
    # VAT rate
    vat_rate: float = float(os.getenv("VAT_RATE", "0.20"))
    
    # Quote validity
    quote_validity_days: int = int(os.getenv("QUOTE_VALIDITY_DAYS", "30"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
