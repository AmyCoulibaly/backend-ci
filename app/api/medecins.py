"""Namespace Flask-RESTX pour les médecins et leurs disponibilités (/api/medecins)."""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.services.medecin_service import MedecinService

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


@medecins_ns.route("/<int:id>/disponibilites")
@medecins_ns.param("id", "Identifiant unique du médecin")
class MedecinDisponibilitesResource(Resource):
    """Créneaux disponibles d'un médecin."""

    @medecins_ns.doc(security=[])
    @medecins_ns.marshal_list_with(disponibilite_dto, code=200)
    @medecins_ns.response(404, "Médecin introuvable.")
    def get(self, id: int):
        """Retourne les créneaux horaires libres (est_reserve=False) du médecin."""
        return MedecinService.get_disponibilites_libres(id_medecin=id), 200
