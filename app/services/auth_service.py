"""Service d'authentification et d'inscription (AuthService)."""

from datetime import datetime
from typing import Any

from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Medecin, Patient, RoleUtilisateur, Specialite, Utilisateur
from app.services.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)


class AuthService:
    """Logique métier pour l'inscription et la connexion des utilisateurs."""

    @staticmethod
    def inscrire(data: dict[str, Any]) -> Utilisateur:
        """Inscrit un nouveau Patient ou Medecin avec hachage du mot de passe."""
        email = (data.get("email") or "").strip().lower()
        mot_de_passe = data.get("mot_de_passe")
        nom = (data.get("nom") or "").strip()
        prenom = (data.get("prenom") or "").strip()
        role_str = (data.get("role") or "PATIENT").strip().upper()

        if not email or not mot_de_passe or not nom or not prenom:
            raise BadRequestError(
                "Les champs nom, prenom, email et mot_de_passe sont obligatoires."
            )

        try:
            role = RoleUtilisateur(role_str)
        except ValueError as exc:
            raise BadRequestError(
                f"Rôle invalide '{role_str}'. Valeurs acceptées : PATIENT, MEDECIN."
            ) from exc

        if Utilisateur.query.filter_by(email=email).first() is not None:
            raise ConflictError(f"Un utilisateur avec l'email '{email}' existe déjà.")

        if role == RoleUtilisateur.PATIENT:
            date_naissance = None
            raw_dob = data.get("date_naissance")
            if raw_dob:
                if isinstance(raw_dob, str):
                    try:
                        date_naissance = datetime.strptime(raw_dob, "%Y-%m-%d").date()
                    except ValueError as exc:
                        raise BadRequestError(
                            "Format de date_naissance invalide (attendu: YYYY-MM-DD)."
                        ) from exc
                else:
                    date_naissance = raw_dob

            utilisateur: Utilisateur = Patient(
                nom=nom,
                prenom=prenom,
                email=email,
                telephone=data.get("telephone"),
                role=RoleUtilisateur.PATIENT,
                date_naissance=date_naissance,
                adresse=data.get("adresse"),
            )
        else:
            numero_ordre = (data.get("numero_ordre") or "").strip()
            id_specialite = data.get("id_specialite")
            if not numero_ordre or not id_specialite:
                raise BadRequestError(
                    "Les champs numero_ordre et id_specialite sont obligatoires pour un MEDECIN."
                )

            if Medecin.query.filter_by(numero_ordre=numero_ordre).first() is not None:
                raise ConflictError(
                    f"Un médecin avec le numéro d'ordre '{numero_ordre}' existe déjà."
                )

            specialite = db.session.get(Specialite, id_specialite)
            if specialite is None:
                raise NotFoundError(
                    f"Spécialité avec l'id {id_specialite} introuvable."
                )

            tarif = data.get("tarif", 0.0)
            if float(tarif) < 0:
                raise BadRequestError("Le tarif de consultation doit être positif.")

            utilisateur = Medecin(
                nom=nom,
                prenom=prenom,
                email=email,
                telephone=data.get("telephone"),
                role=RoleUtilisateur.MEDECIN,
                numero_ordre=numero_ordre,
                biographie=data.get("biographie"),
                tarif=tarif,
                id_specialite=id_specialite,
            )

        utilisateur.set_password(mot_de_passe)

        try:
            db.session.add(utilisateur)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError(
                "Conflit d'intégrité lors de la création du compte utilisateur."
            ) from exc

        return utilisateur

    @staticmethod
    def authentifier(email: str, mot_de_passe: str) -> dict[str, Any]:
        """Authentifie un utilisateur et génère un token JWT incluant son rôle."""
        if not email or not mot_de_passe:
            raise BadRequestError("Email et mot de passe sont requis.")

        utilisateur = Utilisateur.query.filter_by(email=email.strip().lower()).first()
        if utilisateur is None or not utilisateur.check_password(mot_de_passe):
            raise UnauthorizedError("Identifiants (email ou mot de passe) incorrects.")

        access_token = create_access_token(
            identity=str(utilisateur.id),
            additional_claims={
                "role": utilisateur.role.value,
                "email": utilisateur.email,
                "nom": utilisateur.nom,
                "prenom": utilisateur.prenom,
            },
        )
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "utilisateur": {
                "id": utilisateur.id,
                "nom": utilisateur.nom,
                "prenom": utilisateur.prenom,
                "email": utilisateur.email,
                "role": utilisateur.role.value,
            },
        }
