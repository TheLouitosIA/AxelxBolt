// src/ProtectedRoute.js
import React, { useEffect, useState } from "react";
import { getProtectedData } from "./components/API";

const ProtectedRoute = ({ token }) => {
  const [data, setData] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await getProtectedData(token);
        setData(result.message);
      } catch (error) {
        setData("Erreur lors de l'accès aux données protégées");
      }
    };
    if (token) fetchData();
  }, [token]);

  return (
    <div>
      <h2>Données protégées</h2>
      <p>{data}</p>
    </div>
  );
};

export default ProtectedRoute;