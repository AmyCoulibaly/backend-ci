"""Point d'entrée de l'application Flask (développement et serveur WSGI Gunicorn)."""

import os
from app import create_app

env_name = os.getenv("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    app.run(host=host, port=port)
