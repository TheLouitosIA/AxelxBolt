// src/components/Navbar.js
import React from "react";
import { Link, useNavigate } from "react-router-dom";

const Navbar = ({ setToken }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("userId");
    setToken(null);
    navigate("/");
  };

  return (
    <nav className="navbar">
      <Link to="/take-photo">Prise de Photos</Link>
      <Link to="/results">Historique des Résultats</Link>
      <Link to="/account">Mon Compte</Link>
      <button onClick={handleLogout} className="logout-button">Déconnexion</button>
    </nav>
  );
};

export default Navbar;