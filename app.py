import psycopg2
import os
import cv2  # Import OpenCV pour lire l'image
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Header, Query
import detect  # Importation du script YOLO
from db_connection import get_connection
import json  # Import JSON pour convertir le dictionnaire
from datetime import datetime, timedelta, date
from pydantic import EmailStr, constr, BaseModel, field_validator
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import hashlib
from jose import JWTError, jwt
import re
from typing import Optional
from uuid import uuid4
from detect import detect_image, validate_detection
import easyocr  # Import EasyOCR
from difflib import SequenceMatcher

app = FastAPI()
date_prise = datetime.now().isoformat()  # Format ISO pour la date et heure actuelle
API_TOKEN = "AXL_api_key_validation314"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Autoriser React sur le port 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèle Pydantic pour les utilisateurs
class User(BaseModel):
    nom: constr(min_length=2, max_length=50) # type: ignore
    prenom: constr(min_length=2, max_length=50) # type: ignore
    email: EmailStr
    telephone: str
    marque_voiture: constr(min_length=2, max_length=50) # type: ignore
    plaque_immatriculation: constr(min_length=2, max_length=15) # type: ignore
    password: constr(min_length=8) # type: ignore

    @field_validator('telephone')
    def telephone_format(cls, v):
        if not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError("Le numéro de téléphone n'est pas dans un format valide.")
        return v

class Photo(BaseModel):
    utilisateur_id: int
    type_photo: str
    chemin_photo: str
    date_prise: str  # Format ISO 8601, ex : "2024-11-01T12:00:00"

class Validation(BaseModel):
    utilisateur_id: int
    mois_verification: str  # Format YYYY-MM, par exemple "2024-11"
    resultat: bool

class RecherchePhoto(BaseModel):
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None

# Connexion à la base de données
def get_connection():
    return psycopg2.connect(
        dbname="chauffeurs_db",
        user="app_user",
        password="AXL_userapp",
        host="localhost",
        port="5432"
    )

def verify_token(x_api_token: str = Header(...)):
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Accès non autorisé")

def verifier_photos_mensuelles(utilisateur_id: int, mois: str):
    try:
        # Calcul des dates de début et de fin pour le mois
        date_debut = datetime.strptime(mois, "%Y-%m")
        date_fin = (date_debut.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        conn = get_connection()
        cur = conn.cursor()

        # Liste des types de photos requis
        types_photos_requis = ["face", "droite", "gauche", "plaque", "compteur"]
        photos_valides = set()  # Pour collecter les types validés

        # Vérification pour chaque type requis
        for type_photo in types_photos_requis:
            query = """
                SELECT COUNT(*)
                FROM photos
                WHERE utilisateur_id = %s
                  AND type_photo = %s
                  AND date_prise BETWEEN %s AND %s
                  AND statut_validation = 'validé'
            """
            cur.execute(query, (utilisateur_id, type_photo, date_debut, date_fin))
            result = cur.fetchone()

            # Ajout au set des types validés si au moins une photo est correcte
            if result and result[0] > 0:
                photos_valides.add(type_photo)

        # Vérifier si tous les types requis sont validés
        if set(types_photos_requis) == photos_valides:
            query = """
                INSERT INTO validations (utilisateur_id, mois_verification, resultat)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (utilisateur_id, mois_verification)
                DO UPDATE SET resultat = TRUE
            """
            cur.execute(query, (utilisateur_id, mois))
        else:
            # Notification des types manquants/non conformes
            types_non_valides = set(types_photos_requis) - photos_valides
            message = f"Photos non conformes ou manquantes pour les types : {', '.join(types_non_valides)}."
            notification_query = """
                INSERT INTO notifications (utilisateur_id, mois, message)
                VALUES (%s, %s, %s)
            """
            cur.execute(notification_query, (utilisateur_id, mois, message))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "validation_status": "validé" if set(types_photos_requis) == photos_valides else "non validé",
            "types_valides": list(photos_valides),
            "types_non_valides": list(set(types_photos_requis) - photos_valides),
        }
    except Exception as e:
        return {"error": f"Erreur lors de la vérification des photos mensuelles : {e}"} 

# Clé secrète et algorithme pour JWT
SECRET_KEY = "secret_key_for_token"  # Utilisez une clé secrète forte pour la production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Modèle de connexion
class LoginData(BaseModel):
    email: EmailStr
    password: constr(min_length=8)  # Contrainte de longueur minimale pour le mot de passe

# Fonction pour générer un token JWT
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Fonction pour vérifier le token
def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

# Fonction pour hacher les mots de passe
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def normalize_plate(plate):
    """
    Nettoie une plaque en supprimant les caractères inutiles et en mettant en majuscules.
    """
    return re.sub(r'[^A-Z0-9]', '', plate.upper())  # Conserve uniquement lettres et chiffres

def is_similar(plate1, plate2, threshold=0.8):
    """
    Compare deux plaques d'immatriculation et retourne True si elles sont similaires au-dessus du seuil donné.
    """
    similarity = SequenceMatcher(None, plate1, plate2).ratio()
    return similarity >= threshold

# Route d'inscription
@app.post("/inscription/", summary="Inscription d'un nouvel utilisateur")
async def inscrire_utilisateur(user: User):
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT * FROM utilisateurs WHERE email = %s OR telephone = %s
        """
        cur.execute(query, (user.email, user.telephone))
        existing_user = cur.fetchone()

        if existing_user:
            cur.close()
            conn.close()
            return {"error": "Un utilisateur avec cet email ou ce numéro de téléphone existe déjà."}

        hashed_password = hash_password(user.password)

        query = """
            INSERT INTO utilisateurs (nom, prenom, email, telephone, marque_voiture, plaque_immatriculation, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (
            user.nom, user.prenom, user.email, user.telephone, user.marque_voiture, user.plaque_immatriculation, hashed_password
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Utilisateur inscrit avec succès"}
    except Exception as e:
        return {"error": f"Erreur lors de l'inscription : {e}"}

# Route de connexion
@app.post("/login")
async def login(login_data: LoginData):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Hachage du mot de passe pour la comparaison
        hashed_password = hash_password(login_data.password)

        # Vérification des identifiants dans la base de données
        query = """
            SELECT id, nom, email FROM utilisateurs WHERE email = %s AND password = %s
        """
        cur.execute(query, (login_data.email, hashed_password))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            # Générer un token JWT
            token = create_access_token(data={"sub": user[2]})  # Utiliser l'email comme 'sub' pour le token
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user[0],
                    "nom": user[1],
                    "email": user[2]
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    except Exception as e:
        return {"error": f"Erreur lors de la connexion : {str(e)}"}

# Dépendance pour protéger les routes
def get_current_user(token: str = Depends(verify_token)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Impossible de vérifier les informations d'identification.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return verify_access_token(token, credentials_exception)

# Route protégée d'exemple
@app.get("/protected_route")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Bienvenue {current_user['sub']}"}

# Autres routes...

@app.post("/photos/")
async def ajouter_photo(photo: Photo):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            INSERT INTO photos (utilisateur_id, type_photo, chemin_photo, date_prise)
            VALUES (%s, %s, %s, %s)
        """
        cur.execute(query, (
            photo.utilisateur_id, photo.type_photo, photo.chemin_photo, photo.date_prise
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Photo ajoutée avec succès"}
    except Exception as e:
        return {"error": f"Erreur lors de l'ajout de la photo : {e}"}

# Gestion des erreurs
@app.exception_handler(psycopg2.DatabaseError)
async def database_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Erreur de base de données. Veuillez réessayer plus tard."},
    )

@app.exception_handler(ValueError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Données non valides", "details": str(exc)},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"error": "Ressource non trouvée"},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )
    
@app.post("/validations/")
async def ajouter_validation(validation: Validation):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            INSERT INTO validations (utilisateur_id, mois_verification, resultat)
            VALUES (%s, %s, %s)
        """
        cur.execute(query, (
            validation.utilisateur_id, validation.mois_verification, validation.resultat
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Validation ajoutée avec succès"}
    except Exception as e:
        return {"error": f"Erreur lors de l'ajout de la validation : {e}"}

@app.post("/detect/")
async def detect_vehicle(utilisateur_id: int, type_photo: str, image: UploadFile = File(...)):
    """
    Analyse une photo, détecte les éléments avec YOLO, applique l'OCR pour les plaques,
    et compare la plaque détectée avec celle enregistrée pour l'utilisateur dans la base de données.
    """
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    image_path = os.path.join(temp_dir, image.filename)
    try:
        # Enregistrement temporaire de l'image
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())

        # Lecture de l'image en tant que tableau numpy
        image_np = cv2.imread(image_path)

        # Initialisation d'EasyOCR
        ocr_reader = easyocr.Reader(['en'], gpu=True)

        # Détection des éléments sur l'image
        results = detect_image(image_np)

        # Récupérer la plaque d'immatriculation de l'utilisateur depuis la base
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT plaque_immatriculation FROM utilisateurs WHERE id = %s
        """
        cur.execute(query, (utilisateur_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        if not user_data:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")

        registered_plate = user_data[0]  # La plaque enregistrée pour l'utilisateur
        registered_plate_normalized = normalize_plate(registered_plate)  # Normalisation

        # Résultats OCR
        ocr_results = []
        for result in results:
            # Appliquer l'OCR uniquement pour les détections de classe 2 (plaque)
            if result.get("class") == 2:
                x1, y1, x2, y2 = result["bbox"]
                cropped_img = image_np[y1:y2, x1:x2]  # Découper la région de la plaque
                ocr_texts = ocr_reader.readtext(cropped_img, detail=0)  # OCR avec EasyOCR
                ocr_text = ocr_texts[0] if ocr_texts else None
                ocr_text_normalized = normalize_plate(ocr_text) if ocr_text else None  # Normalisation

                # Ajouter le texte OCR au résultat avec normalisation
                result["text"] = ocr_text
                result["text_normalized"] = ocr_text_normalized
                if ocr_text:
                    ocr_results.append({
                        "bbox": result["bbox"],
                        "confidence": result["confidence"],
                        "class_id": result["class"],
                        "text": ocr_text,
                        "text_normalized": ocr_text_normalized
                    })

        # Validation des plaques détectées avec tolérance
        is_valid = any(
            is_similar(registered_plate_normalized, result["text_normalized"])
            for result in ocr_results
        )
        validation_status = "validé" if is_valid else "non validé"

        # Formatage des résultats pour stockage
        results_formatted = [
            {
                "bbox": result.get("bbox", []),
                "confidence": round(result.get("confidence", 0), 2),
                "class_id": result.get("class"),
                "text": result.get("text", None)
            }
            for result in results
        ]

        # Sérialisation des résultats pour la base de données
        results_json = json.dumps(results_formatted)
        conn = get_connection()
        cur = conn.cursor()

        # Enregistrement dans la base de données
        date_prise = datetime.now().isoformat()
        mois_verification = datetime.now().strftime("%Y-%m")
        query = """
            INSERT INTO photos (utilisateur_id, type_photo, chemin_photo, date_prise, resultat_detection, statut_validation)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (
            utilisateur_id,
            type_photo,
            image_path,
            date_prise,
            results_json,
            validation_status
        ))

        # Vérification des photos mensuelles pour l'utilisateur
        verifier_photos_mensuelles(utilisateur_id, mois_verification)

        # Sauvegarde des modifications
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        return {"error": f"Erreur lors de l'ajout de la photo : {e}"}
    finally:
        # Suppression de l'image temporaire
        os.remove(image_path)

    return {
        "utilisateur_id": utilisateur_id,
        "type_photo": type_photo,
        "validation_status": validation_status,
        "registered_plate": registered_plate,
        "registered_plate_normalized": registered_plate_normalized,
        "detections": results_formatted,
        "ocr_results": ocr_results
    }


@app.get("/suivi_validations/")
async def suivi_validations(utilisateur_id: int, mois: str = Query(None, description="Format YYYY-MM")):
    """
    Récupère le statut de validation pour un utilisateur donné pour un mois spécifique.
    Si aucun mois n'est fourni, récupère l'historique complet.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Si un mois est spécifié, récupérer les validations pour ce mois
        if mois:
            query = """
                SELECT mois_verification, resultat FROM validations
                WHERE utilisateur_id = %s AND mois_verification = %s
            """
            cur.execute(query, (utilisateur_id, mois))
        else:
            # Récupérer l'historique complet si aucun mois n'est spécifié
            query = """
                SELECT mois_verification, resultat FROM validations
                WHERE utilisateur_id = %s
            """
            cur.execute(query, (utilisateur_id,))

        validations = cur.fetchall()
        cur.close()
        conn.close()

        # Formatage des résultats pour affichage
        resultats = [{"mois_verification": val[0], "resultat": "validé" if val[1] else "non validé"} for val in validations]

        return {"historique_validations": resultats}
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des validations : {e}"}

@app.get("/photos_mensuelles/")
async def photos_mensuelles(utilisateur_id: int, mois: str):
    """
    Récupère toutes les photos d'un utilisateur pour un mois spécifique, avec leur statut de validation et informations de détection.
    """
    try:
        # Calcul de la plage de dates pour le mois donné
        date_debut = datetime.strptime(mois, "%Y-%m")
        date_fin = (date_debut.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT type_photo, chemin_photo, date_prise, statut_validation, resultat_detection
            FROM photos
            WHERE utilisateur_id = %s AND date_prise >= %s AND date_prise <= %s
        """
        cur.execute(query, (utilisateur_id, date_debut, date_fin))
        photos = cur.fetchall()
        cur.close()
        conn.close()

        # Formatage des résultats et récapitulatif
        photos_formatees = []
        recapitulatif = {"validé": 0, "non validé": 0}

        for photo in photos:
            statut = "validé" if photo[3] == "validé" else "non validé"

            # Vérifier le type de resultat_detection
            if isinstance(photo[4], (dict, list)):
                resultat_detection = photo[4]  # Utiliser directement si c'est déjà un dict ou une liste
            elif photo[4]:  # Charger comme JSON si c'est une chaîne JSON
                resultat_detection = json.loads(photo[4])
            else:
                resultat_detection = {}  # Utiliser un dict vide si la valeur est None

            photos_formatees.append({
                "type_photo": photo[0],
                "chemin_photo": photo[1],
                "date_prise": photo[2],
                "statut_validation": statut,
                "resultat_detection": resultat_detection
            })
            recapitulatif[statut] += 1  # Compte les photos validées/non validées

        return {
            "photos_mensuelles": photos_formatees,
            "recapitulatif": recapitulatif
        }
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des photos mensuelles : {e}"}

@app.get("/utilisateur/{utilisateur_id}", summary="Récupérer les informations d'un utilisateur")
async def obtenir_utilisateur(utilisateur_id: int):
    """
    Récupère les informations complètes d'un utilisateur, y compris le mot de passe.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT nom, prenom, email, telephone, marque_voiture, plaque_immatriculation, password
            FROM utilisateurs WHERE id = %s
        """
        cur.execute(query, (utilisateur_id,))
        utilisateur = cur.fetchone()
        cur.close()
        conn.close()

        if utilisateur:
            return {
                "utilisateur": {
                    "nom": utilisateur[0],
                    "prenom": utilisateur[1],
                    "email": utilisateur[2],
                    "telephone": utilisateur[3],
                    "marque_voiture": utilisateur[4],
                    "plaque_immatriculation": utilisateur[5],
                    "password": utilisateur[6]  # Ajout du mot de passe
                }
            }
        else:
            return {"error": "Utilisateur non trouvé."}
    except Exception as e:
        return {"error": f"Erreur lors de la récupération de l'utilisateur : {e}"}
    
@app.put("/mise_a_jour_utilisateur/{utilisateur_id}", summary="Mettre à jour les informations d'un utilisateur")
async def mettre_a_jour_utilisateur(utilisateur_id: int, user: User, token: str = Depends(verify_token)):
    """
    Met à jour les informations d'un utilisateur existant.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Vérifier si l'utilisateur existe
        query = "SELECT * FROM utilisateurs WHERE id = %s"
        cur.execute(query, (utilisateur_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        # Mettre à jour les informations
        query = """
            UPDATE utilisateurs SET nom = %s, prenom = %s, email = %s, telephone = %s,
            marque_voiture = %s, plaque_immatriculation = %s
            WHERE id = %s
        """
        cur.execute(query, (
            user.nom, user.prenom, user.email, user.telephone,
            user.marque_voiture, user.plaque_immatriculation, utilisateur_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Informations de l'utilisateur mises à jour avec succès"}
    except Exception as e:
        return {"error": f"Erreur lors de la mise à jour de l'utilisateur : {e}"}

@app.get("/recherche_photos/", summary="Rechercher les photos selon des critères spécifiques")
async def recherche_photos(
    utilisateur_id: int,
    type_photo: Optional[str] = Query(None, description="Type de photo (face, droite, gauche, plaque, compteur)"),
    statut_validation: Optional[str] = Query(None, description="Statut de validation (validé ou non validé)"),
    date_debut: Optional[str] = Query(None, description="Date de début au format YYYY-MM-DD"),
    date_fin: Optional[str] = Query(None, description="Date de fin au format YYYY-MM-DD"),
    tri: Optional[str] = Query("desc", description="Ordre de tri par date (asc ou desc)")
):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Construction de la requête SQL dynamique
        query = """
            SELECT type_photo, chemin_photo, date_prise, statut_validation, resultat_detection
            FROM photos
            WHERE utilisateur_id = %s
        """
        params = [utilisateur_id]

        # Ajout des filtres dynamiques
        if type_photo:
            query += " AND type_photo = %s"
            params.append(type_photo)
        
        if statut_validation:
            query += " AND statut_validation = %s"
            params.append(statut_validation)

        if date_debut and date_fin:
            query += " AND date_prise BETWEEN %s AND %s"
            params.extend([date_debut, date_fin])
        
        # Ajout de l’ordre de tri
        query += " ORDER BY date_prise " + ("ASC" if tri == "asc" else "DESC")

        # Exécution de la requête
        cur.execute(query, tuple(params))
        photos = cur.fetchall()
        cur.close()
        conn.close()

        # Formatage des résultats
        photos_formatees = []
        for photo in photos:
            # Vérifie et formate resultat_detection
            resultat_detection = photo[4]
            if isinstance(resultat_detection, str):
                resultat_detection = json.loads(resultat_detection)  # Convertit en JSON si c'est une chaîne
            elif not isinstance(resultat_detection, dict):
                resultat_detection = {}  # Utilise un dictionnaire vide si le type n'est pas compatible

            photos_formatees.append({
                "type_photo": photo[0],
                "chemin_photo": photo[1],
                "date_prise": photo[2],
                "statut_validation": photo[3],
                "resultat_detection": resultat_detection
            })

        return {"photos_filtrees": photos_formatees}
    except Exception as e:
        return {"error": f"Erreur lors de la recherche des photos : {e}"}


@app.get("/verifier_conformite/", summary="Vérifier la conformité des photos mensuelles d'un utilisateur")
async def verifier_conformite(utilisateur_id: int, mois: str = Query(..., description="Format YYYY-MM")):
    """
    Vérifie la conformité des photos d'un utilisateur pour le mois donné.
    """
    if not mois:
        raise HTTPException(status_code=400, detail="Le paramètre 'mois' est requis et doit être au format YYYY-MM.")

    try:
        # Appel de la fonction de vérification
        rapport = verifier_photos_mensuelles(utilisateur_id, mois)

        # Génération d'une notification si des photos sont non conformes
        if "photos_non_conformes" in rapport:
            rapport["notification"] = "Certaines photos sont manquantes ou non conformes. Veuillez les soumettre à nouveau."

        return rapport
    except Exception as e:
        return {"error": f"Erreur lors de la vérification de la conformité : {e}"}

    
@app.get("/notifications/{utilisateur_id}", summary="Récupérer les notifications d'un utilisateur")
async def obtenir_notifications(utilisateur_id: int):
    """
    Récupère toutes les notifications d'un utilisateur concernant les photos non conformes.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT mois, message, date_notification FROM notifications
            WHERE utilisateur_id = %s
            ORDER BY date_notification DESC
        """
        cur.execute(query, (utilisateur_id,))
        notifications = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {"mois": n[0], "message": n[1], "date_notification": n[2]}
            for n in notifications
        ]
    except Exception as e:
        return {"error": f"Erreur lors de la récupération des notifications : {e}"}

@app.exception_handler(psycopg2.DatabaseError)
async def database_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Erreur de base de données. Veuillez réessayer plus tard."},
    )

@app.exception_handler(ValueError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Données non valides", "details": str(exc)},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"error": "Ressource non trouvée"},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.get("/")
async def root():
    return {"message": "API Chauffeurs est opérationnelle"}

# Gestion des erreurs globales
@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Une erreur interne est survenue", "details": str(exc)},
    )

@app.post("/mot_de_passe_oublie/")
async def mot_de_passe_oublie(email: EmailStr):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Vérifie si l'utilisateur existe
        query = "SELECT id FROM utilisateurs WHERE email = %s"
        cur.execute(query, (email,))
        utilisateur = cur.fetchone()

        if not utilisateur:
            return {"error": "Aucun utilisateur trouvé avec cet email."}

        utilisateur_id = utilisateur[0]
        token = str(uuid4())  # Génère un jeton unique
        date_expiration = datetime.utcnow() + timedelta(hours=1)  # Valide 1 heure

        # Insère le jeton dans la base
        query = """
            INSERT INTO reset_tokens (utilisateur_id, token, date_expiration)
            VALUES (%s, %s, %s)
        """
        cur.execute(query, (utilisateur_id, token, date_expiration))
        conn.commit()

        # Simule l'envoi d'un email (dans la vraie vie, utiliser un service d'email)
        reset_url = f"http://localhost:3000/reset/{token}"
        print(f"Lien de réinitialisation : {reset_url}")

        cur.close()
        conn.close()
        return {"message": "Lien de réinitialisation envoyé à votre email."}
    except Exception as e:
        return {"error": f"Erreur lors de la génération du lien de réinitialisation : {e}"}

@app.post("/reset_password/")
async def reset_password(token: str, new_password: str):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Vérifie le jeton
        query = """
            SELECT utilisateur_id FROM reset_tokens
            WHERE token = %s AND date_expiration > %s
        """
        cur.execute(query, (token, datetime.utcnow()))
        utilisateur = cur.fetchone()

        if not utilisateur:
            return {"error": "Jeton invalide ou expiré."}

        utilisateur_id = utilisateur[0]
        hashed_password = hash_password(new_password)

        # Met à jour le mot de passe de l'utilisateur
        query = "UPDATE utilisateurs SET password = %s WHERE id = %s"
        cur.execute(query, (hashed_password, utilisateur_id))

        # Supprime le jeton après utilisation
        query = "DELETE FROM reset_tokens WHERE token = %s"
        cur.execute(query, (token,))
        
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Mot de passe réinitialisé avec succès."}
    except Exception as e:
        return {"error": f"Erreur lors de la réinitialisation du mot de passe : {e}"}
