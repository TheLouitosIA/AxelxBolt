// src/components/Register.js
import React, { useState } from "react";
import { registerUser } from "./API";

const Register = ({ goToLogin }) => {
  const [formData, setFormData] = useState({
    nom: "",
    prenom: "",
    email: "",
    telephone: "",
    marque_voiture: "",
    plaque_immatriculation: "",
    password: "",
  });
  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = await registerUser(formData);
      if (data.message) {
        setMessage(data.message || "Inscription réussie !");
      } else {
        setMessage("Erreur lors de l'inscription : réponse inattendue.");
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Erreur lors de l'inscription";
      setMessage(errorMsg);
    }
  };

  return (
    <div className="form-container">
      <h2>Inscription</h2>
      <form onSubmit={handleSubmit}>
        <input type="text" name="nom" placeholder="Nom" onChange={handleChange} value={formData.nom} required />
        <input type="text" name="prenom" placeholder="Prénom" onChange={handleChange} value={formData.prenom} required />
        <input type="email" name="email" placeholder="Email" onChange={handleChange} value={formData.email} required />
        <input type="text" name="telephone" placeholder="Téléphone" onChange={handleChange} value={formData.telephone} required />
        <input type="text" name="marque_voiture" placeholder="Marque de voiture" onChange={handleChange} value={formData.marque_voiture} required />
        <input type="text" name="plaque_immatriculation" placeholder="Plaque d'immatriculation" onChange={handleChange} value={formData.plaque_immatriculation} required />
        <input type="password" name="password" placeholder="Mot de passe" onChange={handleChange} value={formData.password} required />
        <button type="submit" className="submit-button">S'inscrire</button>
      </form>
      {message && <p>{message}</p>}
      <button className="switch-button" onClick={goToLogin}>Se connecter</button>
    </div>
  );
};

export default Register;