"""Export centralisé des services métier."""

from app.services.auth_service import AuthService
from app.services.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceError,
    UnauthorizedError,
    UnprocessableEntityError,
)
from app.services.medecin_service import MedecinService
from app.services.ordonnance_service import OrdonnanceService
from app.services.rendezvous_service import RendezVousService

__all__ = [
    "AuthService",
    "MedecinService",
    "RendezVousService",
    "OrdonnanceService",
    "ServiceError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
]
