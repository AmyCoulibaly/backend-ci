"""Modèles Ordonnance et LigneOrdonnance."""

from datetime import date

from app.extensions import db


class Ordonnance(db.Model):
    """Prescription médicale émise à l'issue d'un rendez-vous terminé."""

    __tablename__ = "ordonnance"

    id = db.Column(db.Integer, primary_key=True)
    date_emission = db.Column(db.Date, nullable=False, default=date.today)
    instructions = db.Column(db.Text, nullable=True)
    id_rendezvous = db.Column(
        db.Integer,
        db.ForeignKey("rendezvous.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    rendezvous = db.relationship("RendezVous", back_populates="ordonnance")
    lignes = db.relationship(
        "LigneOrdonnance",
        back_populates="ordonnance",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class LigneOrdonnance(db.Model):
    """Ligne de médicament prescrite au sein d'une ordonnance."""

    __tablename__ = "ligne_ordonnance"
    __table_args__ = (
        db.CheckConstraint("quantite > 0", name="check_quantite_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    medicament = db.Column(db.String(150), nullable=False)
    posologie = db.Column(db.String(150), nullable=False)
    duree = db.Column(db.String(100), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=1)
    id_ordonnance = db.Column(
        db.Integer,
        db.ForeignKey("ordonnance.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ordonnance = db.relationship("Ordonnance", back_populates="lignes")
