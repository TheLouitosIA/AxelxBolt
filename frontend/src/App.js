// src/App.js
import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Auth from "./Auth";
import TakePhoto from "./components/TakePhoto";
import ResultsPage from "./components/Results";
import AccountPage from "./components/AccountPage";
import Navbar from "./components/Navbar";
import "./css/app.css";

function App() {
  // État pour le token d'authentification
  const [token, setToken] = useState(localStorage.getItem("token"));

  return (
    <Router>
      <div className="App">
        {/* Affiche la barre de navigation seulement si l'utilisateur est connecté */}
        {token && <Navbar setToken={setToken} />}

        <Routes>
          {/* Route pour la page de connexion / inscription */}
          <Route path="/" element={!token ? <Auth setToken={setToken} /> : <Navigate to="/take-photo" />} />
          
          {/* Route pour la prise de photos */}
          <Route path="/take-photo" element={token ? <TakePhoto /> : <Navigate to="/" />} />
          
          {/* Route pour l'historique des résultats */}
          <Route path="/results" element={token ? <ResultsPage /> : <Navigate to="/" />} />
          
          {/* Route pour la page "Mon Compte" */}
          <Route path="/account" element={token ? <AccountPage setToken={setToken} /> : <Navigate to="/" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;