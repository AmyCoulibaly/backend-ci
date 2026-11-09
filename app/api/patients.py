"""Namespace Flask-RESTX pour l'espace patient (/api/patients)."""

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask import request
from flask_restx import Namespace, Resource

from app.api.decorators import role_required
from app.api.ordonnances import ordonnance_dto
from app.api.rendezvous import rendezvous_dto
from app.models import RoleUtilisateur
from app.services.exceptions import ForbiddenError
from app.services.ordonnance_service import OrdonnanceService
from app.services.rendezvous_service import RendezVousService

patients_ns = Namespace(
    "patients",
    description="Historique des rendez-vous et ordonnances du patient connecté",
    path="/api/patients",
)
for _modele in (rendezvous_dto, ordonnance_dto):
    patients_ns.add_model(_modele.name, _modele)


def _exiger_patient_proprietaire(id_patient: int) -> None:
    """Un patient ne consulte que ses propres données."""
    if int(get_jwt_identity()) != id_patient:
        raise ForbiddenError("Vous ne pouvez consulter que vos propres données.")


@patients_ns.route("/<int:id>/rendezvous")
@patients_ns.param("id", "Identifiant du patient (celui du jeton)")
class PatientRendezVousResource(Resource):
    """Historique des rendez-vous d'un patient."""

    @role_required(RoleUtilisateur.PATIENT)
    @patients_ns.doc(params={"date": "Filtre facultatif : 'today' ou 'YYYY-MM-DD'"})
    @patients_ns.marshal_list_with(rendezvous_dto, code=200)
    @patients_ns.response(403, "Accès réservé au patient concerné.")
    def get(self, id: int):
        """(Rôle PATIENT) Liste ses rendez-vous, tous statuts confondus."""
        _exiger_patient_proprietaire(id)
        return (
            RendezVousService.lister_rendezvous(
                id_utilisateur=id,
                role=RoleUtilisateur.PATIENT.value,
                filtre_date=request.args.get("date"),
            ),
            200,
        )


@patients_ns.route("/<int:id>/ordonnances")
@patients_ns.param("id", "Identifiant du patient (celui du jeton)")
class PatientOrdonnancesResource(Resource):
    """Ordonnances reçues par un patient."""

    @role_required(RoleUtilisateur.PATIENT)
    @patients_ns.marshal_list_with(ordonnance_dto, code=200)
    @patients_ns.response(403, "Accès réservé au patient concerné.")
    def get(self, id: int):
        """(Rôle PATIENT) Liste les ordonnances qui lui ont été émises."""
        _exiger_patient_proprietaire(id)
        return (
            OrdonnanceService.lister_ordonnances(
                id_utilisateur=id, role=RoleUtilisateur.PATIENT.value
            ),
            200,
        )
