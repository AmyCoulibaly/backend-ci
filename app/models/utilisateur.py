"""Modèles Utilisateur, Patient et Medecin (héritage joint SQLAlchemy)."""

import enum
from datetime import datetime, timezone
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class RoleUtilisateur(str, enum.Enum):
    """Énumération des rôles utilisateurs."""

    PATIENT = "PATIENT"
    MEDECIN = "MEDECIN"


class Utilisateur(db.Model):
    """Table de base pour l'héritage joint Utilisateur -> Patient / Medecin."""

    __tablename__ = "utilisateur"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    telephone = db.Column(db.String(20), nullable=True)
    role = db.Column(
        db.Enum(RoleUtilisateur, name="role_utilisateur"),
        nullable=False,
    )
    date_creation = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __mapper_args__ = {
        "polymorphic_on": role,
        "polymorphic_identity": "UTILISATEUR",
    }

    def set_password(self, raw_password: str) -> None:
        """Hache et enregistre le mot de passe de l'utilisateur."""
        self.mot_de_passe = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Vérifie la correspondance du mot de passe avec le hash stocké."""
        return check_password_hash(self.mot_de_passe, raw_password)


class Patient(Utilisateur):
    """Modèle représentant un patient sur la plateforme e-Santé Sénégal."""

    __tablename__ = "patient"

    id = db.Column(
        db.Integer,
        db.ForeignKey("utilisateur.id", ondelete="CASCADE"),
        primary_key=True,
    )
    date_naissance = db.Column(db.Date, nullable=True)
    adresse = db.Column(db.String(255), nullable=True)

    rendezvous = db.relationship(
        "RendezVous",
        back_populates="patient",
        lazy="dynamic",
    )

    __mapper_args__ = {
        "polymorphic_identity": RoleUtilisateur.PATIENT,
    }


class Medecin(Utilisateur):
    """Modèle représentant un médecin sur la plateforme e-Santé Sénégal."""

    __tablename__ = "medecin"

    id = db.Column(
        db.Integer,
        db.ForeignKey("utilisateur.id", ondelete="CASCADE"),
        primary_key=True,
    )
    numero_ordre = db.Column(db.String(50), unique=True, nullable=False)
    biographie = db.Column(db.Text, nullable=True)
    tarif = db.Column(
        db.Numeric(8, 2),
        db.CheckConstraint("tarif >= 0", name="check_tarif_positif"),
        nullable=False,
        default=0.0,
    )
    id_specialite = db.Column(
        db.Integer,
        db.ForeignKey("specialite.id"),
        nullable=False,
    )

    specialite = db.relationship("Specialite", back_populates="medecins")
    disponibilites = db.relationship(
        "Disponibilite",
        back_populates="medecin",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    rendezvous = db.relationship(
        "RendezVous",
        back_populates="medecin",
        lazy="dynamic",
    )

    __mapper_args__ = {
        "polymorphic_identity": RoleUtilisateur.MEDECIN,
    }
