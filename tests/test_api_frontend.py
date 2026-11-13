"""Tests des routes ajoutées pour l'interface React (historique, disponibilités, ordonnances, déplacement)."""

from datetime import date, datetime, timedelta

from tests.test_api import _login_and_get_headers


def _headers(client):
    patient = _login_and_get_headers(client, "aminata@esante.sn", "Patient@123")
    medecin = _login_and_get_headers(client, "dr.ndiaye@esante.sn", "Medecin@123")
    return patient, medecin


def _reserver(client, headers, id_dispo, motif="Contrôle"):
    resp = client.post(
        "/api/rendezvous", json={"id_disponibilite": id_dispo, "motif": motif}, headers=headers
    )
    assert resp.status_code == 201
    return resp.get_json()


def test_rendezvous_contient_patient_et_medecin_imbriques(client, seed_data):
    patient, medecin = _headers(client)
    rdv = _reserver(client, patient, seed_data["disponibilite_id"])
    assert rdv["patient"]["nom"] == "Diop"
    assert rdv["medecin"]["specialite"]["libelle"] == "Cardiologie"

    agenda = client.get("/api/rendezvous", headers=medecin).get_json()
    assert agenda[0]["patient"]["prenom"] == "Aminata"


def test_historique_patient_et_isolation(client, seed_data):
    patient, _ = _headers(client)
    autre = _login_and_get_headers(client, "moussa@esante.sn", "Patient@123")
    _reserver(client, patient, seed_data["disponibilite_id"])

    mes = client.get(f"/api/patients/{seed_data['patient_1_id']}/rendezvous", headers=patient)
    assert mes.status_code == 200 and len(mes.get_json()) == 1
    # Un autre patient ne voit pas ces données, et un médecin n'y a pas accès
    assert client.get(f"/api/patients/{seed_data['patient_1_id']}/rendezvous", headers=autre).status_code == 403
    _, medecin = _headers(client)
    assert client.get(f"/api/patients/{seed_data['patient_1_id']}/rendezvous", headers=medecin).status_code == 403


def test_transition_interdite_422(client, seed_data):
    patient, medecin = _headers(client)
    rdv = _reserver(client, patient, seed_data["disponibilite_id"])
    # EN_ATTENTE -> TERMINE n'est pas autorisé
    resp = client.put(f"/api/rendezvous/{rdv['id']}", json={"statut": "TERMINE"}, headers=medecin)
    assert resp.status_code == 422
    assert client.put(f"/api/rendezvous/{rdv['id']}", json={"statut": "ACCEPTE"}, headers=medecin).status_code == 200
    # ANNULE est final
    assert client.put(f"/api/rendezvous/{rdv['id']}", json={"statut": "ANNULE"}, headers=medecin).status_code == 200
    assert client.put(f"/api/rendezvous/{rdv['id']}", json={"statut": "ACCEPTE"}, headers=medecin).status_code == 422


def test_gestion_disponibilites_medecin(client, seed_data):
    patient, medecin = _headers(client)
    mid = seed_data["medecin_id"]
    debut = datetime.combine(date.today(), datetime.min.time()) + timedelta(days=1, hours=14)

    # Création, puis chevauchement refusé (409), fin avant début refusée (400)
    ok = client.post(
        f"/api/medecins/{mid}/disponibilites",
        json={"date_heure_debut": debut.isoformat(), "date_heure_fin": (debut + timedelta(minutes=30)).isoformat()},
        headers=medecin,
    )
    assert ok.status_code == 201
    nouveau_id = ok.get_json()["id"]
    chevauche = client.post(
        f"/api/medecins/{mid}/disponibilites",
        json={"date_heure_debut": (debut + timedelta(minutes=15)).isoformat(), "date_heure_fin": (debut + timedelta(minutes=45)).isoformat()},
        headers=medecin,
    )
    assert chevauche.status_code == 409
    inverse = client.post(
        f"/api/medecins/{mid}/disponibilites",
        json={"date_heure_debut": debut.isoformat(), "date_heure_fin": (debut - timedelta(minutes=5)).isoformat()},
        headers=medecin,
    )
    assert inverse.status_code == 400
    # Un patient ne peut pas créer de créneau
    assert client.post(
        f"/api/medecins/{mid}/disponibilites",
        json={"date_heure_debut": debut.isoformat(), "date_heure_fin": (debut + timedelta(hours=1)).isoformat()},
        headers=patient,
    ).status_code == 403

    # ?toutes=true : créneaux libres et réservés, réservé au médecin
    _reserver(client, patient, seed_data["disponibilite_id"])
    toutes = client.get(f"/api/medecins/{mid}/disponibilites?toutes=true", headers=medecin).get_json()
    assert len(toutes) == 2 and any(d["est_reserve"] for d in toutes)
    assert client.get(f"/api/medecins/{mid}/disponibilites?toutes=true").status_code in (401, 422)
    assert len(client.get(f"/api/medecins/{mid}/disponibilites").get_json()) == 1  # public : libres seulement

    # Suppression : refusée si réservé (409), acceptée sinon (204)
    assert client.delete(f"/api/disponibilites/{seed_data['disponibilite_id']}", headers=medecin).status_code == 409
    assert client.delete(f"/api/disponibilites/{nouveau_id}", headers=medecin).status_code == 204
    assert client.delete(f"/api/disponibilites/{nouveau_id}", headers=medecin).status_code == 404


def test_deplacement_rendezvous_vers_autre_creneau(client, seed_data):
    patient, medecin = _headers(client)
    mid = seed_data["medecin_id"]
    debut = datetime.combine(date.today(), datetime.min.time()) + timedelta(days=1, hours=9)
    autre = client.post(
        f"/api/medecins/{mid}/disponibilites",
        json={"date_heure_debut": debut.isoformat(), "date_heure_fin": (debut + timedelta(minutes=30)).isoformat()},
        headers=medecin,
    ).get_json()
    rdv = _reserver(client, patient, seed_data["disponibilite_id"])

    resp = client.put(f"/api/rendezvous/{rdv['id']}", json={"id_disponibilite": autre["id"]}, headers=medecin)
    assert resp.status_code == 200
    assert resp.get_json()["id_disponibilite"] == autre["id"]
    # L'ancien créneau est de nouveau libre, le nouveau est pris
    libres = {d["id"] for d in client.get(f"/api/medecins/{mid}/disponibilites").get_json()}
    assert libres == {seed_data["disponibilite_id"]}


def test_listes_ordonnances_patient_et_medecin(client, seed_data):
    patient, medecin = _headers(client)
    rdv = _reserver(client, patient, seed_data["disponibilite_id"])
    for statut in ("ACCEPTE", "TERMINE"):
        client.put(f"/api/rendezvous/{rdv['id']}", json={"statut": statut}, headers=medecin)
    ordo = client.post(
        f"/api/rendezvous/{rdv['id']}/ordonnance",
        json={"instructions": "Repos", "lignes": [{"medicament": "Paracétamol", "posologie": "1/j", "duree": "5 jours", "quantite": 1}]},
        headers=medecin,
    )
    assert ordo.status_code == 201
    assert ordo.get_json()["medecin"]["nom"] == "Ndiaye"

    cote_patient = client.get(f"/api/patients/{seed_data['patient_1_id']}/ordonnances", headers=patient).get_json()
    assert len(cote_patient) == 1 and cote_patient[0]["patient"]["nom"] == "Diop"
    cote_medecin = client.get(f"/api/medecins/{seed_data['medecin_id']}/ordonnances", headers=medecin).get_json()
    assert len(cote_medecin) == 1 and len(cote_medecin[0]["lignes"]) == 1
    # Isolation : le patient n'accède pas aux ordonnances émises par le médecin
    assert client.get(f"/api/medecins/{seed_data['medecin_id']}/ordonnances", headers=patient).status_code == 403


def test_seed_db_cree_des_creneaux_sur_plusieurs_jours_sans_doublon(app, client):
    """seed-db génère des créneaux futurs sur plusieurs jours et reste idempotent."""
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-db"]).exit_code == 0

    medecins = client.get("/api/medecins").get_json()
    assert len(medecins) == 2
    creneaux = client.get(f"/api/medecins/{medecins[0]['id']}/disponibilites").get_json()
    jours = {c["date_heure_debut"][:10] for c in creneaux}
    assert len(jours) >= 5
    assert all(c["date_heure_debut"] > datetime.now().isoformat() for c in creneaux)

    # Relancer le seed ne duplique ni les comptes ni les créneaux
    assert runner.invoke(args=["seed-db"]).exit_code == 0
    apres = client.get(f"/api/medecins/{medecins[0]['id']}/disponibilites").get_json()
    assert len(apres) == len(creneaux)
