"""Configuration de l'application Flask (Dev, Test, Prod)."""

import os
from datetime import timedelta


class Config:
    """Configuration de base commune à tous les environnements."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-esante-senegal")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-esante-senegal")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_EXPIRES_HOURS", "24"))
    )
    RESTX_MASK_SWAGGER = False
    RESTX_ERROR_404_HELP = False
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    PASSWORD_MIN_LENGTH = 8


class DevelopmentConfig(Config):
    """Configuration pour l'environnement de développement."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/esante_senegal_dev",
    )


class TestingConfig(Config):
    """Configuration pour l'exécution des tests automatisés (pytest)."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )
    JWT_SECRET_KEY = "test-jwt-secret-key-esante-senegal-2026"


class ProductionConfig(Config):
    """Configuration pour la mise en production."""

    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")

    REQUIRED_ENV_VARS = ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL")

    @classmethod
    def validate(cls) -> None:
        """Lève RuntimeError si une variable obligatoire est absente."""
        missing = [v for v in cls.REQUIRED_ENV_VARS if not os.getenv(v)]
        if missing:
            raise RuntimeError(
                "Variables d'environnement obligatoires en production : "
                + ", ".join(missing)
            )


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
