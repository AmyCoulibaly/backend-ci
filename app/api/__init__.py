"""Enregistrement des namespaces Flask-RESTX."""

from app.api.auth import auth_ns
from app.api.medecins import medecins_ns
from app.api.ordonnances import ordonnances_ns
from app.api.rendezvous import rendezvous_ns

__all__ = [
    "auth_ns",
    "medecins_ns",
    "rendezvous_ns",
    "ordonnances_ns",
]
