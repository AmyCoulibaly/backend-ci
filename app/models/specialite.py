"""Modèle Specialite médicale."""

from app.extensions import db


class Specialite(db.Model):
    """Domaine médical exercé par un ou plusieurs médecins."""

    __tablename__ = "specialite"

    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    medecins = db.relationship(
        "Medecin",
        back_populates="specialite",
        lazy="dynamic",
    )
