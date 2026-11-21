import React, { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { AudioLines, BookOpen, CalendarDays, Check, CircleHelp, FileText, History as HistoryIcon, Plus, Scale, Search, TextQuote } from "lucide-react";
import { api, practicePath, reasonLabel, statusLabel } from "./api.js";
import { EmptyState, PageHeading, StatusBadge, TopicIcon } from "./ui.jsx";

const formatDate = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });
const categories = {
  pronunciation: { name: "Pronunciación", Icon: AudioLines, color: "mint" },
  grammar: { name: "Gramática", Icon: TextQuote, color: "lavender" },
  vocabulary: { name: "Vocabulario", Icon: BookOpen, color: "peach" },
};
const categoryText = {
  no_supported_observations: "Sin observaciones respaldadas.", not_evaluated: "No se pudo evaluar.",
};

function useHistory() {
  const [page, setPage] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function load(cursor, signal) {
    setLoading(true);
    setError("");
    const query = cursor ? "?cursor=" + encodeURIComponent(cursor) : "";
    api("/history" + query, "HistoryPage", { signal })
      .then((next) => setPage((prior) => ({
        ...next, items: cursor ? [...prior.items, ...next.items] : next.items,
      })))
      .catch((error) => { if (error.name !== "AbortError") setError(error.message); })
      .finally(() => { if (!signal?.aborted) setLoading(false); });
  }

  useEffect(() => {
    const controller = new AbortController();
    load(null, controller.signal);
    return () => controller.abort();
  }, []);

  return {
    page, error, loading,
    more: page?.next_cursor && <button type="button" className="secondary" disabled={loading}
      onClick={() => load(page.next_cursor)}>Cargar más sesiones</button>,
  };
}

function labelFor(catalog, topicId) {
  return catalog.topics.find((topic) => topic.id === topicId)?.label_es ?? topicId;
}

export function History({ catalog }) {
  const { page, error, more, loading } = useHistory();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const items = (page?.items ?? []).filter((item) =>
    (filter === "all" || item.status === filter) &&
    (labelFor(catalog, item.topic_id) + " " + item.level).toLocaleLowerCase("es").includes(search.trim().toLocaleLowerCase("es")));

  return (
    <div className="history-page">
      <PageHeading title="Tus conversaciones" description="Vuelve a tus sesiones. Escúchate con otra perspectiva.">
        <Link className="button" to="/practica"><Plus size={17} aria-hidden="true" />Nueva práctica</Link>
      </PageHeading>
      {error && <p className="notice error" role="alert">{error}</p>}
      <section className="panel history-panel" aria-label="Historial de prácticas">
        <div className="history-toolbar">
          <div className="filter-tabs" role="group" aria-label="Filtrar sesiones">
            {[["all", "Todas"], ["completed", "Completadas"], ["incomplete", "Incompletas"]].map(([value, label]) =>
              <button key={value} type="button" aria-pressed={filter === value}
                onClick={() => setFilter(value)}>{label}</button>)}
          </div>
          <label className="search-input"><Search size={17} aria-hidden="true" />
            <span className="sr-only">Buscar por tema o nivel</span>
            <input type="search" value={search} placeholder="Buscar tema o nivel"
              onChange={(event) => setSearch(event.target.value)} />
          </label>
        </div>
        {!page && loading && <p className="loading-line" role="status"><span className="spinner" />Cargando sesiones…</p>}
        {page?.items.length === 0 && <EmptyState Icon={HistoryIcon} title="Tu primera conversación te espera">
          <p>Cada práctica y su informe tendrán un lugar aquí.</p>
          <Link className="button" to="/practica">Explorar los temas</Link>
        </EmptyState>}
        {page && page.items.length > 0 && items.length === 0 && <EmptyState Icon={Search} title="Busquemos otra conversación">
          <p>Prueba con otro tema, nivel o estado.</p>
          <button className="secondary" onClick={() => { setFilter("all"); setSearch(""); }}>Ver todas las sesiones</button>
        </EmptyState>}
        {items.length > 0 && <ul className="session-list">
          {items.map((item) => <li key={item.id}>
            <TopicIcon topicId={item.topic_id} size={23} />
            <div className="session-title">
              <Link to={"/sesiones/" + item.id}>{labelFor(catalog, item.topic_id)}<span className="level-tag">{item.level}</span></Link>
              <time dateTime={item.date}><CalendarDays size={13} aria-hidden="true" />{formatDate.format(new Date(item.date))}</time>
            </div>
            <div className="session-status"><StatusBadge status={item.status} label={statusLabel[item.status]} />
              {item.audio_availability === "available" && <small><AudioLines size={13} aria-hidden="true" />Audios disponibles</small>}
            </div>
            <Link className="session-open" to={"/sesiones/" + item.id}><FileText size={16} aria-hidden="true" />
              {item.report_available ? "Ver informe" : "Ver sesión"}</Link>
          </li>)}
        </ul>}
        {more && <div className="pagination">{more}</div>}
      </section>
      <div className="history-note"><Scale size={19} aria-hidden="true" />
        <p>¿Tienes dos sesiones completadas? <Link to="/comparar">Compara sus resultados por sonido.</Link></p>
      </div>
    </div>
  );
}

function AudioPlayer({ label, url }) {
  const [unavailable, setUnavailable] = useState(false);
  return (
    <div className="audio-player">
      <span>{label}</span>
      {unavailable ? <span className="muted">Audio no disponible.</span>
        : <audio aria-label={label} controls preload="none" src={url} onError={() => setUnavailable(true)} />}
    </div>
  );
}

export function Session({ catalog }) {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const params = { signal: controller.signal };
    setDetail(null);
    setError("");
    const path = practicePath(id);
    api(path, "Practice", params).then(async (view) => {
      const extras = view.status === "completed" ? await Promise.all([
        api(path + "/report", "Report", params), api(path + "/anchor-attempts", "AttemptList", params),
      ]) : [];
      if (!controller.signal.aborted) setDetail({ view, report: extras[0], attempts: extras[1]?.items ?? [] });
    }).catch((error) => { if (error.name !== "AbortError") setError(error.message); });
    return () => controller.abort();
  }, [id]);

  const { view, report, attempts } = detail ?? {};
  return (
    <div className="session-page">
      <Link className="back" to="/sesiones">Volver a mis sesiones</Link>
      <PageHeading title={view ? labelFor(catalog, view.topic_id) : "Tu sesión"}
        description={view ? view.level + " · " + formatDate.format(new Date(view.created_at)) : null}>
        {view && <StatusBadge status={view.status} label={statusLabel[view.status]} />}
      </PageHeading>
      {error && <p className="notice error" role="alert">{error}</p>}
      {!view && !error && <p className="loading-line" role="status"><span className="spinner" />Cargando sesión…</p>}
      {view && !report && <section className="panel">
        <EmptyState Icon={HistoryIcon} title={view.status === "incomplete" ? "Puedes volver a empezar" : "Esta práctica está en curso"}>
          <p>{reasonLabel[view.reason_code] ?? "El informe estará disponible al completar la práctica."}</p>
          <Link className="button" to="/practica">Ir a practicar</Link>
        </EmptyState>
      </section>}
      {report && <>
        <section className="report-banner">
          <span className="report-mark"><FileText size={28} strokeWidth={1.4} aria-hidden="true" /></span>
          <div><h2>Una mirada a tu conversación</h2><p>Observaciones de pronunciación, gramática y vocabulario.</p></div>
          <span className="report-type">Informe simulado</span>
        </section>
        <div className="report-categories">
          {Object.entries(categories).map(([key, { name, Icon, color }]) => {
            const category = report.categories[key];
            return <section className="panel category-card" key={key}>
              <span className={"topic-icon " + color}><Icon size={22} strokeWidth={1.7} aria-hidden="true" /></span>
              <h2>{name}</h2>
              {categoryText[category.status] && <p className="category-empty">
                {category.status === "not_evaluated" ? <CircleHelp size={16} aria-hidden="true" /> : <Check size={16} aria-hidden="true" />}
                {categoryText[category.status]}
              </p>}
              {category.observations.map((item) => <div className="observation" key={item.id}>
                {item.student_quote && <blockquote lang="en">“{item.student_quote}”</blockquote>}
                <p>{item.explanation_es}</p>
                {item.audio_id && <a className="listen-link" href={"#audio-" + item.audio_id}>
                  <AudioLines size={15} aria-hidden="true" />Escuchar frase</a>}
              </div>)}
            </section>;
          })}
        </div>
        <section className="report-limitations"><h3>Sobre esta evaluación</h3>
          {report.limitations.map((limitation) => <p key={limitation}>{limitation}</p>)}
        </section>
        <section className="panel recordings-panel">
          <div className="section-heading"><div><h2>Vuelve a escucharte</h2><p>Tus cinco frases, junto a sus referencias de prueba.</p></div><AudioLines size={23} aria-hidden="true" /></div>
          <ol className="recordings">
            {attempts.filter((item) => item.status === "valid").map((item, index) => {
              const phrase = view.anchor_set_version === catalog.anchor_set_version
                ? catalog.anchors.find((phrase) => phrase.id === item.phrase_id) : null;
              return <li key={item.id} id={"audio-" + item.audio_id}>
                <span className="recording-number">{index + 1}</span>
                <div className="recording-content">
                  <strong lang={phrase ? "en" : "es"}>{phrase?.text_en ?? "Frase " + (index + 1)}</strong>
                  <div className="audio-pair">
                    <AudioPlayer label="Mi muestra sintética" url={"/api/v1/audio/" + encodeURIComponent(item.audio_id)} />
                    {phrase && <AudioPlayer label="Referencia sintética" url={"/api/v1/references/" + encodeURIComponent(phrase.reference_audio_id)} />}
                  </div>
                </div>
              </li>;
            })}
          </ol>
        </section>
      </>}
    </div>
  );
}

function SoundCount({ counts }) {
  return <div className="sound-count">
    <span>{counts.evaluated_opportunities ? <><strong>{counts.detected_errors}</strong> de {counts.evaluated_opportunities} oportunidades</> : "Sin evidencia evaluable"}</span>
    {counts.evaluated_opportunities > 0 && <div className="count-track" aria-hidden="true">
      <span style={{ width: (counts.detected_errors * 100 / counts.evaluated_opportunities) + "%" }} />
    </div>}
    <small>{counts.not_evaluated_opportunities} sin evaluar</small>
  </div>;
}

export function Compare({ catalog }) {
  const { page, error: historyError, more, loading } = useHistory();
  const [query, setQuery] = useSearchParams();
  const [left, setLeft] = useState(query.get("left") ?? "");
  const [right, setRight] = useState(query.get("right") ?? "");
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState("");
  const leftId = query.get("left");
  const rightId = query.get("right");
  useEffect(() => {
    setComparison(null);
    setError("");
    setLeft(leftId ?? "");
    setRight(rightId ?? "");
    if (!leftId || !rightId) return;
    const controller = new AbortController();
    api("/comparisons?" + new URLSearchParams({ left: leftId, right: rightId }),
      "Comparison", { signal: controller.signal })
      .then(setComparison)
      .catch((error) => { if (error.name !== "AbortError") setError(error.message); });
    return () => controller.abort();
  }, [leftId, rightId]);
  const items = (page?.items ?? []).filter((item) => item.report_available);

  function options(selectedId) {
    return <>
      <option value="">Selecciona una sesión</option>
      {selectedId && !items.some((item) => item.id === selectedId) && <option value={selectedId}>Sesión seleccionada</option>}
      {items.map((item) => <option key={item.id} value={item.id}>
        {labelFor(catalog, item.topic_id)} · {item.level} · {formatDate.format(new Date(item.date))}
      </option>)}
    </>;
  }

  return (
    <div className="compare-page">
      <PageHeading title="Escucha lo que cambia" description="Compara los mismos sonidos en dos sesiones compatibles." />
      {(error || historyError) && <p className="notice error" role="alert">{error || historyError}</p>}
      <section className="panel compare-selection">
        <form onSubmit={(event) => { event.preventDefault(); setQuery({ left, right }); }}>
          <div className="compare-fields">
            <label><span className="select-label"><span className="comparison-dot left" />Sesión 1</span>
              <select value={left} onChange={(event) => setLeft(event.target.value)}>{options(left)}</select></label>
            <span className="compare-connector" aria-hidden="true"><Scale size={22} strokeWidth={1.5} /></span>
            <label><span className="select-label"><span className="comparison-dot right" />Sesión 2</span>
              <select value={right} onChange={(event) => setRight(event.target.value)}>{options(right)}</select></label>
          </div>
          <div className="compare-actions"><p>Se comparan las cinco frases con las mismas versiones de evaluación.</p>
            <button disabled={!left || !right || left === right}><Scale size={17} aria-hidden="true" />Comparar sesiones</button>
          </div>
        </form>
        {more && <div className="pagination">{more}</div>}
      </section>
      {loading && !page && <p className="loading-line" role="status"><span className="spinner" />Cargando sesiones…</p>}
      {!comparison && !error && !loading && <section className="comparison-placeholder">
        <EmptyState Icon={AudioLines} title={items.length < 2 ? "Cada conversación es un punto de partida" : "Dos conversaciones, una nueva perspectiva"}>
          <p>{items.length < 2 ? "Completa dos prácticas para comparar sus resultados por sonido." : "Selecciona dos sesiones y explora sus oportunidades evaluadas."}</p>
          {items.length < 2 && <Link className="button secondary" to="/practica">Iniciar una práctica</Link>}
        </EmptyState>
      </section>}
      {comparison && <section className="panel comparison" aria-live="polite">
        <div className="table-scroll">
          <table>
            <caption><h2>Sonido a sonido</h2><p>Errores detectados por oportunidades evaluadas</p></caption>
            <thead><tr><th scope="col">Sonido</th><th scope="col"><span className="comparison-dot left" />Sesión 1</th><th scope="col"><span className="comparison-dot right" />Sesión 2</th></tr></thead>
            <tbody>{comparison.sounds.map((row) => <tr key={row.sound}>
              <th scope="row"><span className="phoneme">/{row.sound}/</span></th>
              <td><SoundCount counts={row.left} /></td><td><SoundCount counts={row.right} /></td>
            </tr>)}</tbody>
          </table>
        </div>
        <div className="comparison-limitations">{comparison.limitations.map((item) => <p key={item}>{item}</p>)}</div>
      </section>}
    </div>
  );
}
