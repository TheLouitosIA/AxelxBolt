#!/bin/bash

# Activation de l'environnement virtuel
if [[ "$OSTYPE" == "msys" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Unix-based
    source venv/bin/activate
fi

# Lancer l'application FastAPI
uvicorn app:app --host 0.0.0.0 --port 8000 &

# Lancer ngrok avec le sous-domaine statique configuré dans ngrok.yml
ngrok start default
