"""Commandes CLI Flask personnalisées (ex: flask seed-db)."""

from datetime import date, datetime, timedelta
import click
from flask import Flask

from app.extensions import db
from app.models import (
    Disponibilite,
    Medecin,
    Patient,
    RoleUtilisateur,
    Specialite,
)


JOURS_DE_CRENEAUX = 7


def register_cli_commands(app: Flask) -> None:
    """Enregistre les commandes CLI sur l'instance Flask."""

    @app.cli.command("create-tables")
    def create_tables() -> None:
        """Crée toutes les tables du schéma (alternative à flask db upgrade sans migrations/)."""
        db.create_all()
        click.echo("Tables créées avec succès.")

    @app.cli.command("seed-db")
    def seed_db() -> None:
        """Pré-remplit la base de données e-Santé Sénégal avec des données de test."""
        click.echo("Initialisation du seeding pour e-Santé Sénégal...")

        specialites_data = [
            {
                "libelle": "Cardiologie",
                "description": "Prévention, diagnostic et traitement des maladies cardiovasculaires.",
            },
            {
                "libelle": "Pédiatrie",
                "description": "Suivi médical, vaccination et soins des nourrissons et enfants.",
            },
            {
                "libelle": "Médecine Générale",
                "description": "Consultations générales, orientation et suivi global du patient.",
            },
            {
                "libelle": "Gynécologie-Obstétrique",
                "description": "Suivi de grossesse et santé reproductive de la femme.",
            },
            {
                "libelle": "Infectiologie & Maladies Tropicales",
                "description": "Prise en charge du paludisme et des pathologies infectieuses tropicales.",
            },
        ]

        specialites_map: dict[str, Specialite] = {}
        for spec_info in specialites_data:
            spec = Specialite.query.filter_by(libelle=spec_info["libelle"]).first()
            if spec is None:
                spec = Specialite(**spec_info)
                db.session.add(spec)
                db.session.flush()
            specialites_map[spec.libelle] = spec

        medecins_data = [
            {
                "nom": "Ndiaye",
                "prenom": "Cheikh",
                "email": "dr.ndiaye@esante.sn",
                "mot_de_passe": "Medecin@2026",
                "telephone": "+221771001122",
                "numero_ordre": "ONMS-DKR-001",
                "biographie": (
                    "Cardiologue praticien à l'Hôpital Principal de Dakar, "
                    "12 ans d'expérience en télécardiologie."
                ),
                "tarif": 15000.00,
                "specialite_libelle": "Cardiologie",
            },
            {
                "nom": "Sow",
                "prenom": "Fatou",
                "email": "dr.sow@esante.sn",
                "mot_de_passe": "Medecin@2026",
                "telephone": "+221772003344",
                "numero_ordre": "ONMS-SL-002",
                "biographie": (
                    "Pédiatre diplômée de l'UCAD, spécialisée en néonatologie "
                    "et nutrition infantile à Saint-Louis."
                ),
                "tarif": 10000.00,
                "specialite_libelle": "Pédiatrie",
            },
        ]

        medecins_crees: list[Medecin] = []
        for med_info in medecins_data:
            med = Medecin.query.filter_by(email=med_info["email"]).first()
            if med is None:
                med = Medecin(
                    nom=med_info["nom"],
                    prenom=med_info["prenom"],
                    email=med_info["email"],
                    telephone=med_info["telephone"],
                    role=RoleUtilisateur.MEDECIN,
                    numero_ordre=med_info["numero_ordre"],
                    biographie=med_info["biographie"],
                    tarif=med_info["tarif"],
                    id_specialite=specialites_map[med_info["specialite_libelle"]].id,
                )
                med.set_password(med_info["mot_de_passe"])
                db.session.add(med)
                db.session.flush()
            medecins_crees.append(med)

        patients_data = [
            {
                "nom": "Diop",
                "prenom": "Aminata",
                "email": "aminata.diop@esante.sn",
                "mot_de_passe": "Patient@2026",
                "telephone": "+221783005566",
                "date_naissance": date(1992, 6, 14),
                "adresse": "Quartier Mermoz, Dakar",
            },
            {
                "nom": "Fall",
                "prenom": "Moussa",
                "email": "moussa.fall@esante.sn",
                "mot_de_passe": "Patient@2026",
                "telephone": "+221764007788",
                "date_naissance": date(1985, 11, 23),
                "adresse": "Escale, Thiès",
            },
        ]

        for pat_info in patients_data:
            pat = Patient.query.filter_by(email=pat_info["email"]).first()
            if pat is None:
                pat = Patient(
                    nom=pat_info["nom"],
                    prenom=pat_info["prenom"],
                    email=pat_info["email"],
                    telephone=pat_info["telephone"],
                    role=RoleUtilisateur.PATIENT,
                    date_naissance=pat_info["date_naissance"],
                    adresse=pat_info["adresse"],
                )
                pat.set_password(pat_info["mot_de_passe"])
                db.session.add(pat)

        # Créneaux de 30 min sur les 7 prochains jours (dimanche exclu),
        # matin et après-midi. Idempotent : un créneau existant n'est pas recréé
        # et les créneaux déjà passés aujourd'hui sont ignorés.
        maintenant = datetime.now()
        horaires = [(9, 0), (9, 30), (10, 0), (10, 30), (11, 0), (15, 0), (15, 30), (16, 0)]
        nb_creneaux = 0
        for med in medecins_crees:
            for decalage in range(JOURS_DE_CRENEAUX):
                jour = date.today() + timedelta(days=decalage)
                if jour.weekday() == 6:
                    continue
                for heure, minute in horaires:
                    debut = datetime(jour.year, jour.month, jour.day, heure, minute)
                    if debut <= maintenant:
                        continue
                    existe = Disponibilite.query.filter_by(
                        id_medecin=med.id, date_heure_debut=debut
                    ).first()
                    if existe is None:
                        db.session.add(
                            Disponibilite(
                                date_heure_debut=debut,
                                date_heure_fin=debut + timedelta(minutes=30),
                                est_reserve=False,
                                id_medecin=med.id,
                            )
                        )
                        nb_creneaux += 1

        db.session.commit()
        click.echo(
            "Base de données pré-remplie avec succès : "
            f"{len(specialites_map)} spécialités, 2 médecins, 2 patients "
            f"et {nb_creneaux} nouveaux créneaux (7 prochains jours)."
        )
