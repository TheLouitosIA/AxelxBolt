// src/components/ResultsPage.js
import React, { useEffect, useState } from "react";
import { fetchPhotosByUser } from "./API";
import { useNavigate } from "react-router-dom";
import "../css/ResultsPage.css";

const ResultsPage = () => {
  const [photos, setPhotos] = useState([]);
  const [months, setMonths] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [filteredPhotos, setFilteredPhotos] = useState([]);
  const [userId] = useState(localStorage.getItem("userId"));
  const navigate = useNavigate();

  useEffect(() => {
    const fetchPhotos = async () => {
      try {
        const photosData = await fetchPhotosByUser(userId);
        setPhotos(photosData);

        // Extraire les mois uniques
        const uniqueMonths = Array.from(new Set(
          photosData.map(photo => new Date(photo.date_prise).toLocaleString("fr-FR", { month: "long", year: "numeric" }))
        ));
        setMonths(uniqueMonths);
      } catch (error) {
        console.error("Erreur lors de la récupération des photos:", error);
      }
    };
    
    fetchPhotos();
  }, [userId]);

  // Filtrer les photos par mois sélectionné
  useEffect(() => {
    if (selectedMonth) {
      const filtered = photos.filter(photo => 
        new Date(photo.date_prise).toLocaleString("fr-FR", { month: "long", year: "numeric" }) === selectedMonth
      );
      setFilteredPhotos(filtered);
    }
  }, [selectedMonth, photos]);

  return (
    <div className="results-page">
      <h2>Historique des validations par mois</h2>

      <div className="months-list">
        {months.map((month, index) => (
          <button
            key={index}
            onClick={() => setSelectedMonth(month)}
            className="month-button"
          >
            {month}
          </button>
        ))}
      </div>

      {selectedMonth && (
        <div className="month-details">
          <h3>Détails pour le mois de {selectedMonth}</h3>
          {filteredPhotos.length > 0 ? (
            filteredPhotos.map((photo, index) => (
              <div key={index} className="photo-detail">
                <p>Type de photo : {photo.type_photo}</p>
                <p>Date prise : {new Date(photo.date_prise).toLocaleDateString("fr-FR")}</p>
                <p>Statut de validation : {photo.statut_validation}</p>
              </div>
            ))
          ) : (
            <p>Aucune photo disponible pour ce mois.</p>
          )}
        </div>
      )}

      {/* Bouton Retour */}
      <button className="back-button" onClick={() => navigate("/take-photo")}>
        Retour à la prise de photos
      </button>
    </div>
  );
};

export default ResultsPage;