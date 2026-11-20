import React from "react";
import {
  AudioLines, BriefcaseBusiness, Check, Circle, Clock3, FileText, MessageCircle,
  Newspaper, Plane, Sun, Utensils,
} from "lucide-react";

export const topicDetails = {
  restaurant: { Icon: Utensils, color: "peach", description: "Una mesa, un menú y algo que contar." },
  job_interview: { Icon: BriefcaseBusiness, color: "lavender", description: "Habla de ti y de lo que sabes hacer." },
  weekend: { Icon: Sun, color: "yellow", description: "Planes, pasatiempos y pequeñas historias." },
  travel: { Icon: Plane, color: "blue", description: "El siguiente destino empieza hablando." },
  news: { Icon: Newspaper, color: "mint", description: "Comparte lo que pasa a tu alrededor." },
};

export function TopicIcon({ topicId, size = 22 }) {
  const { Icon = MessageCircle, color = "mint" } = topicDetails[topicId] ?? {};
  return <span className={"topic-icon " + color}><Icon size={size} strokeWidth={1.7} aria-hidden="true" /></span>;
}

export function PageHeading({ title, description, children }) {
  return (
    <div className="page-heading">
      <div><h1>{title}</h1>{description && <p>{description}</p>}</div>
      {children}
    </div>
  );
}

export function EmptyState({ Icon = MessageCircle, title, children }) {
  return (
    <div className="empty-state">
      <span className="empty-icon"><Icon size={30} strokeWidth={1.5} aria-hidden="true" /></span>
      <h2>{title}</h2>
      {children}
    </div>
  );
}

export function PracticeSteps({ status }) {
  const current = { ready: 0, conversation: 0, anchors: 1, processing: 2, completed: 2 }[status] ?? 0;
  return (
    <ol className="practice-steps" aria-label="Etapas de la práctica">
      {[
        { title: "Conversa", detail: "A tu nivel", Icon: MessageCircle },
        { title: "Lee cinco frases", detail: "Practica los sonidos", Icon: AudioLines },
        { title: "Revisa tu informe", detail: "Vuelve a escucharte", Icon: FileText },
      ].map(({ title, detail, Icon }, index) => (
        <li key={title} className={index < current ? "done" : index === current ? "current" : ""}
          aria-current={status && index === current ? "step" : undefined}>
          <span className="step-icon">{index < current ? <Check size={18} aria-hidden="true" />
            : <Icon size={18} strokeWidth={1.7} aria-hidden="true" />}</span>
          <span><strong>{title}</strong><small>{detail}</small></span>
        </li>
      ))}
    </ol>
  );
}

export function StatusBadge({ status, label }) {
  const complete = status === "completed";
  return (
    <span className={"status-badge " + (complete ? "complete" : status === "incomplete" ? "incomplete" : "pending")}>
      {complete ? <Check size={13} aria-hidden="true" />
        : status === "incomplete" ? <Circle size={10} aria-hidden="true" /> : <Clock3 size={13} aria-hidden="true" />}
      {label}
    </span>
  );
}
