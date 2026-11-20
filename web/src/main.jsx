import React, { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AudioLines, FlaskConical, History as HistoryIcon, MessageCircle, Scale } from "lucide-react";
import { api } from "./api.js";
import { Compare, History, Session } from "./History.jsx";
import Practice from "./Practice.jsx";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-600.css";
import "@fontsource/dm-sans/latin-700.css";
import "@fontsource/instrument-serif/latin-400.css";
import "@fontsource/instrument-serif/latin-400-italic.css";
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
  const location = useLocation();
  const pageName = location.pathname.startsWith("/sesiones/")
    ? "Informe de sesión" : location.pathname === "/sesiones" ? "Mis sesiones"
      : location.pathname === "/comparar" ? "Comparar sesiones" : "Nueva práctica";
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);
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
    <div className="app-layout">
      <a className="skip" href="#contenido">Saltar al contenido</a>
      <aside className="sidebar">
        <NavLink to="/practica" className="brand" aria-label="¡Habla! Inicio">
          <span className="brand-mark"><AudioLines size={25} strokeWidth={2} aria-hidden="true" /></span>
          ¡habla!
        </NavLink>
        <span className="nav-label">TU ESPACIO</span>
        <nav aria-label="Navegación principal">
          <NavLink to="/practica"><MessageCircle size={20} aria-hidden="true" /><span>Practicar</span></NavLink>
          <NavLink to="/sesiones"><HistoryIcon size={20} aria-hidden="true" /><span>Mis sesiones</span></NavLink>
          <NavLink to="/comparar"><Scale size={20} aria-hidden="true" /><span>Comparar</span></NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="simulation-card">
            <FlaskConical size={19} strokeWidth={1.7} aria-hidden="true" />
            <div><strong>Modo de prueba</strong><p>Audio y evaluación simulados para explorar la experiencia.</p></div>
          </div>
          <div className="workspace-profile"><span className="avatar">H</span>
            <span><strong>Espacio del equipo</strong><small>Usuario base · Local</small></span>
          </div>
        </div>
      </aside>
      <div className="app-content">
        <header className="topbar">
          <div className="breadcrumb"><span>Mi espacio</span><span aria-hidden="true">/</span><strong>{pageName}</strong></div>
          <div className="topbar-status">
            <span className="mobile-simulation"><FlaskConical size={14} aria-hidden="true" />Modo de prueba</span>
            <span className={"connection-status " + (data && !error ? "online" : "")}>
              <span aria-hidden="true" />{error ? "Sin conexión" : data ? "Conectado" : "Conectando"}
            </span>
          </div>
        </header>
        <main id="contenido" tabIndex={-1}>
          {error && (
            <section className="panel connection-error">
              <span className="empty-icon"><AudioLines size={30} aria-hidden="true" /></span>
              <h1>Conectemos tu espacio</h1>
              <p className="muted">Inicia la API local de HABLA para entrar a tus prácticas.</p>
              <p className="notice error" role="alert">{error}</p>
              <button onClick={() => setLoad((prior) => prior + 1)}>Volver a conectar</button>
            </section>
          )}
          {!data && !error && <p className="loading-line" role="status"><span className="spinner" />Preparando tu espacio…</p>}
          {data && !error && (
            <>
              {scenarios[data.health.scenario] && <p className="notice demo-scenario">
                <FlaskConical size={18} aria-hidden="true" />Escenario de prueba · {scenarios[data.health.scenario]}
              </p>}
              <Routes>
                <Route path="/practica" element={<Practice catalog={data.catalog} />} />
                <Route path="/sesiones" element={<History catalog={data.catalog} />} />
                <Route path="/sesiones/:id" element={<Session catalog={data.catalog} />} />
                <Route path="/comparar" element={<Compare catalog={data.catalog} />} />
                <Route path="*" element={<Navigate to="/practica" replace />} />
              </Routes>
            </>
          )}
          <footer className="app-footer"><span>¡Habla! · Un espacio para tu inglés.</span><span>Hecho para conversar.</span></footer>
        </main>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>,
);
