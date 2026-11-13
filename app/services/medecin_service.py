"""Service métier pour la consultation des médecins et de leurs disponibilités."""

from datetime import datetime

from app.extensions import db
from app.models import Disponibilite, Medecin, Specialite
from app.services.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)


def _parse_datetime(valeur: str, champ: str) -> datetime:
    """Convertit une date ISO 8601 en datetime naïf (heure locale du créneau)."""
    try:
        dt = datetime.fromisoformat(str(valeur).replace("Z", "+00:00"))
    except ValueError as exc:
        raise BadRequestError(f"Le champ '{champ}' doit être une date ISO 8601.") from exc
    return dt.replace(tzinfo=None)


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

    @staticmethod
    def get_toutes_disponibilites(id_medecin: int) -> list[Disponibilite]:
        """Retourne tous les créneaux d'un médecin (libres et réservés)."""
        if db.session.get(Medecin, id_medecin) is None:
            raise NotFoundError(f"Médecin avec l'identifiant {id_medecin} introuvable.")
        return (
            Disponibilite.query.filter_by(id_medecin=id_medecin)
            .order_by(Disponibilite.date_heure_debut.asc())
            .all()
        )

    @staticmethod
    def creer_disponibilite(id_medecin: int, debut: str, fin: str) -> Disponibilite:
        """Ajoute un créneau au planning du médecin (refuse un chevauchement : 409)."""
        if not debut or not fin:
            raise BadRequestError("Les champs 'date_heure_debut' et 'date_heure_fin' sont obligatoires.")
        d1 = _parse_datetime(debut, "date_heure_debut")
        d2 = _parse_datetime(fin, "date_heure_fin")
        if d2 <= d1:
            raise BadRequestError("La fin du créneau doit être postérieure à son début.")

        chevauche = Disponibilite.query.filter(
            Disponibilite.id_medecin == id_medecin,
            Disponibilite.date_heure_debut < d2,
            Disponibilite.date_heure_fin > d1,
        ).first()
        if chevauche is not None:
            raise ConflictError("Ce créneau chevauche un créneau existant.")

        dispo = Disponibilite(
            date_heure_debut=d1,
            date_heure_fin=d2,
            est_reserve=False,
            id_medecin=id_medecin,
        )
        db.session.add(dispo)
        db.session.commit()
        return dispo

    @staticmethod
    def supprimer_disponibilite(id_disponibilite: int, id_medecin: int) -> None:
        """Supprime un créneau libre appartenant au médecin (409 s'il est réservé)."""
        dispo = db.session.get(Disponibilite, id_disponibilite)
        if dispo is None:
            raise NotFoundError(f"Créneau {id_disponibilite} introuvable.")
        if dispo.id_medecin != id_medecin:
            raise ForbiddenError("Ce créneau n'appartient pas à ce médecin.")
        if dispo.est_reserve:
            raise ConflictError("Impossible de supprimer un créneau déjà réservé.")
        db.session.delete(dispo)
        db.session.commit()
