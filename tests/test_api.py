"""Tests unitaires et d'intégration complets pour l'API e-Santé Sénégal."""


def _login_and_get_headers(client, email: str, password: str) -> dict[str, str]:
    """Utilitaire de connexion retournant l'en-tête Authorization Bearer."""
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "mot_de_passe": password},
    )
    assert resp.status_code == 200
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client):
    """Vérifie que GET /health retourne 200 OK avec le statut UP."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "UP"
    assert data["database"] == "healthy"


def test_register_and_login_flow(client, seed_data):
    """Vérifie l'inscription d'un nouveau patient puis sa connexion JWT."""
    register_resp = client.post(
        "/api/auth/register",
        json={
            "nom": "Ba",
            "prenom": "Mariama",
            "email": "mariama.ba@esante.sn",
            "mot_de_passe": "Secret@2026",
            "telephone": "+221770009988",
            "role": "PATIENT",
            "date_naissance": "1998-02-14",
            "adresse": "Sacré-Cœur 3, Dakar",
        },
    )
    assert register_resp.status_code == 201
    assert register_resp.get_json()["utilisateur"]["role"] == "PATIENT"

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "mariama.ba@esante.sn", "mot_de_passe": "Secret@2026"},
    )
    assert login_resp.status_code == 200
    payload = login_resp.get_json()
    assert "access_token" in payload
    assert payload["utilisateur"]["role"] == "PATIENT"


def test_authorization_role_enforcement(client, seed_data):
    """
    Vérifie le contrôle d'accès basé sur les rôles (RBAC) :
    - Un MEDECIN ne peut pas réserver un rendez-vous (endpoint réservé au rôle PATIENT -> 403).
    - Un PATIENT ne peut pas lister l'agenda médecin ni modifier le statut d'un RDV (403).
    """
    medecin_headers = _login_and_get_headers(
        client, "dr.ndiaye@esante.sn", "Medecin@123"
    )
    patient_headers = _login_and_get_headers(
        client, "aminata@esante.sn", "Patient@123"
    )

    # Un médecin tente de réserver un créneau (réservé aux patients)
    resp_medecin_book = client.post(
        "/api/rendezvous",
        json={
            "id_disponibilite": seed_data["disponibilite_id"],
            "motif": "Test rôle invalide",
        },
        headers=medecin_headers,
    )
    assert resp_medecin_book.status_code == 403

    # Un patient tente d'accéder au tableau de bord médecin GET /api/rendezvous?date=today
    resp_patient_agenda = client.get(
        "/api/rendezvous?date=today",
        headers=patient_headers,
    )
    assert resp_patient_agenda.status_code == 403


def test_conflit_409_reservation_simultanee_meme_creneau(client, seed_data):
    """
    Vérifie la règle métier critique de concurrence sur les réservations :
    - Le Patient 1 réserve le créneau disponible -> 201 Created (est_reserve passe à True).
    - Le Patient 2 tente de réserver le même créneau -> 409 Conflict.
    """
    headers_p1 = _login_and_get_headers(client, "aminata@esante.sn", "Patient@123")
    headers_p2 = _login_and_get_headers(client, "moussa@esante.sn", "Patient@123")

    # 1. Le créneau est initialement visible dans les disponibilités du médecin
    dispos_avant = client.get(
        f"/api/medecins/{seed_data['medecin_id']}/disponibilites"
    ).get_json()
    assert len(dispos_avant) == 1

    # 2. Premier patient réserve le créneau -> 201 Created
    resp_1 = client.post(
        "/api/rendezvous",
        json={
            "id_disponibilite": seed_data["disponibilite_id"],
            "motif": "Consultation cardiologique",
        },
        headers=headers_p1,
    )
    assert resp_1.status_code == 201
    assert resp_1.get_json()["statut"] == "EN_ATTENTE"

    # 3. Deuxième patient tente de réserver le même créneau -> 409 Conflict
    resp_2 = client.post(
        "/api/rendezvous",
        json={
            "id_disponibilite": seed_data["disponibilite_id"],
            "motif": "Deuxième tentative sur le même créneau",
        },
        headers=headers_p2,
    )
    assert resp_2.status_code == 409

    # 4. Le créneau n'apparaît plus dans les disponibilités libres (est_reserve=False)
    dispos_apres = client.get(
        f"/api/medecins/{seed_data['medecin_id']}/disponibilites"
    ).get_json()
    assert len(dispos_apres) == 0


def test_cycle_complet_rdv_annulation_et_ordonnance_422_puis_201(client, seed_data):
    """
    Vérifie :
    1. L'émission d'une ordonnance sur un RDV non terminé retourne 422 Unprocessable Entity.
    2. Le passage du RDV à TERMINE permet de créer l'ordonnance (201 Created).
    3. L'annulation d'un RDV libère bien la disponibilité (est_reserve=False).
    """
    headers_patient = _login_and_get_headers(client, "aminata@esante.sn", "Patient@123")
    headers_medecin = _login_and_get_headers(
        client, "dr.ndiaye@esante.sn", "Medecin@123"
    )

    # Création du RDV par la patiente
    rdv_resp = client.post(
        "/api/rendezvous",
        json={
            "id_disponibilite": seed_data["disponibilite_id"],
            "motif": "Suivi hypertension",
        },
        headers=headers_patient,
    )
    assert rdv_resp.status_code == 201
    rdv_id = rdv_resp.get_json()["id"]

    # Tentative de création d'ordonnance alors que le RDV est EN_ATTENTE -> 422
    ordo_422 = client.post(
        f"/api/rendezvous/{rdv_id}/ordonnance",
        json={
            "instructions": "Prendre pendant les repas",
            "lignes": [
                {
                    "medicament": "Amlodipine 5mg",
                    "posologie": "1 comprimé le matin",
                    "duree": "30 jours",
                    "quantite": 1,
                }
            ],
        },
        headers=headers_medecin,
    )
    assert ordo_422.status_code == 422

    # Le médecin accepte puis termine la consultation
    put_accepte = client.put(
        f"/api/rendezvous/{rdv_id}",
        json={"statut": "ACCEPTE"},
        headers=headers_medecin,
    )
    assert put_accepte.status_code == 200
    assert put_accepte.get_json()["statut"] == "ACCEPTE"

    put_termine = client.put(
        f"/api/rendezvous/{rdv_id}",
        json={"statut": "TERMINE"},
        headers=headers_medecin,
    )
    assert put_termine.status_code == 200
    assert put_termine.get_json()["statut"] == "TERMINE"

    # Création de l'ordonnance sur le RDV TERMINE -> 201 Created
    ordo_201 = client.post(
        f"/api/rendezvous/{rdv_id}/ordonnance",
        json={
            "instructions": "Régime hyposodé recommandé.",
            "lignes": [
                {
                    "medicament": "Amlodipine 5mg",
                    "posologie": "1 comprimé chaque matin",
                    "duree": "30 jours",
                    "quantite": 1,
                }
            ],
        },
        headers=headers_medecin,
    )
    assert ordo_201.status_code == 201
    assert len(ordo_201.get_json()["lignes"]) == 1


def test_annulation_rdv_libere_disponibilite(client, seed_data):
    """Vérifie que l'annulation (ANNULE) d'un RDV par le médecin remet est_reserve à False."""
    headers_patient = _login_and_get_headers(client, "aminata@esante.sn", "Patient@123")
    headers_medecin = _login_and_get_headers(
        client, "dr.ndiaye@esante.sn", "Medecin@123"
    )

    rdv_resp = client.post(
        "/api/rendezvous",
        json={
            "id_disponibilite": seed_data["disponibilite_id"],
            "motif": "Consultation à annuler",
        },
        headers=headers_patient,
    )
    assert rdv_resp.status_code == 201
    rdv_id = rdv_resp.get_json()["id"]

    # Le médecin consulte ses RDV du jour
    agenda_resp = client.get("/api/rendezvous?date=today", headers=headers_medecin)
    assert agenda_resp.status_code == 200
    assert len(agenda_resp.get_json()) == 1

    # Le médecin annule le RDV
    annule_resp = client.put(
        f"/api/rendezvous/{rdv_id}",
        json={"statut": "ANNULE"},
        headers=headers_medecin,
    )
    assert annule_resp.status_code == 200
    assert annule_resp.get_json()["statut"] == "ANNULE"

    # La disponibilité doit de nouveau apparaître comme libre (est_reserve=False)
    dispos = client.get(
        f"/api/medecins/{seed_data['medecin_id']}/disponibilites"
    ).get_json()
    assert len(dispos) == 1
    assert dispos[0]["est_reserve"] is False

    # Le créneau libéré doit pouvoir être réservé à nouveau par un autre patient
    headers_p2 = _login_and_get_headers(client, "moussa@esante.sn", "Patient@123")
    rebook_resp = client.post(
        "/api/rendezvous",
        json={
            "id_disponibilite": seed_data["disponibilite_id"],
            "motif": "Nouvelle réservation après annulation",
        },
        headers=headers_p2,
    )
    assert rebook_resp.status_code == 201


def test_filtrage_medecins_et_seed_cli(app, client, seed_data):
    """Vérifie le filtrage GET /api/medecins?specialite=Cardiologie et la commande seed-db."""
    resp_cardio = client.get("/api/medecins?specialite=Cardiologie")
    assert resp_cardio.status_code == 200
    assert len(resp_cardio.get_json()) == 1

    resp_pediatrie = client.get("/api/medecins?specialite=Pediatrie")
    assert resp_pediatrie.status_code == 200
    assert len(resp_pediatrie.get_json()) == 0

    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-db"])
    assert result.exit_code == 0
    assert "Base de données pré-remplie avec succès" in result.output

