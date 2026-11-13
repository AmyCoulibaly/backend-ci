"""Service métier pour la gestion des rendez-vous (RendezVousService)."""

from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Disponibilite, Patient, RendezVous, RoleUtilisateur, StatutRendezVous
from app.services.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableEntityError,
)

# Transitions de statut autorisées (diagramme d'états du document de modélisation)
TRANSITIONS_AUTORISEES = {
    StatutRendezVous.EN_ATTENTE: {
        StatutRendezVous.ACCEPTE,
        StatutRendezVous.REFUSE,
        StatutRendezVous.ANNULE,
    },
    StatutRendezVous.ACCEPTE: {StatutRendezVous.TERMINE, StatutRendezVous.ANNULE},
    StatutRendezVous.REFUSE: set(),
    StatutRendezVous.ANNULE: set(),
    StatutRendezVous.TERMINE: set(),
}


class RendezVousService:
    """Logique métier pour la réservation, la consultation et la mise à jour des RDV."""

    @staticmethod
    def reserver(
        id_patient: int,
        id_disponibilite: int,
        motif: str | None = None,
    ) -> RendezVous:
        """
        Crée un rendez-vous pour un patient sur un créneau disponible.
        Règle métier critique :
        - Vérifie de manière atomique (verrouillage SELECT ... FOR UPDATE + contrainte UNIQUE)
          si la Disponibilite est libre (est_reserve == False).
        - Marque est_reserve = True et crée le RendezVous.
        - Lève ConflictError (409 Conflict) si le créneau est déjà réservé.
        """
        patient = db.session.get(Patient, id_patient)
        if patient is None:
            raise NotFoundError(f"Patient avec l'id {id_patient} introuvable.")

        try:
            disponibilite = (
                db.session.query(Disponibilite)
                .filter(Disponibilite.id == id_disponibilite)
                .with_for_update()
                .first()
            )
            if disponibilite is None:
                raise NotFoundError(
                    f"Disponibilité avec l'id {id_disponibilite} introuvable."
                )

            if disponibilite.est_reserve:
                raise ConflictError(
                    "Ce créneau de disponibilité est déjà réservé par un autre patient."
                )

            disponibilite.est_reserve = True

            rendezvous = RendezVous(
                date_heure=disponibilite.date_heure_debut,
                motif=motif,
                statut=StatutRendezVous.EN_ATTENTE,
                id_patient=id_patient,
                id_medecin=disponibilite.id_medecin,
                id_disponibilite=disponibilite.id,
            )
            db.session.add(rendezvous)
            db.session.commit()
            return rendezvous
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError(
                "Conflit d'accès concurrent : ce créneau vient d'être réservé."
            ) from exc
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def lister_rendezvous_medecin(
        id_medecin: int,
        filtre_date: str | None = None,
    ) -> list[RendezVous]:
        """Liste les rendez-vous d'un médecin, avec filtre optionnel (?date=today ou YYYY-MM-DD)."""
        return RendezVousService.lister_rendezvous(
            id_utilisateur=id_medecin,
            role=RoleUtilisateur.MEDECIN.value,
            filtre_date=filtre_date,
        )

    @staticmethod
    def lister_rendezvous(
        id_utilisateur: int,
        role: str,
        filtre_date: str | None = None,
    ) -> list[RendezVous]:
        """
        Liste les rendez-vous de l'utilisateur connecté :
        - MEDECIN : son agenda ; PATIENT : son historique de rendez-vous.
        Filtre optionnel ?date=today ou YYYY-MM-DD.
        """
        if role == RoleUtilisateur.PATIENT.value:
            query = RendezVous.query.filter_by(id_patient=id_utilisateur)
        else:
            query = RendezVous.query.filter_by(id_medecin=id_utilisateur)

        if filtre_date:
            filtre_normalise = filtre_date.strip().lower()
            if filtre_normalise == "today":
                cible_date = date.today()
            else:
                try:
                    cible_date = datetime.strptime(filtre_normalise, "%Y-%m-%d").date()
                except ValueError as exc:
                    raise BadRequestError(
                        "Paramètre 'date' invalide. Utilisez 'today' ou 'YYYY-MM-DD'."
                    ) from exc

            query = query.filter(func.date(RendezVous.date_heure) == cible_date)

        return query.order_by(RendezVous.date_heure.asc()).all()

    @staticmethod
    def mettre_a_jour_statut(
        id_rendezvous: int,
        id_medecin: int,
        nouveau_statut_str: str,
    ) -> RendezVous:
        """
        Met à jour le statut d'un rendez-vous par le médecin propriétaire.
        Règle métier critique :
        - Si le nouveau statut est ANNULE (ou REFUSE), libère la Disponibilite (est_reserve=False)
          et détache id_disponibilite pour permettre une nouvelle réservation du créneau.
        """
        rendezvous = db.session.get(RendezVous, id_rendezvous)
        if rendezvous is None:
            raise NotFoundError(
                f"Rendez-vous avec l'id {id_rendezvous} introuvable."
            )

        if rendezvous.id_medecin != id_medecin:
            raise ForbiddenError(
                "Vous n'êtes pas autorisé à modifier le rendez-vous d'un autre médecin."
            )

        try:
            nouveau_statut = StatutRendezVous((nouveau_statut_str or "").strip().upper())
        except ValueError as exc:
            raise BadRequestError(
                f"Statut '{nouveau_statut_str}' invalide. Valeurs autorisées : "
                f"{', '.join(s.value for s in StatutRendezVous)}."
            ) from exc

        if nouveau_statut not in TRANSITIONS_AUTORISEES[rendezvous.statut]:
            raise UnprocessableEntityError(
                f"Transition interdite : {rendezvous.statut.value} -> {nouveau_statut.value}."
            )

        rendezvous.statut = nouveau_statut

        if nouveau_statut in (StatutRendezVous.ANNULE, StatutRendezVous.REFUSE):
            if rendezvous.disponibilite is not None:
                rendezvous.disponibilite.est_reserve = False
                # Détache le créneau (contrainte UNIQUE) pour permettre une
                # nouvelle réservation ; date_heure conserve l'historique.
                rendezvous.disponibilite = None

        db.session.commit()
        return rendezvous

    @staticmethod
    def deplacer(
        id_rendezvous: int,
        id_medecin: int,
        id_disponibilite: int,
    ) -> RendezVous:
        """
        Déplace un rendez-vous (EN_ATTENTE ou ACCEPTE) vers un autre créneau libre du même médecin :
        libère l'ancien créneau et réserve le nouveau.
        """
        rendezvous = db.session.get(RendezVous, id_rendezvous)
        if rendezvous is None:
            raise NotFoundError(f"Rendez-vous avec l'id {id_rendezvous} introuvable.")
        if rendezvous.id_medecin != id_medecin:
            raise ForbiddenError(
                "Vous n'êtes pas autorisé à modifier le rendez-vous d'un autre médecin."
            )
        if rendezvous.statut not in (StatutRendezVous.EN_ATTENTE, StatutRendezVous.ACCEPTE):
            raise UnprocessableEntityError(
                f"Un rendez-vous au statut {rendezvous.statut.value} ne peut plus être déplacé."
            )

        try:
            nouvelle = (
                db.session.query(Disponibilite)
                .filter(Disponibilite.id == id_disponibilite)
                .with_for_update()
                .first()
            )
            if nouvelle is None or nouvelle.id_medecin != id_medecin:
                raise NotFoundError("Créneau introuvable pour ce médecin.")
            if nouvelle.id == rendezvous.id_disponibilite:
                return rendezvous
            if nouvelle.est_reserve:
                raise ConflictError("Ce créneau est déjà réservé.")

            ancienne = rendezvous.disponibilite
            if ancienne is not None:
                ancienne.est_reserve = False
                rendezvous.disponibilite = None
                db.session.flush()

            nouvelle.est_reserve = True
            rendezvous.disponibilite = nouvelle
            rendezvous.date_heure = nouvelle.date_heure_debut
            db.session.commit()
            return rendezvous
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError("Conflit d'accès concurrent sur ce créneau.") from exc
        except Exception:
            db.session.rollback()
            raise
