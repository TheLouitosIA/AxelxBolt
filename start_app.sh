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
uvicorn app:app --reload

# Lancer ngrok avec le sous-domaine statique configuré dans ngrok.yml
ngrok start app
