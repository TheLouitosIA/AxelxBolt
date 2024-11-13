// src/components/AccountPage.js
import React, { useEffect, useState } from "react";
import { fetchUserInfo } from "./API";
import { useNavigate } from "react-router-dom";
import "../css/AccountPage.css";

const AccountPage = ({ setToken }) => {
  const [userInfo, setUserInfo] = useState(null);
  const [userId] = useState(localStorage.getItem("userId"));
  const navigate = useNavigate();

  useEffect(() => {
    const getUserInfo = async () => {
      try {
        const data = await fetchUserInfo(userId);
        setUserInfo(data);
      } catch (error) {
        console.error("Erreur lors de la récupération des informations utilisateur:", error);
      }
    };

    getUserInfo();
  }, [userId]);

  const handleLogout = () => {
    // Supprime le token et l'ID utilisateur de la session
    localStorage.removeItem("userId");
    setToken(null); // Réinitialise le token pour déconnecter l'utilisateur
    navigate("/"); // Redirige vers la page de connexion
  };

  return (
    <div className="account-page">
      <h2>Mon Compte</h2>
      {userInfo ? (
        <div className="user-info">
          <p><strong>Nom :</strong> {userInfo.nom}</p>
          <p><strong>Prénom :</strong> {userInfo.prenom}</p>
          <p><strong>Email :</strong> {userInfo.email}</p>
          <p><strong>Téléphone :</strong> {userInfo.telephone}</p>
          <p><strong>Marque de voiture :</strong> {userInfo.marque_voiture}</p>
          <p><strong>Plaque d'immatriculation :</strong> {userInfo.plaque_immatriculation}</p>
        </div>
      ) : (
        <p>Chargement des informations utilisateur...</p>
      )}
      <button className="logout-button" onClick={handleLogout}>Déconnexion</button>
    </div>
  );
};

export default AccountPage;