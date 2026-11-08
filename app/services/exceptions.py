"""Exceptions métier personnalisées pour découpler la logique métier de la couche HTTP."""


class ServiceError(Exception):
    """Exception de base pour la couche service."""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class BadRequestError(ServiceError):
    """Erreur 400 : Données d'entrée invalides."""

    status_code = 400


class UnauthorizedError(ServiceError):
    """Erreur 401 : Authentification échouée."""

    status_code = 401


class ForbiddenError(ServiceError):
    """Erreur 403 : Accès interdit (rôle ou propriété invalide)."""

    status_code = 403


class NotFoundError(ServiceError):
    """Erreur 404 : Ressource introuvable."""

    status_code = 404


class ConflictError(ServiceError):
    """Erreur 409 : Conflit d'état (ex: créneau déjà réservé ou email existant)."""

    status_code = 409


class UnprocessableEntityError(ServiceError):
    """Erreur 422 : Règle métier non respectée (ex: ordonnance sur RDV non terminé)."""

    status_code = 422
