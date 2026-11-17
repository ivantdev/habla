import React, { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api.js";
import { Compare, History, Session } from "./History.jsx";
import Practice from "./Practice.jsx";
import "./style.css";

const scenarios = {
  anchor_invalid: "Muestra no evaluable",
  anchor_fail_once: "Fallo recuperable del validador",
  asr_fail_once: "Fallo recuperable de reconocimiento",
  tutor_fail_once: "Fallo recuperable del tutor",
  tts_fail_once: "Fallo recuperable de síntesis",
  report_fail_once: "Fallo recuperable del informe",
  report_unavailable: "Fallo persistente del informe",
  commit_fail_once: "Fallo al publicar",
  slow_evaluation: "Evaluación lenta",
};

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [load, setLoad] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal };
    setError("");
    Promise.all([api("/health", null, options), api("/catalog", "Catalog", options)])
      .then(([health, catalog]) => setData({ health, catalog }))
      .catch((error) => { if (error.name !== "AbortError") setError(error.message); });
    return () => controller.abort();
  }, [load]);
  return (
    <>
      <a className="skip" href="#contenido">Saltar al contenido</a>
      <header>
        <div className="topbar">
          <NavLink to="/practica" className="brand">¡Habla!</NavLink>
          <nav aria-label="Navegación principal">
            <NavLink to="/practica">Práctica</NavLink>
            <NavLink to="/sesiones">Historial</NavLink>
            <NavLink to="/comparar">Comparar</NavLink>
          </nav>
        </div>
      </header>
      <main id="contenido">
        {error && (
          <section className="panel">
            <h1>API local</h1>
            <p className="notice error" role="alert">{error}</p>
            <button onClick={() => setLoad((prior) => prior + 1)}>Volver a conectar</button>
          </section>
        )}
        {!data && !error && <p role="status">Conectando con la API local…</p>}
        {data && (
          <>
            <p className="mode">
              <span className="mode-dot" aria-hidden="true" />
              {data.health.mode === "demo" ? "Demo con datos simulados" : "Simulación local"} · Sin micrófono
              {scenarios[data.health.scenario] && ` · ${scenarios[data.health.scenario]}`}
            </p>
            <Routes>
              <Route path="/practica" element={<Practice catalog={data.catalog} />} />
              <Route path="/sesiones" element={<History catalog={data.catalog} />} />
              <Route path="/sesiones/:id" element={<Session catalog={data.catalog} />} />
              <Route path="/comparar" element={<Compare catalog={data.catalog} />} />
              <Route path="*" element={<Navigate to="/practica" replace />} />
            </Routes>
          </>
        )}
      </main>
    </>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>,
);
