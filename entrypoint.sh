#!/bin/sh
set -e

echo "==> Initialisation de la base de données..."
if [ -d "migrations" ]; then
    echo "    Dossier migrations/ détecté : flask db upgrade"
    flask db upgrade
else
    echo "    Pas de dossier migrations/ : flask create-tables"
    flask create-tables
fi

echo "==> Démarrage de Gunicorn..."
exec gunicorn -w "${GUNICORN_WORKERS:-4}" -b "0.0.0.0:${PORT:-5000}" --access-logfile - --error-logfile - run:app
