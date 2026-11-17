import React, { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, practicePath, reasonLabel, statusLabel } from "./api.js";

const formatDate = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });
const categories = {
  pronunciation: "Pronunciación", grammar: "Gramática", vocabulary: "Vocabulario",
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
    const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
    api(`/history${query}`, "HistoryPage", { signal })
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
    more: page?.next_cursor && <button className="secondary" disabled={loading}
      onClick={() => load(page.next_cursor)}>Cargar más sesiones</button>,
  };
}

function labelFor(catalog, topicId) {
  return catalog.topics.find((topic) => topic.id === topicId)?.label_es ?? topicId;
}

export function History({ catalog }) {
  const { page, error, more, loading } = useHistory();
  return (
    <section className="panel">
      <div className="heading"><h1>Historial</h1><Link to="/comparar">Comparar sesiones</Link></div>
      {error && <p className="notice error" role="alert">{error}</p>}
      {!page && loading && <p role="status">Cargando sesiones…</p>}
      {page?.items.length === 0 && <p>Aún no hay sesiones. <Link to="/practica">Inicia una práctica</Link>.</p>}
      {page?.items.length > 0 && (
        <ul className="session-list">
          {page.items.map((item) => (
            <li key={item.id}>
              <Link to={`/sesiones/${item.id}`}>
                <strong>{labelFor(catalog, item.topic_id)} · {item.level}</strong>
                <time dateTime={item.date}>{formatDate.format(new Date(item.date))}</time>
              </Link>
              <span>{statusLabel[item.status]}{item.audio_availability === "available" ? " · Audio disponible" : ""}</span>
            </li>
          ))}
        </ul>
      )}
      {more}
    </section>
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
        api(`${path}/report`, "Report", params), api(`${path}/anchor-attempts`, "AttemptList", params),
      ]) : [];
      if (!controller.signal.aborted) setDetail({ view, report: extras[0], attempts: extras[1]?.items ?? [] });
    }).catch((error) => { if (error.name !== "AbortError") setError(error.message); });
    return () => controller.abort();
  }, [id]);

  const { view, report, attempts } = detail ?? {};
  return (
    <section className="panel">
      <Link className="back" to="/sesiones">← Historial</Link>
      <h1>{view ? labelFor(catalog, view.topic_id) : "Sesión"}</h1>
      {error && <p className="notice error" role="alert">{error}</p>}
      {!view && !error && <p role="status">Cargando sesión…</p>}
      {view && <p className="muted">{view.level} · {statusLabel[view.status]} · {formatDate.format(new Date(view.created_at))}</p>}
      {view?.reason_code && <p>{reasonLabel[view.reason_code] ?? "La práctica se detuvo."}</p>}
      {report && (
        <>
          <h2>Informe simulado</h2>
          {report.limitations.map((limitation) => <p className="muted" key={limitation}>{limitation}</p>)}
          <div className="report-categories">
            {Object.entries(categories).map(([key, name]) => {
              const category = report.categories[key];
              return (
                <section key={key}>
                  <h3>{name}</h3>
                  {categoryText[category.status] && <p>{categoryText[category.status]}</p>}
                  {category.observations.map((item) => (
                    <div key={item.id}>
                      {item.student_quote && <blockquote lang="en">{item.student_quote}</blockquote>}
                      <p>{item.explanation_es}</p>
                    </div>
                  ))}
                </section>
              );
            })}
          </div>
          <h2>Audios de las frases ancla</h2>
          <ol className="recordings">
            {attempts.filter((item) => item.status === "valid").map((item, index) => {
              const phrase = view.anchor_set_version === catalog.anchor_set_version
                ? catalog.anchors.find((phrase) => phrase.id === item.phrase_id) : null;
              return (
                <li key={item.id}>
                  <strong lang={phrase ? "en" : "es"}>{phrase?.text_en ?? `Frase ${index + 1}`}</strong>
                  <div className="audio-pair">
                    <AudioPlayer label="Mi muestra sintética" url={`/api/v1/audio/${encodeURIComponent(item.audio_id)}`} />
                    {phrase && <AudioPlayer label="Referencia sintética" url={`/api/v1/references/${encodeURIComponent(phrase.reference_audio_id)}`} />}
                  </div>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </section>
  );
}

function countsText(counts) {
  return counts.evaluated_opportunities ? `${counts.detected_errors} de ${counts.evaluated_opportunities}`
    : "Sin evidencia evaluable";
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
    api(`/comparisons?${new URLSearchParams({ left: leftId, right: rightId })}`,
      "Comparison", { signal: controller.signal })
      .then(setComparison)
      .catch((error) => { if (error.name !== "AbortError") setError(error.message); });
    return () => controller.abort();
  }, [leftId, rightId]);
  const items = (page?.items ?? []).filter((item) => item.report_available);

  function options(selectedId) {
    return (
      <>
        <option value="">Selecciona una sesión</option>
        {selectedId && !items.some((item) => item.id === selectedId) && (
          <option value={selectedId}>Sesión seleccionada</option>
        )}
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {labelFor(catalog, item.topic_id)} · {item.level} · {formatDate.format(new Date(item.date))}
          </option>
        ))}
      </>
    );
  }

  return (
    <section className="panel">
      <h1>Comparación por sonido</h1>
      {(error || historyError) && <p className="notice error" role="alert">{error || historyError}</p>}
      {loading && !page && <p role="status">Cargando sesiones…</p>}
      {page && items.length < 2 && <p>Selecciona dos prácticas completadas para comparar.</p>}
      <form onSubmit={(event) => { event.preventDefault(); setQuery({ left, right }); }}>
        <div className="fields compare">
          <label>Sesión 1<select value={left} onChange={(event) => setLeft(event.target.value)}>{options(left)}</select></label>
          <label>Sesión 2<select value={right} onChange={(event) => setRight(event.target.value)}>{options(right)}</select></label>
        </div>
        <div className="actions"><button disabled={!left || !right || left === right}>Comparar</button>{more}</div>
      </form>
      {comparison && (
        <div className="comparison" aria-live="polite">
          <div className="table-scroll">
            <table>
              <caption>Errores detectados por oportunidades evaluadas</caption>
              <thead><tr><th scope="col">Sonido</th><th scope="col">Sesión 1</th><th scope="col">Sesión 2</th></tr></thead>
              <tbody>
                {comparison.sounds.map((row) => (
                  <tr key={row.sound}>
                    <th scope="row">/{row.sound}/</th>
                    <td>{countsText(row.left)}<small>{row.left.not_evaluated_opportunities} sin evaluar</small></td>
                    <td>{countsText(row.right)}<small>{row.right.not_evaluated_opportunities} sin evaluar</small></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {comparison.limitations.map((item) => <p className="muted" key={item}>{item}</p>)}
        </div>
      )}
    </section>
  );
}
