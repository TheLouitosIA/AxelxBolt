// src/Auth.js
import React, { useState } from "react";
import Login from "./components/Login";
import Register from "./components/Register";
import './css/auth.css';

const Auth = ({ setToken }) => {
  const [formToShow, setFormToShow] = useState("");

  const goToLogin = () => setFormToShow("login");
  const goToRegister = () => setFormToShow("register");

  return (
    <div className="auth-container">
      <h1>Bienvenue</h1>
      {!formToShow && (
        <div className="auth-buttons">
          <button className="auth-button" onClick={goToLogin}>Connexion</button>
          <button className="auth-button" onClick={goToRegister}>Inscription</button>
        </div>
      )}
      {formToShow === "login" && <Login setToken={setToken} goToRegister={goToRegister} />}
      {formToShow === "register" && <Register goToLogin={goToLogin} />}
    </div>
  );
};

export default Auth;