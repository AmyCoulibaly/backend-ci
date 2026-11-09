"""Namespace Flask-RESTX pour les ordonnances (/api/rendezvous/<id>/ordonnance)."""

from flask import request
from flask_jwt_extended import get_jwt_identity
from flask_restx import Namespace, Resource, fields

from app.api.decorators import role_required
from app.models import RoleUtilisateur
from app.services.ordonnance_service import OrdonnanceService

ordonnances_ns = Namespace(
    "ordonnances",
    description="Émission d'ordonnances médicales post-consultation",
    path="/api/rendezvous",
)

ligne_ordonnance_input = ordonnances_ns.model(
    "LigneOrdonnanceInput",
    {
        "medicament": fields.String(
            required=True,
            description="Nom et dosage du médicament",
            example="Paracétamol 1000mg",
        ),
        "posologie": fields.String(
            required=True,
            description="Posologie quotidienne",
            example="1 comprimé matin, midi et soir",
        ),
        "duree": fields.String(
            required=True,
            description="Durée du traitement",
            example="5 jours",
        ),
        "quantite": fields.Integer(
            required=True,
            description="Quantité de boîtes / unités",
            example=2,
        ),
    },
)

ordonnance_create_input = ordonnances_ns.model(
    "OrdonnanceCreateInput",
    {
        "instructions": fields.String(
            required=False,
            description="Recommandations générales du médecin",
            example="Repos strict et hydratation abondante.",
        ),
        "lignes": fields.List(
            fields.Nested(ligne_ordonnance_input),
            required=True,
            description="Liste des médicaments prescrits",
        ),
    },
)

ligne_ordonnance_dto = ordonnances_ns.model(
    "LigneOrdonnanceDTO",
    {
        "id": fields.Integer(description="ID de la ligne"),
        "medicament": fields.String(description="Médicament"),
        "posologie": fields.String(description="Posologie"),
        "duree": fields.String(description="Durée"),
        "quantite": fields.Integer(description="Quantité"),
    },
)

specialite_resume_dto = ordonnances_ns.model(
    "OrdonnanceSpecialiteDTO",
    {
        "id": fields.Integer(description="ID de la spécialité"),
        "libelle": fields.String(description="Libellé de la spécialité"),
    },
)

medecin_resume_dto = ordonnances_ns.model(
    "OrdonnanceMedecinDTO",
    {
        "id": fields.Integer(description="ID du médecin"),
        "nom": fields.String(description="Nom"),
        "prenom": fields.String(description="Prénom"),
        "specialite": fields.Nested(specialite_resume_dto),
    },
)

patient_resume_dto = ordonnances_ns.model(
    "OrdonnancePatientDTO",
    {
        "id": fields.Integer(description="ID du patient"),
        "nom": fields.String(description="Nom"),
        "prenom": fields.String(description="Prénom"),
    },
)

ordonnance_dto = ordonnances_ns.model(
    "OrdonnanceDTO",
    {
        "id": fields.Integer(description="ID de l'ordonnance"),
        "date_emission": fields.Date(description="Date d'émission"),
        "instructions": fields.String(description="Instructions médicales"),
        "id_rendezvous": fields.Integer(description="ID du rendez-vous associé"),
        "lignes": fields.List(fields.Nested(ligne_ordonnance_dto)),
        "medecin": fields.Nested(medecin_resume_dto, attribute="rendezvous.medecin"),
        "patient": fields.Nested(patient_resume_dto, attribute="rendezvous.patient"),
    },
)

@ordonnances_ns.route("/<int:id>/ordonnance")
@ordonnances_ns.param("id", "Identifiant unique du rendez-vous")
class OrdonnanceResource(Resource):
    """Création d'une ordonnance rattachée à un rendez-vous terminé."""

    @role_required(RoleUtilisateur.MEDECIN)
    @ordonnances_ns.expect(ordonnance_create_input, validate=True)
    @ordonnances_ns.marshal_with(ordonnance_dto, code=201)
    @ordonnances_ns.response(403, "Accès réservé au médecin du rendez-vous.")
    @ordonnances_ns.response(404, "Rendez-vous introuvable.")
    @ordonnances_ns.response(
        422,
        "Règle métier non respectée : le rendez-vous n'est pas au statut TERMINE.",
    )
    def post(self, id: int):
        """
        (Rôle MEDECIN) Crée une ordonnance et ses lignes pour un RDV.
        Retourne 422 Unprocessable Entity si le statut du RDV n'est pas TERMINE.
        """
        payload = request.get_json(silent=True) or {}
        id_medecin = int(get_jwt_identity())
        ordonnance = OrdonnanceService.creer_ordonnance(
            id_rendezvous=id,
            id_medecin=id_medecin,
            instructions=payload.get("instructions"),
            lignes_data=payload.get("lignes", []),
        )
        return ordonnance, 201

