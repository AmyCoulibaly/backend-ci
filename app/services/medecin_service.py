"""Service métier pour la consultation des médecins et de leurs disponibilités."""

from app.extensions import db
from app.models import Disponibilite, Medecin, Specialite
from app.services.exceptions import NotFoundError


class MedecinService:
    """Logique métier liée aux médecins et à leurs créneaux horaires."""

    @staticmethod
    def lister_medecins(libelle_specialite: str | None = None) -> list[Medecin]:
        """Retourne la liste des médecins, optionnellement filtrée par spécialité."""
        query = Medecin.query.join(Specialite)
        if libelle_specialite:
            query = query.filter(
                Specialite.libelle.ilike(f"%{libelle_specialite.strip()}%")
            )
        return query.order_by(Medecin.nom.asc(), Medecin.prenom.asc()).all()

    @staticmethod
    def get_disponibilites_libres(id_medecin: int) -> list[Disponibilite]:
        """Retourne la liste des créneaux disponibles (est_reserve=False) d'un médecin."""
        medecin = db.session.get(Medecin, id_medecin)
        if medecin is None:
            raise NotFoundError(f"Médecin avec l'identifiant {id_medecin} introuvable.")

        return (
            Disponibilite.query.filter_by(id_medecin=id_medecin, est_reserve=False)
            .order_by(Disponibilite.date_heure_debut.asc())
            .all()
        )
