"""Modèle RendezVous et énumération StatutRendezVous."""

import enum
from datetime import datetime, timezone

from app.extensions import db


class StatutRendezVous(str, enum.Enum):
    """Cycle de vie des statuts d'un rendez-vous."""

    EN_ATTENTE = "EN_ATTENTE"
    ACCEPTE = "ACCEPTE"
    REFUSE = "REFUSE"
    ANNULE = "ANNULE"
    TERMINE = "TERMINE"


class RendezVous(db.Model):
    """Réservation d'un créneau de téléconsultation par un patient."""

    __tablename__ = "rendezvous"

    id = db.Column(db.Integer, primary_key=True)
    date_heure = db.Column(db.DateTime, nullable=False)
    motif = db.Column(db.String(255), nullable=True)
    statut = db.Column(
        db.Enum(StatutRendezVous, name="statut_rdv"),
        nullable=False,
        default=StatutRendezVous.EN_ATTENTE,
    )
    date_creation = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    id_patient = db.Column(
        db.Integer,
        db.ForeignKey("patient.id"),
        nullable=False,
        index=True,
    )
    id_medecin = db.Column(
        db.Integer,
        db.ForeignKey("medecin.id"),
        nullable=False,
        index=True,
    )
    id_disponibilite = db.Column(
        db.Integer,
        db.ForeignKey("disponibilite.id"),
        unique=True,
        nullable=True,
    )

    patient = db.relationship("Patient", back_populates="rendezvous")
    medecin = db.relationship("Medecin", back_populates="rendezvous")
    disponibilite = db.relationship(
        "Disponibilite",
        back_populates="rendezvous",
        uselist=False,
    )
    ordonnance = db.relationship(
        "Ordonnance",
        back_populates="rendezvous",
        uselist=False,
        cascade="all, delete-orphan",
    )
