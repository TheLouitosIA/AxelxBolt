// src/components/TakePhoto.js
import React, { useState, useEffect } from "react";
import { detectVehiclePhoto } from "./API";
import { useNavigate } from "react-router-dom";
import "../css/TakePhoto.css";

const TakePhoto = () => {
  const [message, setMessage] = useState("");
  const [validationStatus, setValidationStatus] = useState(null); // Nouvel état pour le statut de validation
  const [userId, setUserId] = useState(null);
  const photoTypes = [
    { type: "face", label: "Photo de face" },
    { type: "droite", label: "Photo côté droit" },
    { type: "gauche", label: "Photo côté gauche" },
    { type: "plaque", label: "Photo arrière + plaque" },
    { type: "compteur", label: "Photo compteur" },
  ];
  const navigate = useNavigate();

  useEffect(() => {
    const storedUserId = localStorage.getItem("userId");
    if (storedUserId) {
      setUserId(storedUserId);
    } else {
      setMessage("ID utilisateur non trouvé, veuillez vous reconnecter.");
    }
  }, []);

  const handlePhotoUpload = async (type) => {
    if (!userId) {
      setMessage("Veuillez vous reconnecter pour continuer.");
      return;
    }
  
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/*";
    fileInput.onchange = async (event) => {
      const file = event.target.files[0];
      if (file) {
        try {
          const response = await detectVehiclePhoto(file, userId, type);
          console.log("Réponse du serveur :", response); // Ajout de console.log pour la réponse du serveur
          setMessage("Photo téléchargée avec succès !");
          setValidationStatus(response.validation_status);
        } catch (error) {
          setMessage(`Erreur : ${error.response?.data?.error || "Erreur lors du téléchargement de la photo"}`);
          console.error("Erreur lors de la requête de détection", error.response?.data);
          setValidationStatus(null);
        }
      }
    };
    fileInput.click();
  };
  

  return (
    <div className="take-photo-container">
      <h2>Prise de Photos</h2>
      <p>Sélectionnez le type de photo que vous souhaitez capturer :</p>
      {photoTypes.map((photo) => (
        <button
          key={photo.type}
          onClick={() => handlePhotoUpload(photo.type)}
          className="photo-button"
        >
          {photo.label}
        </button>
      ))}
      {message && <p className="upload-message">{message}</p>}
      {validationStatus && (
        <p className="validation-status">Statut de validation : {validationStatus}</p>
      )}

      {/* Boutons de navigation */}
      <div className="navigation-buttons">
        <button className="switch-button" onClick={() => navigate("/results")}>
          Voir les résultats
        </button>
      </div>
    </div>
  );
};

export default TakePhoto;