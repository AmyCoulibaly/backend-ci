"""Modèle Disponibilite (créneau horaire d'un médecin)."""

from app.extensions import db


class Disponibilite(db.Model):
    """Créneau horaire proposé par un médecin pour une téléconsultation."""

    __tablename__ = "disponibilite"
    __table_args__ = (
        db.CheckConstraint(
            "date_heure_fin > date_heure_debut",
            name="check_dates_disponibilite",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    date_heure_debut = db.Column(db.DateTime, nullable=False)
    date_heure_fin = db.Column(db.DateTime, nullable=False)
    est_reserve = db.Column(db.Boolean, nullable=False, default=False)
    id_medecin = db.Column(
        db.Integer,
        db.ForeignKey("medecin.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    medecin = db.relationship("Medecin", back_populates="disponibilites")
    rendezvous = db.relationship(
        "RendezVous",
        back_populates="disponibilite",
        uselist=False,
    )
