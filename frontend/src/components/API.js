// src/components/API.js
import axios from "axios";

const API_URL = "http://localhost:8000"; // Assurez-vous que l'URL pointe vers votre serveur API

// Fonction pour connecter un utilisateur
export const loginUser = async (credentials) => {
  const response = await axios.post(`${API_URL}/login`, credentials);
  return response.data;
};

// Fonction pour inscrire un nouvel utilisateur
export const registerUser = async (formData) => {
  const response = await axios.post(`${API_URL}/inscription/`, formData);
  return response.data;
};

// Fonction pour appeler la détection avec validation et adapter l'URL
export const detectVehiclePhoto = async (file, utilisateurId, typePhoto) => {
  if (!utilisateurId || !typePhoto || !file) {
    console.error("Paramètres manquants pour detectVehiclePhoto", { utilisateurId, typePhoto, file });
    throw new Error("Paramètres manquants pour la requête.");
  }

  const formData = new FormData();
  formData.append("image", file); // Le fichier image est ajouté au formulaire

  const url = `${API_URL}/detect/?utilisateur_id=${utilisateurId}&type_photo=${typePhoto}`;
  console.log("URL de la requête : ", url);

  const response = await axios.post(url, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

// Fonction pour récupérer les résultats de validation des derniers mois
export const fetchValidationResults = async () => {
  const response = await axios.get(`${API_URL}/suivi_validations/`);
  return response.data;
};

// Fonction pour récupérer les photos filtrées pour un utilisateur spécifique
export const fetchPhotosByUser = async (userId) => {
  const response = await axios.get(`${API_URL}/recherche_photos/?utilisateur_id=${userId}&tri=desc`);
  return response.data.photos_filtrees;
};

// Fonction pour récupérer les informations utilisateur
export const fetchUserInfo = async (userId) => {
  const response = await axios.get(`${API_URL}/utilisateur/${userId}`);
  return response.data.utilisateur;
};