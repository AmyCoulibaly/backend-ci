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
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@db:5432/esante_senegal_prod",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
