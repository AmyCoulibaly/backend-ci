"""Namespace Flask-RESTX pour la gestion des rendez-vous (/api/rendezvous)."""

from flask import request
from flask_jwt_extended import get_jwt_identity
from flask_restx import Namespace, Resource, fields

from app.api.decorators import role_required
from app.models import RoleUtilisateur
from app.services.exceptions import BadRequestError
from app.services.rendezvous_service import RendezVousService

rendezvous_ns = Namespace(
    "rendezvous",
    description="Réservation et gestion des rendez-vous de téléconsultation",
    path="/api/rendezvous",
)

rendezvous_create_input = rendezvous_ns.model(
    "RendezVousCreateInput",
    {
        "id_disponibilite": fields.Integer(
            required=True,
            description="Identifiant du créneau de disponibilité choisi",
            example=1,
        ),
        "motif": fields.String(
            required=False,
            description="Motif de la téléconsultation",
            example="Douleurs thoraciques et contrôle tensionnel",
        ),
    },
)

rendezvous_update_input = rendezvous_ns.model(
    "RendezVousUpdateInput",
    {
        "statut": fields.String(
            required=True,
            description="Nouveau statut du rendez-vous",
            enum=["ACCEPTE", "REFUSE", "ANNULE", "TERMINE"],
            example="ACCEPTE",
        ),
    },
)

rendezvous_dto = rendezvous_ns.model(
    "RendezVousDTO",
    {
        "id": fields.Integer(description="ID du rendez-vous"),
        "date_heure": fields.DateTime(description="Date et heure du rendez-vous"),
        "motif": fields.String(description="Motif de la consultation"),
        "statut": fields.String(
            description="Statut du RDV",
            attribute=lambda rdv: rdv.statut.value if rdv.statut else None,
        ),
        "date_creation": fields.DateTime(description="Date de prise du RDV"),
        "id_patient": fields.Integer(description="ID du patient"),
        "id_medecin": fields.Integer(description="ID du médecin"),
        "id_disponibilite": fields.Integer(description="ID du créneau réservé"),
    },
)


@rendezvous_ns.route("")
class RendezVousListResource(Resource):
    """Création d'un rendez-vous (PATIENT) et consultation de l'agenda (MEDECIN)."""

    @role_required(RoleUtilisateur.PATIENT)
    @rendezvous_ns.expect(rendezvous_create_input, validate=True)
    @rendezvous_ns.marshal_with(rendezvous_dto, code=201)
    @rendezvous_ns.response(403, "Accès réservé aux patients.")
    @rendezvous_ns.response(404, "Créneau de disponibilité introuvable.")
    @rendezvous_ns.response(409, "Conflit : Créneau déjà réservé.")
    def post(self):
        """(Rôle PATIENT) Réserve un créneau de disponibilité et crée un rendez-vous."""
        payload = request.get_json(silent=True) or {}
        id_disponibilite = payload.get("id_disponibilite")
        if id_disponibilite is None:
            raise BadRequestError("Le champ 'id_disponibilite' est obligatoire.")

        id_patient = int(get_jwt_identity())
        rdv = RendezVousService.reserver(
            id_patient=id_patient,
            id_disponibilite=int(id_disponibilite),
            motif=payload.get("motif"),
        )
        return rdv, 201

    @role_required(RoleUtilisateur.MEDECIN)
    @rendezvous_ns.doc(
        params={
            "date": "Filtrer par date ('today' pour les RDV du jour ou 'YYYY-MM-DD')",
        }
    )
    @rendezvous_ns.marshal_list_with(rendezvous_dto, code=200)
    @rendezvous_ns.response(403, "Accès réservé aux médecins.")
    def get(self):
        """(Rôle MEDECIN) Liste les rendez-vous du médecin connecté (?date=today)."""
        id_medecin = int(get_jwt_identity())
        filtre_date = request.args.get("date")
        rdvs = RendezVousService.lister_rendezvous_medecin(
            id_medecin=id_medecin,
            filtre_date=filtre_date,
        )
        return rdvs, 200


@rendezvous_ns.route("/<int:id>")
@rendezvous_ns.param("id", "Identifiant unique du rendez-vous")
class RendezVousDetailResource(Resource):
    """Mise à jour du statut d'un rendez-vous par le médecin."""

    @role_required(RoleUtilisateur.MEDECIN)
    @rendezvous_ns.expect(rendezvous_update_input, validate=True)
    @rendezvous_ns.marshal_with(rendezvous_dto, code=200)
    @rendezvous_ns.response(400, "Statut invalide.")
    @rendezvous_ns.response(403, "Accès interdit (rôle ou médecin non propriétaire).")
    @rendezvous_ns.response(404, "Rendez-vous introuvable.")
    def put(self, id: int):
        """
        (Rôle MEDECIN) Met à jour le statut d'un RDV (ACCEPTE, ANNULE, REFUSE, TERMINE).
        Si ANNULE, libère automatiquement la Disponibilite (est_reserve=False).
        """
        payload = request.get_json(silent=True) or {}
        statut = payload.get("statut")
        if not statut:
            raise BadRequestError("Le champ 'statut' est obligatoire.")

        id_medecin = int(get_jwt_identity())
        rdv = RendezVousService.mettre_a_jour_statut(
            id_rendezvous=id,
            id_medecin=id_medecin,
            nouveau_statut_str=statut,
        )
        return rdv, 200
