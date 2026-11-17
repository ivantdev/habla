import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, practicePath, reasonLabel, statusLabel } from "./api.js";
import { conforms } from "./contract.js";
import { FixtureStream, sampleWave } from "./fixture-stream.js";

const stages = {
  acoustic: "Evaluando muestras",
  linguistic: "Revisando la transcripción",
  report: "Preparando el informe",
  cleanup: "Limpiando el audio temporal",
};

function RemainingTime({ endsAt }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const update = () => setSeconds(Math.max(0, Math.ceil((Date.parse(endsAt) - Date.now()) / 1000)));
    update();
    const timer = setInterval(update, 250);
    return () => clearInterval(timer);
  }, [endsAt]);
  const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
  return <time className="timer" aria-label="Tiempo restante">{minutes}:{String(seconds % 60).padStart(2, "0")}</time>;
}

export default function Practice({ catalog }) {
  const [selection, setSelection] = useState({ level: "A2", topic_id: "restaurant", duration_seconds: 300 });
  const [view, setView] = useState(null);
  const [turns, setTurns] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [incident, setIncident] = useState(null);
  const [stage, setStage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const connection = useRef({ mounted: false, view: null, stream: null, audio: null });

  useEffect(() => {
    const current = connection.current;
    current.mounted = true;
    return () => {
      current.mounted = false;
      current.stream?.close();
      current.audio?.close().catch(() => {});
    };
  }, []);

  function apply(next) {
    const current = connection.current;
    if (!current.mounted || current.view?.id !== next.id || current.view.state_version > next.state_version) return;
    current.view = next;
    setView(next);
  }

  async function refresh(id) {
    if (connection.current.view?.id === id) apply(await api(practicePath(id), "Practice"));
  }

  async function refreshAttempts(id) {
    const list = await api(`${practicePath(id)}/anchor-attempts`, "AttemptList");
    if (connection.current.mounted && connection.current.view?.id === id) {
      setAttempts((prior) => {
        const known = new Map(prior.map((item) => [item.id, item]));
        for (const item of list.items) {
          if (!known.has(item.id) || known.get(item.id).status === "pending") known.set(item.id, item);
        }
        return [...known.values()];
      });
    }
  }

  function streamEvent(id, event) {
    if (connection.current.view?.id !== id || !connection.current.mounted) return;
    const { type, payload } = event;
    if (type === "practice.state_changed") {
      if (payload.status !== "recoverable_error") setIncident(null);
      refresh(id).catch((error) => setError(error.message));
    } else if (type === "transcript.updated" && conforms("Turn", payload)) {
      setTurns((prior) => {
        const updated = prior.filter((turn) => turn.id !== payload.id);
        return [...updated, payload].sort((left, right) => left.sequence - right.sequence);
      });
    } else if (type === "anchor.validated") {
      refreshAttempts(id).catch((error) => setError(error.message));
    } else if (type === "practice.error") {
      setIncident(payload.retryable ? payload : null);
    } else if (type === "processing.updated") {
      setStage(payload.stage);
    }
  }

  async function action(work) {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (error) {
      if (connection.current.mounted) setError(error.message);
    } finally {
      if (connection.current.mounted) setBusy(false);
    }
  }

  function begin(event) {
    event.preventDefault();
    action(async () => {
      const current = connection.current;
      if (!current.audio && typeof AudioContext === "function") current.audio = new AudioContext();
      current.audio?.resume().catch(() => {});
      const created = await api("/practices", "Practice", {
        method: "POST", body: { ...selection, catalog_version: catalog.version },
      });
      if (!current.mounted) {
        await api(`${practicePath(created.id)}/cancel`, "Operation", {
          method: "POST", body: { state_version: created.state_version },
        });
        return;
      }
      current.view = created;
      setTurns([]);
      setAttempts([]);
      setIncident(null);
      setStage(null);
      apply(created);
      try {
        const stream = new FixtureStream(
          created.id, current.audio, (event) => streamEvent(created.id, event),
          () => {
            if (current.mounted && current.view?.id === created.id) {
              refresh(created.id).catch((error) => setError(error.message));
            }
          },
        );
        current.stream = stream;
        await stream.ready;
        if (current.mounted) {
          apply(await api(`${practicePath(created.id)}/start`, "Practice", {
            method: "POST", body: { state_version: created.state_version },
          }));
        }
      } catch (error) {
        current.stream?.close();
        await api(`${practicePath(created.id)}/cancel`, "Operation", {
          method: "POST", body: { state_version: current.view.state_version },
        }).catch(() => {});
        await refresh(created.id).catch(() => {});
        throw error;
      }
    });
  }

  function command(name, fields = {}) {
    action(async () => {
      const current = connection.current.view;
      await api(`${practicePath(current.id)}/${name}`, "Operation", {
        method: "POST", body: { state_version: current.state_version, ...fields },
      });
      await refresh(current.id);
    });
  }

  function sendAnchor(phraseId) {
    action(async () => {
      const current = connection.current.view;
      const form = new FormData();
      form.set("phrase_id", phraseId);
      form.set("state_version", current.state_version);
      form.set("audio", sampleWave(), "muestra.wav");
      await api(`${practicePath(current.id)}/anchor-attempts`, "AnchorAttempt", { method: "POST", body: form });
      await refreshAttempts(current.id);
      await refresh(current.id);
    });
  }

  const phase = view?.status;
  const finished = phase === "completed" || phase === "incomplete";
  const currentAnchor = catalog.anchors.find((phrase) =>
    !attempts.some((item) => item.phrase_id === phrase.id && item.status === "valid"));
  const lastAttempt = attempts.filter((attempt) => attempt.phrase_id === currentAnchor?.id).at(-1);

  return (
    <section className="panel">
      <div className="heading">
        <h1>Práctica de inglés</h1>
        {phase === "conversation" && <RemainingTime endsAt={view.conversation_ends_at} />}
      </div>
      {error && <p className="notice error" role="alert">{error}</p>}
      {(!view || finished) && (
        <>
          {finished && (
            <div className="notice" role="status">
              {phase === "completed" ? <Link to={`/sesiones/${view.id}`}>Abrir informe simulado</Link>
                : (reasonLabel[view.reason_code] ?? "La práctica quedó incompleta.")}
            </div>
          )}
          <form onSubmit={begin}>
            <div className="fields">
              <label>Nivel<select value={selection.level} onChange={(event) => setSelection({ ...selection, level: event.target.value })}>
                {catalog.levels.map((level) => <option key={level}>{level}</option>)}
              </select></label>
              <label>Tema<select value={selection.topic_id} onChange={(event) => setSelection({ ...selection, topic_id: event.target.value })}>
                {catalog.topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.label_es}</option>)}
              </select></label>
              <label>Duración<select value={selection.duration_seconds} onChange={(event) => setSelection({
                ...selection, duration_seconds: Number(event.target.value),
              })}>
                <option value={300}>5 minutos</option><option value={600}>10 minutos</option>
              </select></label>
            </div>
            <button disabled={busy}>{busy ? "Abriendo canal…" : "Iniciar práctica simulada"}</button>
          </form>
        </>
      )}
      {phase === "ready" && <p role="status">Abriendo el canal de práctica…</p>}
      {phase === "conversation" && (
        <>
          <h2>Conversación</h2>
          <div className="transcript" role="log" aria-label="Transcripción simulada" aria-live="polite">
            {turns.length === 0 && <p className="muted">Envía un turno de prueba para ver la transcripción.</p>}
            {turns.map((turn) => (
              <p key={turn.id}><strong>{turn.speaker === "student" ? "Estudiante" : "Tutor"}</strong>
                <span lang="en">{turn.text}</span>{turn.status === "interrupted" && <small>Interrumpido</small>}
              </p>
            ))}
          </div>
          <button disabled={busy} onClick={() => action(() => connection.current.stream.sendTurn())}>
            Enviar turno simulado
          </button>
        </>
      )}
      {phase === "anchors" && (
        <>
          <h2>Frases ancla</h2>
          <ol className="anchors">
            {catalog.anchors.map((phrase) => (
              <li key={phrase.id} aria-current={phrase.id === currentAnchor?.id ? "step" : undefined}>
                <span lang="en">{phrase.text_en}</span>
                {attempts.some((attempt) => attempt.phrase_id === phrase.id && attempt.status === "valid") && <small>Válida</small>}
              </li>
            ))}
          </ol>
          {lastAttempt?.status === "invalid" && (
            <p role="status">Muestra no evaluable. Te quedan {3 - lastAttempt.attempt_number} reintentos.</p>
          )}
          <button disabled={busy || lastAttempt?.status === "pending" || !currentAnchor}
            onClick={() => sendAnchor(currentAnchor.id)}>Enviar muestra sintética</button>
        </>
      )}
      {phase === "processing" && <p role="status">{stages[stage] ?? "Preparando la evaluación…"}</p>}
      {phase === "recoverable_error" && (
        <div className="notice" role="status">
          <p>La operación simulada falló. Puedes reintentar una vez.</p>
          {incident && <button disabled={busy} onClick={() => command("retry", {
            operation_id: incident.operation_id,
          })}>Reintentar</button>}
        </div>
      )}
      {view && !finished && (
        <div className="actions">
          <button className="secondary" disabled={busy} onClick={() => command("cancel")}>Cancelar práctica</button>
          <span className="muted">{statusLabel[phase]}</span>
        </div>
      )}
    </section>
  );
}
