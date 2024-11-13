// src/components/Login.js
import React, { useState } from "react";
import { loginUser } from "./API";
import { useNavigate } from "react-router-dom";
import "../css/Login.css";

const Login = ({ setToken }) => {
  const [credentials, setCredentials] = useState({ email: "", password: "" });
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setCredentials({ ...credentials, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = await loginUser(credentials);
      if (data.access_token) {
        setToken(data.access_token);
        localStorage.setItem("userId", data.user.id); // Stocke l'ID utilisateur
        setMessage("Connexion réussie !");
        navigate("/take-photo");
      } else {
        setMessage("Erreur de connexion : Token non reçu");
      }
    } catch (error) {
      setMessage(error.response?.data?.detail || "Erreur de connexion");
    }
  };

  return (
    <div className="form-container">
      <h2>Connexion</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          name="email"
          placeholder="Email"
          onChange={handleChange}
          value={credentials.email}
          required
        />
        <input
          type="password"
          name="password"
          placeholder="Mot de passe"
          onChange={handleChange}
          value={credentials.password}
          required
        />
        <button type="submit" className="submit-button">Se connecter</button>
      </form>
      {message && <p>{message}</p>}
      <button className="switch-button" onClick={() => navigate("/register")}>S'inscrire</button>
    </div>
  );
};

export default Login;