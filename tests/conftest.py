"""Fixtures pytest pour les tests d'intégration de l'API e-Santé Sénégal."""

from datetime import date, datetime, timedelta
import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Disponibilite,
    Medecin,
    Patient,
    RoleUtilisateur,
    Specialite,
)


@pytest.fixture()
def app():
    """Crée une instance Flask configurée en mode testing avec base SQLite en mémoire."""
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Client HTTP de test Flask."""
    return app.test_client()


@pytest.fixture()
def seed_data(app):
    """Crée des entités de base : spécialité, médecin, 2 patients et un créneau libre."""
    spec = Specialite(
        libelle="Cardiologie",
        description="Maladies cardiovasculaires",
    )
    db.session.add(spec)
    db.session.flush()

    medecin = Medecin(
        nom="Ndiaye",
        prenom="Cheikh",
        email="dr.ndiaye@esante.sn",
        telephone="+221771001122",
        role=RoleUtilisateur.MEDECIN,
        numero_ordre="ONMS-DKR-001",
        biographie="Cardiologue à Dakar",
        tarif=15000.0,
        id_specialite=spec.id,
    )
    medecin.set_password("Medecin@123")

    patient_1 = Patient(
        nom="Diop",
        prenom="Aminata",
        email="aminata@esante.sn",
        telephone="+221781112233",
        role=RoleUtilisateur.PATIENT,
        date_naissance=date(1993, 5, 10),
        adresse="Dakar",
    )
    patient_1.set_password("Patient@123")

    patient_2 = Patient(
        nom="Fall",
        prenom="Moussa",
        email="moussa@esante.sn",
        telephone="+221762223344",
        role=RoleUtilisateur.PATIENT,
        date_naissance=date(1989, 8, 21),
        adresse="Thiès",
    )
    patient_2.set_password("Patient@123")

    db.session.add_all([medecin, patient_1, patient_2])
    db.session.flush()

    maintenant = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=10)
    dispo = Disponibilite(
        date_heure_debut=maintenant,
        date_heure_fin=maintenant + timedelta(minutes=30),
        est_reserve=False,
        id_medecin=medecin.id,
    )
    db.session.add(dispo)
    db.session.commit()

    return {
        "specialite_id": spec.id,
        "medecin_id": medecin.id,
        "patient_1_id": patient_1.id,
        "patient_2_id": patient_2.id,
        "disponibilite_id": dispo.id,
    }
