"""Application Factory Flask pour le microservice backend-ci (e-Santé Sénégal)."""

import os
from flask import Flask, jsonify
from sqlalchemy import text

from app.api import auth_ns, medecins_ns, ordonnances_ns, rendezvous_ns
from app.cli import register_cli_commands
from app.config import CONFIG_BY_NAME
from app.extensions import cors, create_api, db, jwt, migrate
from app.services.exceptions import ServiceError


def create_app(config_name: str | None = None) -> Flask:
    """Crée et configure une instance de l'application Flask (Application Factory)."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "default")

    app = Flask(__name__)
    config_class = CONFIG_BY_NAME.get(config_name, CONFIG_BY_NAME["default"])
    app.config.from_object(config_class)

    # Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    # Endpoint public de healthcheck pour Docker / Jenkins
    @app.route("/health", methods=["GET"])
    def health_check():
        """Vérifie l'état de santé de l'application et de la connexion base de données."""
        db_status = "healthy"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db_status = "unhealthy"
            return (
                jsonify(
                    {
                        "status": "degraded",
                        "service": "e-sante-senegal-backend",
                        "database": db_status,
                    }
                ),
                503,
            )

        return (
            jsonify(
                {
                    "status": "UP",
                    "service": "e-sante-senegal-backend",
                    "database": db_status,
                }
            ),
            200,
        )

    # Initialisation de Flask-RESTX (une instance Api par application)
    api = create_api()
    api.init_app(app)
    for namespace in (auth_ns, medecins_ns, rendezvous_ns, ordonnances_ns):
        api.add_namespace(namespace)

    # Gestionnaires d'erreurs centralisés
    @api.errorhandler(ServiceError)
    def handle_service_error(error: ServiceError):
        """Transforme toute ServiceError métier en réponse JSON HTTP normalisée."""
        return {"message": error.message}, error.status_code

    @app.errorhandler(ServiceError)
    def handle_app_service_error(error: ServiceError):
        """Fallback Flask pour les ServiceError hors contexte RESTX."""
        return jsonify({"message": error.message}), error.status_code

    # Enregistrement des commandes CLI (flask seed-db)
    register_cli_commands(app)

    return app
