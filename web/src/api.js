import { conforms } from "./contract.js";

export class ApiError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

export async function api(path, contract, options = {}) {
  const headers = new Headers(options.headers);
  let body = options.body;
  if (body && !(body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers, body, cache: "no-store" });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("NETWORK_ERROR", "No se pudo conectar con la API local.");
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (conforms("ErrorEnvelope", payload)) throw new ApiError(payload.error.code, payload.error.message);
    throw new ApiError("API_ERROR", "La API local devolvió un error.");
  }
  if (!payload || (contract && !conforms(contract, payload))) {
    throw new ApiError("CONTRACT_ERROR", "La respuesta de la API no coincide con el contrato v1.");
  }
  return payload;
}

export const statusLabel = {
  ready: "Lista",
  conversation: "Conversación",
  anchors: "Frases ancla",
  processing: "Procesando",
  recoverable_error: "Reintento disponible",
  completed: "Completada",
  incomplete: "Incompleta",
};

export const reasonLabel = {
  CANCELLED: "Cancelaste la práctica.",
  CHANNEL_CLOSED: "Se cerró el canal. Puedes empezar otra práctica.",
  READY_EXPIRED: "Venció el tiempo para abrir el canal.",
  SERVER_RESTARTED: "El servidor se reinició durante la práctica.",
  RETRY_EXHAUSTED: "El reintento falló. Puedes empezar otra práctica.",
  RETRY_WINDOW_EXPIRED: "Terminó el plazo para reintentar.",
  ATTEMPTS_EXHAUSTED: "Se agotaron los tres intentos de la frase.",
};

export function practicePath(id) {
  return `/practices/${encodeURIComponent(id)}`;
}
