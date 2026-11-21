import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AudioLines, Check, Clock3, Headphones, Info, MessageCircle, Play, RotateCcw } from "lucide-react";
import { api, practicePath, reasonLabel } from "./api.js";
import { conforms } from "./contract.js";
import { FixtureStream, sampleWave } from "./fixture-stream.js";
import { PageHeading, PracticeSteps, TopicIcon, topicDetails } from "./ui.jsx";

const stages = {
  acoustic: "Evaluando muestras",
  linguistic: "Revisando la transcripción",
  report: "Preparando el informe",
  cleanup: "Limpiando el audio temporal",
};
const levelNames = { A2: "Básico", B1: "Intermedio", B2: "Intermedio alto" };

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
  const [speaking, setSpeaking] = useState(false);
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
      if (payload.status !== "conversation") setSpeaking(false);
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
    } else if (type === "tutor.audio_started") {
      setSpeaking(true);
    } else if (type === "tutor.audio_ended" || type === "tutor.interrupted") {
      setSpeaking(false);
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
      setSpeaking(false);
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
  const selectedTopic = catalog.topics.find((topic) => topic.id === selection.topic_id);
  const activeTopic = catalog.topics.find((topic) => topic.id === view?.topic_id);
  const currentStage = Object.keys(stages).indexOf(stage);

  return (
    <div className="practice-page">
      {error && <p className="notice error" role="alert">{error}</p>}
      {(!view || finished) && (
        <>
          {finished && (
            <div className="notice finished-notice" role="status">
              {phase === "completed" ? <><Check size={20} aria-hidden="true" /><span>Tu práctica está lista.
                {" "}<Link to={"/sesiones/" + view.id}>Ver informe simulado</Link></span></>
                : (reasonLabel[view.reason_code] ?? "La práctica quedó incompleta.")}
            </div>
          )}
          <section className="practice-hero">
            <div className="hero-copy">
              <p className="eyebrow"><span className="tiny-wave" aria-hidden="true"><i /><i /><i /></span>DALE VOZ A TU INGLÉS</p>
              <h1>Las conversaciones<br />abren <em>puertas.</em></h1>
              <p>Un tema cotidiano, tu propio ritmo<br className="desktop-break" /> y un espacio para soltarte hablando.</p>
              <a className="button hero-button" href="#preparar-practica"><MessageCircle size={17} aria-hidden="true" />Elige tu conversación</a>
            </div>
            <div className="hero-photo">
              <img src="/images/practice-hero.png" alt="Estudiante practicando una conversación con auriculares" width="1536" height="1024" fetchPriority="high" />
            </div>
          </section>
          <form id="preparar-practica" className="practice-setup" onSubmit={begin}>
            <section className="topic-section">
              <div className="section-heading"><div><h2>¿De qué hablamos hoy?</h2><p>Escoge un tema que te dé ganas de conversar.</p></div></div>
              <fieldset className="topic-grid">
                <legend className="sr-only">Tema de la práctica</legend>
                {catalog.topics.map((topic) => (
                  <label key={topic.id} className={"topic-card " + (selection.topic_id === topic.id ? "selected" : "")}>
                    <input type="radio" name="topic" value={topic.id} checked={selection.topic_id === topic.id}
                      onChange={() => setSelection({ ...selection, topic_id: topic.id })} />
                    <span className="topic-card-top"><TopicIcon topicId={topic.id} /><span className="radio-indicator"><Check size={12} aria-hidden="true" /></span></span>
                    <strong>{topic.label_es}</strong>
                    <span className="topic-description">{topicDetails[topic.id]?.description}</span>
                  </label>
                ))}
              </fieldset>
              <div className="practice-tip"><Headphones size={19} aria-hidden="true" />
                <p>Primero, conversa. Al terminar, revisa las observaciones de tu sesión.</p>
              </div>
            </section>
            <aside className="session-config panel">
              <h2>Hazla a tu medida</h2>
              <fieldset className="level-picker">
                <legend>Tu nivel de inglés</legend>
                <div className="segmented">
                  {catalog.levels.map((level) => <label key={level}>
                    <input type="radio" name="level" value={level} checked={selection.level === level}
                      onChange={() => setSelection({ ...selection, level })} />
                    <span>{level}</span>
                  </label>)}
                </div>
                <p className="field-hint">{levelNames[selection.level]}</p>
              </fieldset>
              <fieldset className="duration-picker">
                <legend>¿Cuánto tiempo tienes?</legend>
                <div className="duration-options">
                  {[300, 600].map((duration) => <label key={duration}>
                    <input type="radio" name="duration" value={duration} checked={selection.duration_seconds === duration}
                      onChange={() => setSelection({ ...selection, duration_seconds: duration })} />
                    <span><Clock3 size={16} aria-hidden="true" /><strong>{duration / 60} <small>min</small></strong></span>
                  </label>)}
                </div>
              </fieldset>
              <div className="selection-summary"><TopicIcon topicId={selection.topic_id} size={17} />
                <span><strong>{selectedTopic.label_es}</strong><small>{selection.level} · {selection.duration_seconds / 60} minutos</small></span>
              </div>
              <button className="start-button" disabled={busy}>
                {busy ? <span className="spinner" /> : <Play size={17} fill="currentColor" aria-hidden="true" />}
                {busy ? "Preparando…" : "Iniciar práctica simulada"}
              </button>
              <p className="simulation-hint">Este recorrido utiliza audio de prueba.</p>
            </aside>
          </form>
          <PracticeSteps />
        </>
      )}
      {view && !finished && (
        <>
          <PageHeading title={phase === "anchors" ? "Dale un momento a tu pronunciación" : phase === "processing" ? "Tu conversación, en perspectiva" : "Es momento de conversar"}
            description={(activeTopic?.label_es ?? "") + " · " + view.level}>
            {phase === "conversation" && <RemainingTime endsAt={view.conversation_ends_at} />}
          </PageHeading>
          <PracticeSteps status={phase} />
          {phase === "ready" && <div className="panel loading-line" role="status"><span className="spinner" />Abriendo el canal de práctica…</div>}
          {phase === "conversation" && (
            <div className="conversation-layout">
              <section className="voice-studio">
                <span className="studio-label">TU TUTOR DE INGLÉS</span>
                <div className={"voice-orb " + (speaking ? "speaking" : "")}><AudioLines size={48} strokeWidth={1.2} aria-hidden="true" /></div>
                <h2>{speaking ? "El tutor está respondiendo" : "Tu próxima idea, en inglés"}</h2>
                <p>Pulsa el botón para enviar un turno simulado.</p>
                <div className={"voice-wave " + (speaking ? "active" : "")} aria-hidden="true">
                  {[12, 23, 34, 19, 41, 31, 49, 28, 37, 22, 32, 17, 10].map((height, index) =>
                    <i key={index} style={{ height, animationDelay: (index * 0.08) + "s" }} />)}
                </div>
                <button disabled={busy} onClick={() => action(() => connection.current.stream.sendTurn())}>
                  <MessageCircle size={18} aria-hidden="true" />Enviar turno simulado
                </button>
              </section>
              <section className="panel transcript-panel">
                <div className="section-heading"><h2>La conversación</h2><span className="muted">En inglés</span></div>
                <div className="transcript" role="log" aria-label="Transcripción simulada" aria-live="polite">
                  {turns.length === 0 && <div className="transcript-empty"><MessageCircle size={31} strokeWidth={1.3} aria-hidden="true" /><p>Todo empieza con una conversación.</p><small>Tus intervenciones aparecerán aquí.</small></div>}
                  {turns.map((turn) => (
                    <div key={turn.id} className={"chat-turn " + turn.speaker}>
                      <strong>{turn.speaker === "student" ? "Tú" : "Tutor"}</strong>
                      <p lang="en">{turn.text}</p>{turn.status === "interrupted" && <small>Interrumpido</small>}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
          {phase === "anchors" && (
            <div className="anchor-layout">
              <ol className="anchors panel" aria-label="Las cinco frases">
                {catalog.anchors.map((phrase) => {
                  const valid = attempts.some((item) => item.phrase_id === phrase.id && item.status === "valid");
                  return <li key={phrase.id} className={valid ? "valid" : ""}
                    aria-current={phrase.id === currentAnchor?.id ? "step" : undefined}>
                    <span className="anchor-position">{valid ? <Check size={16} aria-hidden="true" /> : phrase.position}</span>
                    <span lang="en">{phrase.text_en}</span>
                  </li>;
                })}
              </ol>
              <section className="panel anchor-focus">
                <span className="eyebrow">FRASE {currentAnchor?.position ?? 5} DE 5</span>
                <h2 lang="en">{currentAnchor?.text_en}</h2>
                {currentAnchor && <audio controls preload="none" aria-label="Referencia sintética de la frase"
                  src={"/api/v1/references/" + encodeURIComponent(currentAnchor.reference_audio_id)} />}
                <p className="muted">Escucha la referencia y envía una muestra de prueba.</p>
                {lastAttempt?.status === "invalid" && <p className="notice error" role="status">
                  Muestra no evaluable. Te quedan {3 - lastAttempt.attempt_number} reintentos.
                </p>}
                <button disabled={busy || lastAttempt?.status === "pending" || !currentAnchor}
                  onClick={() => sendAnchor(currentAnchor.id)}>
                  <AudioLines size={18} aria-hidden="true" />{lastAttempt?.status === "pending" ? "Validando muestra…" : "Enviar muestra sintética"}
                </button>
              </section>
            </div>
          )}
          {phase === "processing" && <section className="panel processing-panel">
            <div className="processing-orb"><AudioLines size={38} strokeWidth={1.3} aria-hidden="true" /></div>
            <h2>Cada detalle tiene su momento.</h2>
            <p className="muted" role="status">{stages[stage] ?? "Preparando la evaluación…"}</p>
            <ol className="processing-stages">
              {Object.entries(stages).map(([key, label], index) => <li key={key} className={index < currentStage ? "done" : index === currentStage ? "current" : ""}>
                {index < currentStage ? <Check size={16} aria-hidden="true" /> : index === currentStage ? <span className="spinner" /> : <span className="stage-dot" />}
                {label}
              </li>)}
            </ol>
          </section>}
          {phase === "recoverable_error" && <section className="panel retry-panel" role="status">
            <span className="empty-icon"><RotateCcw size={30} aria-hidden="true" /></span>
            <h2>Probemos una vez más</h2>
            <p>La operación simulada falló. Tienes un reintento disponible.</p>
            {incident && <button disabled={busy} onClick={() => command("retry", { operation_id: incident.operation_id })}>
              <RotateCcw size={17} aria-hidden="true" />Reintentar
            </button>}
          </section>}
          <div className="practice-bottom"><p><Info size={16} aria-hidden="true" />Práctica con audio simulado</p>
            <button className="text-button danger" disabled={busy} onClick={() => command("cancel")}>Cancelar práctica</button>
          </div>
        </>
      )}
    </div>
  );
}
