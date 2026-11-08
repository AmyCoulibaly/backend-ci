# e-Santé Sénégal — Backend API (`backend-ci`)

API RESTful du microservice **Backend** de la plateforme de téléconsultation médicale **e-Santé Sénégal**.  
Ce dépôt s'inscrit dans une architecture microservices multi-repositories composée de :
- `frontend-ci` : Interface utilisateur React.js (Espace Patient & Tableau de bord Médecin).
- **`backend-ci`** *(ce dépôt)* : API REST Python/Flask, logique métier, ORM SQLAlchemy, documentation Swagger/OpenAPI et pipeline CI.
- `deployment-cd` : Orchestration Docker Compose (`docker-compose.yml`, `.env`), persistance PostgreSQL et déploiement continu (rolling update).

---

## Sommaire

1. [Stack Technique](#-1-stack-technique)
2. [Architecture du Projet](#-2-architecture-du-projet)
3. [Modèle de Données & Règles Métier](#-3-modèle-de-données--règles-métier)
4. [Installation & Démarrage Local](#-4-installation--démarrage-local)
5. [Commandes CLI & Données de Test (`seed-db`)](#-5-commandes-cli--données-de-test-seed-db)
6. [Documentation des Endpoints REST](#-6-documentation-des-endpoints-rest)
7. [Tests Automatisés & Sécurité](#-7-tests-automatisés--sécurité)
8. [Docker & Pipeline CI/CD Jenkins](#-8-docker--pipeline-cicd-jenkins)

---

## 1. Stack Technique

| Composant | Technologie | Rôle |
| :--- | :--- | :--- |
| **Langage & Framework** | Python 3.11+, Flask 3.0 | Serveur d'application web léger et modulaire (Application Factory) |
| **Documentation API** | Flask-RESTX 1.3 | Exposition automatique Swagger UI (`/docs`), validation et sérialisation DTO |
| **Base de données** | PostgreSQL (Prod/Dev), SQLite (Tests) | Stockage relationnel transactionnel |
| **ORM & Migrations** | Flask-SQLAlchemy 3.1, Flask-Migrate (Alembic) | Modélisation objet-relationnelle et versionnement du schéma SQL |
| **Authentification** | Flask-JWT-Extended 4.6, Werkzeug Security | Authentification stateless par tokens JWT et contrôle d'accès par rôles (`PATIENT`, `MEDECIN`) |
| **Serveur WSGI** | Gunicorn 22.0 | Serveur HTTP de production multi-workers |
| **Qualité & Sécurité** | Pytest, Pytest-Flask, Bandit, Trivy | Tests unitaires/intégration, analyse statique SAST (Bandit) et scan d'image Docker (Trivy) |
| **CI/CD & Conteneurs** | Docker (Multi-stage), Jenkins | Conteneurisation optimisée et pipeline déclaratif d'intégration continue |

---

## 2. Architecture du Projet

Le projet suit le patron de conception **Application Factory** avec séparation stricte entre les couches **Présentation REST (`api/`)**, **Logique Métier (`services/`)** et **Accès aux Données (`models/`)** :

```text
backend-ci/
├── app/
│   ├── __init__.py               # Application Factory (create_app), /health et gestionnaires d'erreurs
│   ├── config.py                 # Configurations par environnement (Development, Testing, Production)
│   ├── extensions.py             # Instances partagées : db, migrate, jwt, cors, api (Swagger)
│   ├── cli.py                    # Commandes Flask CLI personnalisées (flask seed-db)
│   ├── models/                   # Couche Données (Modèles SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── utilisateur.py        # Utilisateur, Patient, Medecin, RoleUtilisateur (héritage joint)
│   │   ├── specialite.py         # Specialite médicale
│   │   ├── disponibilite.py      # Disponibilite (créneaux horaires)
│   │   ├── rendezvous.py         # RendezVous, StatutRendezVous
│   │   └── ordonnance.py         # Ordonnance, LigneOrdonnance (suppression en cascade)
│   ├── services/                 # Couche Métier pure (découplée de HTTP)
│   │   ├── __init__.py
│   │   ├── exceptions.py         # Exceptions métier typées (400, 401, 403, 404, 409, 422)
│   │   ├── auth_service.py       # Inscription, hachage mot de passe et génération JWT
│   │   ├── medecin_service.py    # Recherche filtrée de médecins et créneaux libres
│   │   ├── rendezvous_service.py # Réservation transactionnelle anti-conflit et cycle de vie RDV
│   │   └── ordonnance_service.py # Émission d'ordonnances post-consultation
│   └── api/                      # Couche Présentation REST (Namespaces Flask-RESTX & DTOs)
│       ├── __init__.py
│       ├── decorators.py         # Décorateur @role_required (RBAC JWT)
│       ├── auth.py               # Namespace /api/auth
│       ├── medecins.py           # Namespace /api/medecins
│       ├── rendezvous.py         # Namespace /api/rendezvous
│       └── ordonnances.py        # Namespace /api/rendezvous/<id>/ordonnance
├── tests/                        # Suite de tests automatisés (pytest)
│   ├── conftest.py               # Fixtures d'application, client HTTP et jeu de données isolé
│   └── test_api.py               # Tests de santé, RBAC, concurrence 409, ordonnance 422 et CLI
├── Dockerfile                    # Image Docker multi-stage sécurisée (utilisateur non-root)
├── Jenkinsfile                   # Pipeline CI déclaratif Jenkins
├── requirements.txt              # Dépendances Python verrouillées
└── run.py                        # Point d'entrée WSGI / développement
```

---

## 3. Modèle de Données & Règles Métier

### Entités et Relations
- **`Utilisateur` (`utilisateur`)** : Table parente en **héritage joint** (*Joined Table Inheritance*) contenant `id`, `nom`, `prenom`, `email` (unique), `mot_de_passe` (hashé PBKDF2/Scrypt via Werkzeug), `telephone`, `role` (`PATIENT` | `MEDECIN`), `date_creation`.
- **`Patient` (`patient`)** : Hérite d'`Utilisateur` (`id` clé primaire et étrangère `ON DELETE CASCADE`), `date_naissance`, `adresse`.
- **`Medecin` (`medecin`)** : Hérite d'`Utilisateur` (`id` clé primaire et étrangère `ON DELETE CASCADE`), `numero_ordre` (unique), `biographie`, `tarif` ($\ge 0$), `id_specialite` (FK vers `specialite`).
- **`Specialite` (`specialite`)** : `id`, `libelle` (unique), `description`.
- **`Disponibilite` (`disponibilite`)** : Créneau horaire d'un médecin (`date_heure_debut`, `date_heure_fin` avec contrainte `date_heure_fin > date_heure_debut`, `est_reserve` booléen à `False` par défaut, `id_medecin`).
- **`RendezVous` (`rendezvous`)** : Associe un `Patient`, un `Medecin` et une `Disponibilite` (relation `1-1` via contrainte `UNIQUE`). Suit le cycle de statuts : `EN_ATTENTE` $\rightarrow$ `ACCEPTE` / `REFUSE` / `ANNULE` $\rightarrow$ `TERMINE`.
- **`Ordonnance` (`ordonnance`)** & **`LigneOrdonnance` (`ligne_ordonnance`)** : Relation `1-1` entre `RendezVous` et `Ordonnance`, et composition `1-N` vers `LigneOrdonnance` avec suppression en cascade (`cascade="all, delete-orphan"`).

### Règles Métier Critiques Implémentées
1. **Prévention des doubles réservations (`409 Conflict`)** : Lors de `POST /api/rendezvous`, `RendezVousService.reserver` verrouille la ligne `Disponibilite` dans la transaction courante (`SELECT ... FOR UPDATE`) et vérifie `est_reserve == False`. Si le créneau est déjà réservé ou réservé simultanément par une transaction concurrente, l'API annule la transaction et retourne **`409 Conflict`**.
2. **Libération automatique de créneau** : Lorsqu'un médecin annule (`ANNULE`) ou refuse (`REFUSE`) un rendez-vous via `PUT /api/rendezvous/<id>`, la disponibilité associée repasse automatiquement à `est_reserve = False`.
3. **Validation préalable à l'ordonnance (`422 Unprocessable Entity`)** : Une ordonnance ne peut être créée (`POST /api/rendezvous/<id>/ordonnance`) que par le médecin propriétaire du rendez-vous **et** uniquement si le statut du rendez-vous est **`TERMINE`**. Dans le cas contraire, l'API retourne **`422 Unprocessable Entity`**.

---

## 4. Installation & Démarrage Local

### Prérequis
- **Python 3.11+**
- **PostgreSQL 15+** (pour les environnements `development` et `production`)

### 1. Cloner le dépôt et créer l'environnement virtuel
```bash
cd backend-ci
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement
Créez un fichier `.env` à la racine de `backend-ci` (ou exportez les variables dans votre terminal) :
```env
FLASK_ENV=development
PORT=5000
SECRET_KEY=votre_cle_secrete_flask
JWT_SECRET_KEY=votre_cle_secrete_jwt
JWT_EXPIRES_HOURS=24
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/esante_senegal_dev
```

### 3. Initialiser la base de données (Flask-Migrate / Alembic)
```bash
export FLASK_APP=run.py
flask db init
flask db migrate -m "Initial schema e-Sante Senegal"
flask db upgrade
```

### 4. Lancer le serveur de développement
```bash
python run.py
```
- L'API est accessible sur : `http://127.0.0.1:5000`
- L'interface **Swagger UI (OpenAPI)** est accessible sur : `http://127.0.0.1:5000/docs`
- Le **Healthcheck** est accessible sur : `http://127.0.0.1:5000/health`

---

## 5. Commandes CLI & Données de Test (`seed-db`)

Pour pré-remplir la base de données avec des spécialités médicales pertinentes au Sénégal, 2 médecins de test, 2 patients de test et leurs créneaux de disponibilité :

```bash
export FLASK_APP=run.py
flask seed-db
```

### Comptes créés par `flask seed-db`

| Rôle | Nom & Prénom | Email | Mot de passe | Détails |
| :--- | :--- | :--- | :--- | :--- |
| **MEDECIN** | Dr Cheikh Ndiaye | `dr.ndiaye@esante.sn` | `Medecin@2026` | Cardiologie (`ONMS-DKR-001`) — 15 000 FCFA |
| **MEDECIN** | Dr Fatou Sow | `dr.sow@esante.sn` | `Medecin@2026` | Pédiatrie (`ONMS-SL-002`) — 10 000 FCFA |
| **PATIENT** | Aminata Diop | `aminata.diop@esante.sn` | `Patient@2026` | Mermoz, Dakar |
| **PATIENT** | Moussa Fall | `moussa.fall@esante.sn` | `Patient@2026` | Escale, Thiès |

---

## 6. Documentation des Endpoints REST

| Méthode | Endpoint | Accès / Rôle | Statuts HTTP | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | `200`, `503` | Vérifie l'état du service et de la connexion PostgreSQL |
| `POST` | `/api/auth/register` | Public | `201`, `400`, `409` | Inscription d'un `PATIENT` ou d'un `MEDECIN` |
| `POST` | `/api/auth/login` | Public | `200`, `401` | Connexion et génération du token JWT (inclut le claim `role`) |
| `GET` | `/api/medecins` | Public | `200` | Liste les médecins (filtrable via `?specialite=Cardiologie`) |
| `GET` | `/api/medecins/<id>/disponibilites` | Public | `200`, `404` | Liste les créneaux libres (`est_reserve=False`) d'un médecin |
| `POST` | `/api/rendezvous` | `PATIENT` (JWT) | `201`, `403`, `404`, `409` | Réserve un créneau et crée un RDV (`EN_ATTENTE`) |
| `GET` | `/api/rendezvous?date=today` | `MEDECIN` (JWT) | `200`, `400`, `403` | Liste les RDV du médecin connecté (filtrable par date) |
| `PUT` | `/api/rendezvous/<id>` | `MEDECIN` (JWT) | `200`, `400`, `403`, `404` | Met à jour le statut (`ACCEPTE`, `ANNULE`, `REFUSE`, `TERMINE`) |
| `POST` | `/api/rendezvous/<id>/ordonnance` | `MEDECIN` (JWT) | `201`, `403`, `404`, `409`, `422` | Crée une ordonnance avec ses lignes (requiert un RDV `TERMINE`) |

### Exemples de requêtes (`curl`)

#### 1. Authentification (`POST /api/auth/login`)
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "aminata.diop@esante.sn", "mot_de_passe": "Patient@2026"}'
```

#### 2. Réserver un rendez-vous (`POST /api/rendezvous`)
```bash
curl -X POST http://localhost:5000/api/rendezvous \
  -H "Authorization: Bearer <TOKEN_JWT_PATIENT>" \
  -H "Content-Type: application/json" \
  -d '{"id_disponibilite": 1, "motif": "Contrôle tensionnel"}'
```

#### 3. Créer une ordonnance sur un RDV terminé (`POST /api/rendezvous/<id>/ordonnance`)
```bash
curl -X POST http://localhost:5000/api/rendezvous/1/ordonnance \
  -H "Authorization: Bearer <TOKEN_JWT_MEDECIN>" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Repos strict et régime hyposodé.",
    "lignes": [
      {
        "medicament": "Amlodipine 5mg",
        "posologie": "1 comprimé chaque matin",
        "duree": "30 jours",
        "quantite": 1
      }
    ]
  }'
```

---

## 7. Tests Automatisés & Sécurité

Les tests utilisent une base SQLite en mémoire isolée (`TestingConfig`) et vérifient :
- Le endpoint `/health` (`200 OK`).
- L'inscription, la connexion JWT et le refus d'accès (`403 Forbidden`) en cas de mauvais rôle (`PATIENT` vs `MEDECIN`).
- Le retour **`409 Conflict`** lors de la réservation simultanée d'un même créneau par deux patients.
- Le retour **`422 Unprocessable Entity`** lors de la création d'une ordonnance sur un RDV non terminé, puis **`201 Created`** une fois le RDV passé à `TERMINE`.
- La libération de la disponibilité (`est_reserve = False`) lors de l'annulation (`ANNULE`) d'un RDV.

### Lancer la suite de tests Pytest
```bash
pytest tests/ -v
```

### Lancer l'analyse de sécurité statique (Bandit)
```bash
bandit -r app/ -ll -ii
```

---

## 8. Docker & Pipeline CI/CD Jenkins

### Construction et exécution avec Docker
Le `Dockerfile` multi-stage compile les wheels Python dans une image `builder`, puis copie uniquement les artefacts nécessaires dans une image `python:3.11-slim` exécutée sous l'utilisateur non-privilégié `appuser` avec **Gunicorn** (4 workers sur le port `5000`).

```bash
# Construire l'image de production
docker build -t esante-senegal-backend:latest .

# Lancer le conteneur
docker run -d --name esante-backend \
  -p 5000:5000 \
  -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:5432/esante_senegal_prod" \
  -e SECRET_KEY="prod-secret" \
  -e JWT_SECRET_KEY="prod-jwt-secret" \
  esante-senegal-backend:latest
```

### Pipeline CI (`Jenkinsfile`)
À chaque `git push`, Jenkins exécute séquentiellement les étapes suivantes :
1. **Checkout** : Récupération du code source depuis le dépôt Git `backend-ci`.
2. **Install dependencies** : Création d'un environnement virtuel `.venv` et installation de `requirements.txt`.
3. **Pytest** : Exécution des tests unitaires et d'intégration avec publication du rapport JUnit (`pytest-report.xml`).
4. **Scan de sécurité du code (Bandit)** : Analyse SAST du dossier `app/` pour détecter les failles de sécurité Python.
5. **Docker Build** : Construction de l'image Docker multi-stage taguée avec le numéro de build (`${BUILD_NUMBER}`) et `latest`.
6. **Scan de vulnérabilités (Trivy)** : Inspection des vulnérabilités CVE de l'image Docker (bloque le pipeline en cas de vulnérabilité `CRITICAL` corrigée).
7. **Docker Push vers Docker Hub** : Authentification via les credentials Jenkins (`dockerhub-credentials`) et publication de l'image sur Docker Hub (branches `main`/`master`).
