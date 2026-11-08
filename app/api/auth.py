"""Namespace Flask-RESTX pour l'authentification (/api/auth)."""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.services.auth_service import AuthService

auth_ns = Namespace(
    "auth",
    description="Inscription et authentification JWT (Patient / Médecin)",
    path="/api/auth",
)

register_input_model = auth_ns.model(
    "RegisterInput",
    {
        "nom": fields.String(required=True, description="Nom de famille", example="Diop"),
        "prenom": fields.String(required=True, description="Prénom", example="Aminata"),
        "email": fields.String(
            required=True,
            description="Adresse email unique",
            example="aminata.diop@esante.sn",
        ),
        "mot_de_passe": fields.String(
            required=True,
            description="Mot de passe en clair (sera haché)",
            example="Passer@2026",
        ),
        "telephone": fields.String(
            required=False,
            description="Numéro de téléphone",
            example="+221771234567",
        ),
        "role": fields.String(
            required=True,
            description="Rôle de l'utilisateur (PATIENT ou MEDECIN)",
            enum=["PATIENT", "MEDECIN"],
            example="PATIENT",
        ),
        "date_naissance": fields.String(
            required=False,
            description="Date de naissance (YYYY-MM-DD) - spécifique PATIENT",
            example="1995-04-15",
        ),
        "adresse": fields.String(
            required=False,
            description="Adresse de résidence - spécifique PATIENT",
            example="Mermoz, Dakar",
        ),
        "numero_ordre": fields.String(
            required=False,
            description="Numéro d'inscription à l'Ordre des Médecins - spécifique MEDECIN",
            example="ONMS-SN-2026-001",
        ),
        "biographie": fields.String(
            required=False,
            description="Présentation professionnelle - spécifique MEDECIN",
            example="Spécialiste en cardiologie interventionnelle à Dakar.",
        ),
        "tarif": fields.Float(
            required=False,
            description="Tarif de téléconsultation en FCFA - spécifique MEDECIN",
            example=15000.0,
        ),
        "id_specialite": fields.Integer(
            required=False,
            description="Identifiant de la spécialité médicale - spécifique MEDECIN",
            example=1,
        ),
    },
)

utilisateur_output_model = auth_ns.model(
    "UtilisateurOutput",
    {
        "id": fields.Integer(description="Identifiant unique"),
        "nom": fields.String(description="Nom"),
        "prenom": fields.String(description="Prénom"),
        "email": fields.String(description="Email"),
        "telephone": fields.String(description="Téléphone"),
        "role": fields.String(description="Rôle (PATIENT ou MEDECIN)"),
    },
)

login_input_model = auth_ns.model(
    "LoginInput",
    {
        "email": fields.String(
            required=True,
            description="Adresse email",
            example="aminata.diop@esante.sn",
        ),
        "mot_de_passe": fields.String(
            required=True,
            description="Mot de passe",
            example="Passer@2026",
        ),
    },
)

login_output_model = auth_ns.model(
    "LoginOutput",
    {
        "access_token": fields.String(description="Token JWT signé"),
        "token_type": fields.String(description="Type de token (Bearer)"),
        "utilisateur": fields.Nested(utilisateur_output_model),
    },
)


@auth_ns.route("/register")
class RegisterResource(Resource):
    """Inscription d'un nouvel utilisateur (Patient ou Médecin)."""

    @auth_ns.doc(security=[])
    @auth_ns.expect(register_input_model, validate=True)
    @auth_ns.response(201, "Compte utilisateur créé avec succès.")
    @auth_ns.response(400, "Données d'inscription invalides.")
    @auth_ns.response(409, "Email ou numéro d'ordre déjà utilisé.")
    def post(self):
        """Inscrit un Patient ou un Médecin avec hachage sécurisé du mot de passe."""
        payload = request.get_json(silent=True) or {}
        utilisateur = AuthService.inscrire(payload)
        return {
            "message": "Inscription réussie.",
            "utilisateur": {
                "id": utilisateur.id,
                "nom": utilisateur.nom,
                "prenom": utilisateur.prenom,
                "email": utilisateur.email,
                "telephone": utilisateur.telephone,
                "role": utilisateur.role.value,
            },
        }, 201


@auth_ns.route("/login")
class LoginResource(Resource):
    """Authentification d'un utilisateur existant."""

    @auth_ns.doc(security=[])
    @auth_ns.expect(login_input_model, validate=True)
    @auth_ns.marshal_with(login_output_model, code=200)
    @auth_ns.response(401, "Identifiants invalides.")
    def post(self):
        """Authentifie l'utilisateur et retourne un token JWT contenant son rôle."""
        payload = request.get_json(silent=True) or {}
        resultat = AuthService.authentifier(
            email=payload.get("email", ""),
            mot_de_passe=payload.get("mot_de_passe", ""),
        )
        return resultat, 200
