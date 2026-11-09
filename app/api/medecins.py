"""Namespace Flask-RESTX pour les médecins et leurs disponibilités (/api/medecins)."""

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from flask_restx import Namespace, Resource, fields

from app.api.decorators import role_required
from app.api.ordonnances import ordonnance_dto
from app.models import RoleUtilisateur
from app.services.exceptions import ForbiddenError
from app.services.medecin_service import MedecinService
from app.services.ordonnance_service import OrdonnanceService

medecins_ns = Namespace(
    "medecins",
    description="Recherche de médecins et consultation des disponibilités",
    path="/api/medecins",
)

specialite_dto = medecins_ns.model(
    "SpecialiteDTO",
    {
        "id": fields.Integer(description="ID de la spécialité"),
        "libelle": fields.String(description="Libellé de la spécialité"),
        "description": fields.String(description="Description de la spécialité"),
    },
)

medecin_dto = medecins_ns.model(
    "MedecinDTO",
    {
        "id": fields.Integer(description="ID du médecin"),
        "nom": fields.String(description="Nom du médecin"),
        "prenom": fields.String(description="Prénom du médecin"),
        "email": fields.String(description="Email professionnel"),
        "telephone": fields.String(description="Téléphone"),
        "numero_ordre": fields.String(description="Numéro d'ordre ONMS"),
        "biographie": fields.String(description="Biographie"),
        "tarif": fields.Float(description="Tarif de consultation (FCFA)"),
        "specialite": fields.Nested(specialite_dto),
    },
)

disponibilite_dto = medecins_ns.model(
    "DisponibiliteDTO",
    {
        "id": fields.Integer(description="ID du créneau"),
        "date_heure_debut": fields.DateTime(description="Début du créneau (ISO 8601)"),
        "date_heure_fin": fields.DateTime(description="Fin du créneau (ISO 8601)"),
        "est_reserve": fields.Boolean(description="Indique si le créneau est réservé"),
        "id_medecin": fields.Integer(description="ID du médecin propriétaire"),
    },
)


@medecins_ns.route("")
class MedecinListResource(Resource):
    """Liste et filtrage des médecins par spécialité."""

    @medecins_ns.doc(
        security=[],
        params={"specialite": "Filtrer par libellé de spécialité (ex: Cardiologie)"},
    )
    @medecins_ns.marshal_list_with(medecin_dto, code=200)
    def get(self):
        """Retourne la liste des médecins, filtrable par ?specialite=libelle."""
        specialite = request.args.get("specialite")
        return MedecinService.lister_medecins(libelle_specialite=specialite), 200


medecins_ns.add_model(ordonnance_dto.name, ordonnance_dto)

disponibilite_input = medecins_ns.model(
    "DisponibiliteInput",
    {
        "date_heure_debut": fields.String(required=True, description="Début (ISO 8601)", example="2026-11-10T09:00:00"),
        "date_heure_fin": fields.String(required=True, description="Fin (ISO 8601)", example="2026-11-10T09:30:00"),
    },
)

# Suppression d'un créneau : DELETE /api/disponibilites/<id>
disponibilites_ns = Namespace(
    "disponibilites",
    description="Gestion des créneaux par le médecin",
    path="/api/disponibilites",
)


def _exiger_medecin_proprietaire(id_medecin: int) -> None:
    """Vérifie que le JWT est celui d'un MEDECIN et qu'il agit sur son propre planning."""
    verify_jwt_in_request()
    if get_jwt().get("role") != RoleUtilisateur.MEDECIN.value or int(get_jwt_identity()) != id_medecin:
        raise ForbiddenError("Seul le médecin concerné peut gérer ses disponibilités.")


@medecins_ns.route("/<int:id>/disponibilites")
@medecins_ns.param("id", "Identifiant unique du médecin")
class MedecinDisponibilitesResource(Resource):
    """Créneaux d'un médecin."""

    @medecins_ns.doc(
        security=[],
        params={"toutes": "true : tous les créneaux (libres et réservés), réservé au médecin concerné"},
    )
    @medecins_ns.marshal_list_with(disponibilite_dto, code=200)
    @medecins_ns.response(403, "Accès réservé au médecin concerné (?toutes=true).")
    @medecins_ns.response(404, "Médecin introuvable.")
    def get(self, id: int):
        """Créneaux libres du médecin (public) ; avec ?toutes=true, tous ses créneaux (médecin connecté)."""
        if str(request.args.get("toutes", "")).lower() in ("1", "true", "oui"):
            _exiger_medecin_proprietaire(id)
            return MedecinService.get_toutes_disponibilites(id_medecin=id), 200
        return MedecinService.get_disponibilites_libres(id_medecin=id), 200

    @medecins_ns.expect(disponibilite_input, validate=True)
    @medecins_ns.marshal_with(disponibilite_dto, code=201)
    @medecins_ns.response(400, "Dates invalides.")
    @medecins_ns.response(403, "Accès réservé au médecin concerné.")
    @medecins_ns.response(409, "Le créneau chevauche un créneau existant.")
    def post(self, id: int):
        """(Rôle MEDECIN) Ajoute un créneau à son planning."""
        _exiger_medecin_proprietaire(id)
        payload = request.get_json(silent=True) or {}
        dispo = MedecinService.creer_disponibilite(
            id_medecin=id,
            debut=payload.get("date_heure_debut"),
            fin=payload.get("date_heure_fin"),
        )
        return dispo, 201


@disponibilites_ns.route("/<int:id>")
@disponibilites_ns.param("id", "Identifiant du créneau")
class DisponibiliteResource(Resource):
    """Suppression d'un créneau."""

    @role_required(RoleUtilisateur.MEDECIN)
    @disponibilites_ns.response(204, "Créneau supprimé.")
    @disponibilites_ns.response(403, "Créneau d'un autre médecin.")
    @disponibilites_ns.response(404, "Créneau introuvable.")
    @disponibilites_ns.response(409, "Créneau déjà réservé.")
    def delete(self, id: int):
        """(Rôle MEDECIN) Supprime un de ses créneaux libres."""
        MedecinService.supprimer_disponibilite(id_disponibilite=id, id_medecin=int(get_jwt_identity()))
        return "", 204


@medecins_ns.route("/<int:id>/ordonnances")
@medecins_ns.param("id", "Identifiant du médecin (celui du jeton)")
class MedecinOrdonnancesResource(Resource):
    """Ordonnances émises par un médecin."""

    @medecins_ns.marshal_list_with(ordonnance_dto, code=200)
    @medecins_ns.response(403, "Accès réservé au médecin concerné.")
    def get(self, id: int):
        """(Rôle MEDECIN) Liste les ordonnances qu'il a émises."""
        _exiger_medecin_proprietaire(id)
        return (
            OrdonnanceService.lister_ordonnances(
                id_utilisateur=id, role=RoleUtilisateur.MEDECIN.value
            ),
            200,
        )
