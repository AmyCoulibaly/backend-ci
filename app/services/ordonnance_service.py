"""Service métier pour la gestion des ordonnances médicales (OrdonnanceService)."""

from typing import Any

from app.extensions import db
from app.models import LigneOrdonnance, Ordonnance, RendezVous, RoleUtilisateur, StatutRendezVous
from app.services.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableEntityError,
)


class OrdonnanceService:
    """Logique métier pour la création et la consultation des ordonnances."""

    @staticmethod
    def creer_ordonnance(
        id_rendezvous: int,
        id_medecin: int,
        instructions: str | None,
        lignes_data: list[dict[str, Any]],
    ) -> Ordonnance:
        """
        Crée une ordonnance avec ses LigneOrdonnance pour un rendez-vous donné.
        Règle métier critique :
        - Le statut du RendezVous doit impérativement être TERMINE, sinon lève
          UnprocessableEntityError (422 Unprocessable Entity).
        - Une ordonnance doit contenir au moins une ligne de médicament.
        """
        rendezvous = db.session.get(RendezVous, id_rendezvous)
        if rendezvous is None:
            raise NotFoundError(
                f"Rendez-vous avec l'id {id_rendezvous} introuvable."
            )

        if rendezvous.id_medecin != id_medecin:
            raise ForbiddenError(
                "Seul le médecin en charge de ce rendez-vous peut émettre une ordonnance."
            )

        if rendezvous.statut != StatutRendezVous.TERMINE:
            raise UnprocessableEntityError(
                f"Impossible de créer une ordonnance : le statut du rendez-vous est "
                f"'{rendezvous.statut.value}' (statut requis : 'TERMINE')."
            )

        if rendezvous.ordonnance is not None:
            raise ConflictError(
                "Une ordonnance a déjà été émise pour ce rendez-vous."
            )

        if not lignes_data or not isinstance(lignes_data, list):
            raise BadRequestError(
                "Une ordonnance doit contenir au moins une ligne de médicament."
            )

        lignes_validees = []
        for index, ligne in enumerate(lignes_data, start=1):
            medicament = (ligne.get("medicament") or "").strip()
            posologie = (ligne.get("posologie") or "").strip()
            duree = (ligne.get("duree") or "").strip()
            try:
                quantite = int(ligne.get("quantite", 1))
            except (TypeError, ValueError) as exc:
                raise BadRequestError(
                    f"Ligne {index} invalide : la quantité doit être un entier."
                ) from exc

            if not medicament or not posologie or not duree:
                raise BadRequestError(
                    f"Ligne {index} invalide : medicament, posologie et duree sont requis."
                )
            if quantite <= 0:
                raise BadRequestError(
                    f"Ligne {index} invalide : la quantité doit être strictement positive."
                )
            lignes_validees.append(
                {"medicament": medicament, "posologie": posologie, "duree": duree, "quantite": quantite}
            )

        ordonnance = Ordonnance(
            instructions=instructions,
            id_rendezvous=rendezvous.id,
        )
        db.session.add(ordonnance)

        for lv in lignes_validees:
            db.session.add(LigneOrdonnance(ordonnance=ordonnance, **lv))

        db.session.commit()
        return ordonnance

    @staticmethod
    def lister_ordonnances(id_utilisateur: int, role: str) -> list[Ordonnance]:
        """Liste les ordonnances du patient (reçues) ou du médecin (émises) connecté."""
        colonne = (
            RendezVous.id_patient
            if role == RoleUtilisateur.PATIENT.value
            else RendezVous.id_medecin
        )
        return (
            Ordonnance.query.join(RendezVous, Ordonnance.id_rendezvous == RendezVous.id)
            .filter(colonne == id_utilisateur)
            .order_by(Ordonnance.date_emission.desc(), Ordonnance.id.desc())
            .all()
        )
