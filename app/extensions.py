"""Initialisation des extensions Flask (SQLAlchemy, Migrate, JWT, RESTX, CORS)."""

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

authorizations = {
    "Bearer Auth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Entrez : **Bearer &lt;JWT_TOKEN&gt;**",
    }
}



def create_api() -> Api:
    """
    Crée une nouvelle instance Flask-RESTX Api.

    Une instance par application est nécessaire : Flask-RESTX conserve une
    référence vers la première application initialisée, ce qui empêcherait
    l'enregistrement des routes sur les applications créées ensuite
    (tests pytest, workers multiples).
    """
    return Api(
        version="1.0",
        title="e-Santé Sénégal API",
        description=(
            "API RESTful de la plateforme de téléconsultation médicale "
            "e-Santé Sénégal"
        ),
        doc="/docs",
        authorizations=authorizations,
        security="Bearer Auth",
    )
