"""Décorateurs d'autorisation JWT basés sur les rôles (PATIENT / MEDECIN)."""

from functools import wraps
from typing import Any, Callable

from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.models import RoleUtilisateur
from app.services.exceptions import ForbiddenError


def role_required(*allowed_roles: RoleUtilisateur) -> Callable[..., Any]:
    """Vérifie la présence d'un JWT valide et d'un rôle autorisé dans les claims."""
    allowed_values = {r.value if isinstance(r, RoleUtilisateur) else str(r) for r in allowed_roles}

    def wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def decorator(*args: Any, **kwargs: Any) -> Any:
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role")
            if user_role not in allowed_values:
                raise ForbiddenError(
                    f"Accès refusé : le rôle '{user_role}' n'est pas autorisé pour cette ressource. "
                    f"Rôle(s) requis : {', '.join(sorted(allowed_values))}."
                )
            return fn(*args, **kwargs)

        return decorator

    return wrapper
