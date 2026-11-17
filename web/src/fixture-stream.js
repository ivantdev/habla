// Señal sintética y reproducción del perfil del spike. Sin permisos de micrófono.
import { ApiError, practicePath } from "./api.js";
import { conforms } from "./contract.js";

const headerBytes = 56;
const frameBytes = 640;
const encoder = new TextEncoder();

function uuidBytes(id) {
  return Uint8Array.from(id.replaceAll("-", "").match(/../g), (byte) => parseInt(byte, 16));
}

function sameBytes(view, offset, id) {
  return uuidBytes(id).every((byte, index) => view.getUint8(offset + index) === byte);
}

function writeTone(view, offset, frames, rate, first = 0) {
  for (let index = 0; index < frames; index++) {
    const amplitude = Math.sin((first + index) * 2 * Math.PI * 420 / rate) * 1600;
    view.setInt16(offset + 2 * index, amplitude, true);
  }
}

export function sampleWave() {
  const rate = 16000;
  const frames = 5120;
  const buffer = new ArrayBuffer(44 + frames * 2);
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  bytes.set(encoder.encode("RIFF"), 0);
  view.setUint32(4, buffer.byteLength - 8, true);
  bytes.set(encoder.encode("WAVEfmt "), 8);
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  bytes.set(encoder.encode("data"), 36);
  view.setUint32(40, frames * 2, true);
  writeTone(view, 44, frames, rate);
  return new Blob([buffer], { type: "audio/wav" });
}

export class FixtureStream {
  constructor(practiceId, audio, onEvent, onClose) {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    this.socket = new WebSocket(`${scheme}://${location.host}/api/v1${practicePath(practiceId)}/stream`);
    this.socket.binaryType = "arraybuffer";
    this.practiceId = practiceId;
    this.audio = audio;
    this.seq = 0;
    this.incoming = 0;
    this.streamId = null;
    this.generation = null;
    this.sources = new Set();

    this.ready = new Promise((resolve, reject) => {
      this.socket.addEventListener("open", () => this.event("stream.open", {
        audio_profile_id: "pcm16-v1", client_instance_id: crypto.randomUUID(),
      }));
      this.socket.addEventListener("close", () => {
        this.stopAudio();
        reject(new ApiError("CHANNEL_CLOSED", "Se cerró el canal de la práctica."));
        onClose();
      });
      this.socket.addEventListener("error", () => {
        reject(new ApiError("CHANNEL_ERROR", "No se pudo abrir el canal de la práctica."));
      });
      this.socket.addEventListener("message", ({ data }) => {
        if (typeof data !== "string") {
          this.playFrame(data);
          return;
        }
        const event = JSON.parse(data);
        if (!conforms("Event", event) || event.practice_id !== practiceId || event.seq <= this.incoming) return;
        if (this.streamId && this.streamId !== event.stream_id) return;
        this.incoming = event.seq;
        if (event.type === "stream.rejected") {
          reject(new ApiError(event.payload.code, event.payload.message));
          return;
        }
        if (event.type === "stream.ready" && conforms("StreamReady", event.payload)) {
          this.streamId = event.payload.stream_id;
          this.outputRate = event.payload.output_sample_rate_hz;
          resolve();
          return;
        }
        if (event.type === "tutor.audio_started") {
          this.stopAudio();
          this.generation = { ...event.payload, seq: -1, start: null, next: null };
        } else if (event.type === "tutor.audio_ended" && event.payload.generation_id === this.generation?.generation_id) {
          this.generation.ended = true;
        } else if (event.type === "tutor.interrupted" && event.payload.generation_id === this.generation?.generation_id) {
          this.stopAudio();
        } else if (event.type === "practice.state_changed" && event.payload.status !== "conversation") {
          this.stopAudio();
        }
        onEvent(event);
      });
    });
  }

  event(type, payload) {
    this.socket.send(JSON.stringify({
      v: 1, event_id: crypto.randomUUID(), practice_id: this.practiceId, stream_id: this.streamId,
      seq: ++this.seq, occurred_at: new Date().toISOString(), type, payload,
    }));
  }

  sendTurn() {
    if (this.socket.readyState !== WebSocket.OPEN || !this.streamId) {
      throw new ApiError("CHANNEL_CLOSED", "Se cerró el canal de la práctica.");
    }
    const previous = this.generation;
    const heard = previous?.start == null ? 0 : Math.max(0, Math.floor(
      (Math.min(this.audio.currentTime, previous.next) - previous.start) * 1000,
    ));
    this.stopAudio();
    const turnId = crypto.randomUUID();
    this.event("student.speech_started", {
      turn_id: turnId, client_offset_ms: 0, interrupted_generation_id: previous?.generation_id ?? null,
      heard_until_ms: previous ? heard : null,
    });
    const count = 8;
    for (let seq = 0; seq < count; seq++) {
      const buffer = new ArrayBuffer(headerBytes + frameBytes);
      const view = new DataView(buffer);
      const bytes = new Uint8Array(buffer);
      view.setUint8(0, 1);
      view.setUint8(1, 1);
      view.setUint32(4, seq, true);
      bytes.set(uuidBytes(this.streamId), 8);
      bytes.set(uuidBytes(turnId), 24);
      writeTone(view, headerBytes, frameBytes / 2, 16000, seq * frameBytes / 2);
      this.socket.send(buffer);
    }
    this.event("student.turn_ended", { turn_id: turnId, last_chunk_seq: count - 1 });
  }

  playFrame(data) {
    const generation = this.generation;
    if (!this.audio || !generation || generation.ended || data.byteLength !== headerBytes + this.outputRate / 25) return;
    const view = new DataView(data);
    if (view.getUint8(0) !== 1 || view.getUint8(1) !== 2 || view.getUint16(2, true) !== 0 ||
        !sameBytes(view, 8, this.streamId) || !sameBytes(view, 24, generation.turn_id) ||
        !sameBytes(view, 40, generation.generation_id)) return;
    const seq = view.getUint32(4, true);
    if (seq <= generation.seq) return;
    generation.seq = seq;
    const buffer = this.audio.createBuffer(1, this.outputRate / 50, this.outputRate);
    const target = buffer.getChannelData(0);
    for (let i = 0; i < target.length; i++) target[i] = view.getInt16(headerBytes + 2 * i, true) / 32768;
    const node = this.audio.createBufferSource();
    node.buffer = buffer;
    node.connect(this.audio.destination);
    generation.start ??= this.audio.currentTime + 0.08;
    const at = Math.max(generation.next ?? generation.start, this.audio.currentTime);
    generation.next = at + buffer.duration;
    this.sources.add(node);
    node.onended = () => this.sources.delete(node);
    node.start(at);
  }

  stopAudio() {
    for (const node of this.sources) node.stop();
    this.sources.clear();
    this.generation = null;
  }

  close() {
    this.stopAudio();
    this.socket.close();
  }
}
