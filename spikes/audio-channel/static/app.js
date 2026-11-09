// Spike desechable del canal de audio (S05-P-01, C-04). No es código de producto.
const PROFILE = 'pcm16-v1';
const PRACTICE_ID = 'spike-practice';
const CLIENT_INSTANCE_ID = crypto.randomUUID();
const HEADER_BYTES = 56;
const KIND_STUDENT = 1;
const KIND_TUTOR = 2;
const FRAME_MS = 20;
const NIL = '00000000-0000-0000-0000-000000000000';
const JITTER_S = 0.08; // colchón antes del primer frame de cada generación
const HANGOVER_FRAMES = 25; // 500 ms por debajo del umbral cierran el turno
const MIN_THRESHOLD_DB = -50;
const FADE_S = 0.01; // rampa de salida al interrumpir; evita el clic

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
for (const id of ['aec', 'ns', 'agc']) if (params.get(id) === '0') $(id).checked = false;
$('cond').value = params.get('cond') ?? '';
for (const id of ['salida', 'prueba']) {
  const v = params.get(id);
  if ([...$(id).options].some((o) => o.value === v)) $(id).value = v;
}

const state = {
  ctx: null, track: null, micReady: false,
  ws: null, streamId: null, seq: 0, outRate: null, chunkSeq: 0,
  noiseDb: null, above: 0, below: 0, onset: null, speaking: false, studentTurn: NIL,
  gens: new Map(), currentGen: null, tutorRequestedAt: null, interruptSentAt: null,
};
const metrics = {
  env: {}, rtt_ms: [], interruptions: [], tutor: [],
  frames_sent: 0, late_frames_discarded: 0, unknown_frames: 0, underruns: 0, server: null,
};
window.spike = { state, metrics, summary };

const ms = (s) => Math.round(s * 1000 * 10) / 10;
const sleep = (t) => new Promise((r) => setTimeout(r, t));

function log(text) {
  const li = document.createElement('li');
  li.textContent = `${new Date().toISOString().slice(11, 23)} ${text}`;
  $('log').prepend(li);
  console.log(text);
}

// --- Cabecera binaria: version u8 | kind u8 | reserved u16 | chunk_seq u32 | 3 × UUID de 16 bytes (LE)

function uuidToBytes(u, out, off) {
  const h = u.replace(/-/g, '');
  for (let i = 0; i < 16; i++) out[off + i] = parseInt(h.substr(i * 2, 2), 16);
}

function bytesToUuid(b, off) {
  let h = '';
  for (let i = 0; i < 16; i++) h += b[off + i].toString(16).padStart(2, '0');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

function packFrame(kind, chunkSeq, streamId, turnId, genId, pcm) {
  const buf = new ArrayBuffer(HEADER_BYTES + pcm.byteLength);
  const dv = new DataView(buf);
  const u8 = new Uint8Array(buf);
  dv.setUint8(0, 1);
  dv.setUint8(1, kind);
  dv.setUint16(2, 0, true);
  dv.setUint32(4, chunkSeq, true);
  uuidToBytes(streamId, u8, 8);
  uuidToBytes(turnId, u8, 24);
  uuidToBytes(genId, u8, 40);
  u8.set(new Uint8Array(pcm), HEADER_BYTES); // Int16Array del worklet: little-endian en x86 y ARM
  return buf;
}

function parseFrame(buf) {
  const dv = new DataView(buf);
  const u8 = new Uint8Array(buf);
  return {
    version: dv.getUint8(0), kind: dv.getUint8(1), chunkSeq: dv.getUint32(4, true),
    streamId: bytesToUuid(u8, 8), turnId: bytesToUuid(u8, 24), genId: bytesToUuid(u8, 40),
  };
}

function send(type, payload) {
  if (state.ws?.readyState !== WebSocket.OPEN) return;
  state.ws.send(JSON.stringify({
    v: 1, event_id: crypto.randomUUID(), practice_id: PRACTICE_ID, stream_id: state.streamId,
    seq: ++state.seq, occurred_at: new Date().toISOString(), type, payload,
  }));
}

// --- Micrófono y captura

async function startMic() {
  const audio = {
    echoCancellation: $('aec').checked, noiseSuppression: $('ns').checked,
    autoGainControl: $('agc').checked, channelCount: 1,
  };
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio });
  } catch (e) {
    const help = {
      NotAllowedError: 'Permiso de micrófono denegado: habilítalo junto a la barra de direcciones y vuelve a comprobar.',
      NotFoundError: 'No se encontró un micrófono: conéctalo y vuelve a comprobar.',
    };
    log(help[e.name] ?? `Error de micrófono: ${e.name}`);
    return;
  }
  state.track = stream.getAudioTracks()[0];
  state.ctx = new AudioContext({ latencyHint: 'interactive' });
  await state.ctx.audioWorklet.addModule('capture-worklet.js');
  const node = new AudioWorkletNode(state.ctx, 'capture-16k', { numberOfInputs: 1, numberOfOutputs: 0 });
  node.port.onmessage = (e) => onFrame(e.data);
  state.ctx.createMediaStreamSource(stream).connect(node);

  const { deviceId, groupId, ...settings } = state.track.getSettings();
  const ua = navigator.userAgentData;
  const high = ua ? await ua.getHighEntropyValues(['fullVersionList', 'platformVersion']) : {};
  metrics.env = {
    user_agent: navigator.userAgent,
    full_version_list: high.fullVersionList ?? null,
    platform: ua?.platform ?? null,
    platform_version: high.platformVersion ?? null,
    origin: location.origin,
    audio_context_sample_rate: state.ctx.sampleRate,
    base_latency_ms: ms(state.ctx.baseLatency),
    requested_constraints: audio,
    track_settings: settings,
    track_label: state.track.label,
  };
  state.micReady = true;
  $('btn-mic').disabled = true;
  $('btn-connect').disabled = false;
  log(`Micrófono listo: AudioContext a ${state.ctx.sampleRate} Hz; ajustes ${JSON.stringify(settings)}`);
}

function onFrame({ pcm, rms, t }) {
  const db = Math.max(-100, 20 * Math.log10(rms + 1e-9));
  const seq = state.chunkSeq;
  vad(db, t, seq); // antes de enviar: la parada local no espera a la red
  if (state.streamId && state.ws?.readyState === WebSocket.OPEN) {
    state.ws.send(packFrame(KIND_STUDENT, seq, state.streamId, state.studentTurn, NIL, pcm));
    state.chunkSeq++;
    metrics.frames_sent++;
  }
  if (seq % 5 === 0) {
    $('level').value = db;
    $('db').textContent = db.toFixed(0);
    $('thr').textContent = threshold().toFixed(0);
  }
}

// --- Detector de voz por energía (solo para el spike; el producto calibra su VAD en SPEC-05)

function threshold() {
  return Math.max(MIN_THRESHOLD_DB, (state.noiseDb ?? -100) + Number($('margin').value));
}

function vad(db, t, seq) {
  const thr = threshold();
  if (!state.speaking) {
    if (db > thr) {
      if (state.above++ === 0) state.onset = { t, seq };
      if (state.above >= Number($('onset').value)) speechStarted(t);
    } else {
      state.above = 0;
      state.noiseDb = state.noiseDb === null ? db : 0.95 * state.noiseDb + 0.05 * db;
    }
  } else if (db < thr - 3) {
    if (++state.below >= HANGOVER_FRAMES) speechEnded(seq);
  } else {
    state.below = 0;
  }
}

function speechStarted(tDecision) {
  state.speaking = true;
  state.below = 0;
  state.studentTurn = crypto.randomUUID();
  $('vad').textContent = 'voz';
  const g = state.gens.get(state.currentGen);
  let stopped = null;
  if (g && isActive(g)) {
    stopped = stopGeneration(g);
    const onsetToDecision = ms(tDecision - state.onset.t) + FRAME_MS; // desde el inicio del primer frame con voz
    const frameToStop = ms(state.ctx.currentTime - tDecision); // worklet → hilo principal → parada
    const outputLatency = ms(state.ctx.outputLatency ?? 0);
    const inputLatency = ms(state.track.getSettings().latency ?? 0);
    metrics.interruptions.push({
      condition: $('cond').value, generation_id: g.id, heard_until_ms: stopped.heardMs,
      onset_to_decision_ms: onsetToDecision, frame_to_stop_ms: frameToStop, fade_ms: FADE_S * 1000,
      output_latency_ms: outputLatency, input_latency_ms: inputLatency,
      estimated_stop_ms: Math.round(onsetToDecision + frameToStop + FADE_S * 1000 + outputLatency + inputLatency),
      server_ack_ms: null, late_frames_discarded: 0,
    });
    state.interruptSentAt = performance.now();
    log(`Interrupción: tutor detenido; parada estimada ${metrics.interruptions.at(-1).estimated_stop_ms} ms`);
  }
  send('student.speech_started', {
    turn_id: state.studentTurn,
    client_offset_ms: state.onset.seq * FRAME_MS,
    interrupted_generation_id: stopped ? g.id : null,
    heard_until_ms: stopped ? stopped.heardMs : null,
  });
}

function speechEnded(seq) {
  state.speaking = false;
  state.above = 0;
  $('vad').textContent = 'silencio';
  send('student.turn_ended', { turn_id: state.studentTurn, last_chunk_seq: seq });
  state.studentTurn = NIL;
}

// --- Reproducción del tutor por generación

function isActive(g) {
  return !g.cancelled && !(g.ended && state.ctx.currentTime >= g.nextTime);
}

function stopGeneration(g) {
  const now = state.ctx.currentTime;
  g.cancelled = true;
  g.gain.gain.setValueAtTime(g.gain.gain.value, now);
  g.gain.gain.linearRampToValueAtTime(0, now + FADE_S);
  for (const s of g.sources) s.stop(now + FADE_S);
  g.sources.clear();
  const played = g.startTime === null ? 0 : now - g.startTime - (state.ctx.outputLatency ?? 0);
  return { heardMs: Math.round(Math.min(Math.max(0, played), g.scheduledS) * 1000) };
}

function onTutorFrame(buf) {
  const f = parseFrame(buf);
  const g = state.gens.get(f.genId);
  if (!g || f.version !== 1 || f.kind !== KIND_TUTOR || f.streamId !== state.streamId) {
    metrics.unknown_frames++;
    return;
  }
  if (g.cancelled) { // frame tardío de una generación cancelada: se descarta
    metrics.late_frames_discarded++;
    const last = metrics.interruptions.at(-1);
    if (last?.generation_id === g.id) last.late_frames_discarded++;
    return;
  }
  const n = (buf.byteLength - HEADER_BYTES) / 2;
  const audio = state.ctx.createBuffer(1, n, state.outRate);
  const ch = audio.getChannelData(0);
  const dv = new DataView(buf, HEADER_BYTES);
  for (let i = 0; i < n; i++) ch[i] = dv.getInt16(i * 2, true) / 32768;
  const src = state.ctx.createBufferSource();
  src.buffer = audio;
  src.connect(g.gain);
  const now = state.ctx.currentTime;
  if (g.startTime === null) {
    g.startTime = g.nextTime = now + JITTER_S;
    metrics.tutor.push({
      condition: $('cond').value, generation_id: g.id,
      first_frame_after_request_ms: Math.round(performance.now() - state.tutorRequestedAt),
    });
  } else if (g.nextTime < now) {
    metrics.underruns++;
    g.nextTime = now + 0.02;
  }
  src.start(g.nextTime);
  g.nextTime += audio.duration;
  g.scheduledS += audio.duration;
  g.sources.add(src);
  src.onended = () => g.sources.delete(src);
}

// --- Canal

function connect() {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${scheme}://${location.host}/api/v1/practices/${PRACTICE_ID}/stream`);
  ws.binaryType = 'arraybuffer';
  state.ws = ws;
  ws.onopen = () => send('stream.open', {
    audio_profile_id: params.get('profile') ?? PROFILE, client_instance_id: CLIENT_INSTANCE_ID,
  });
  ws.onmessage = (e) => (typeof e.data === 'string' ? onEvent(JSON.parse(e.data)) : onTutorFrame(e.data));
  ws.onclose = (e) => {
    state.streamId = null;
    log(`Canal cerrado (código ${e.code})`);
  };
  $('btn-connect').disabled = true;
}

function onEvent(msg) {
  const p = msg.payload;
  const g = state.gens.get(p.generation_id);
  switch (msg.type) {
    case 'stream.ready':
      state.streamId = p.stream_id;
      state.outRate = p.output_sample_rate_hz;
      for (const id of ['btn-rtt', 'btn-tutor', 'btn-stats']) $(id).disabled = false;
      log(`Canal listo: ${JSON.stringify(p)}`);
      break;
    case 'stream.rejected':
      log(`Canal rechazado: ${p.code} (${p.message})`);
      break;
    case 'spike.pong':
      metrics.rtt_ms.push(performance.now() - p.t_client);
      break;
    case 'tutor.audio_started': {
      const prev = state.gens.get(state.currentGen);
      if (prev && isActive(prev)) stopGeneration(prev);
      const gain = state.ctx.createGain();
      gain.connect(state.ctx.destination);
      state.gens.set(p.generation_id, {
        id: p.generation_id, gain, sources: new Set(), nextTime: 0, startTime: null,
        scheduledS: 0, cancelled: false, ended: false,
      });
      state.currentGen = p.generation_id;
      log(`Tutor: generación ${p.generation_id.slice(0, 8)} iniciada`);
      break;
    }
    case 'tutor.audio_ended':
      if (g) g.ended = true;
      log(`Tutor: generación ${p.generation_id.slice(0, 8)} terminada (${p.last_chunk_seq + 1} frames)`);
      break;
    case 'tutor.interrupted': {
      if (g && !g.cancelled) stopGeneration(g);
      const last = metrics.interruptions.at(-1);
      if (last?.generation_id === p.generation_id && state.interruptSentAt !== null) {
        last.server_ack_ms = Math.round(performance.now() - state.interruptSentAt);
        state.interruptSentAt = null;
      }
      log(`Servidor confirma interrupción; heard_until_ms=${p.heard_until_ms}`);
      break;
    }
    case 'spike.stats':
      metrics.server = p;
      $('summary').textContent = JSON.stringify(summary(), null, 2);
      break;
    default:
      log(`Evento ${msg.type}`);
  }
}

// --- Resumen y exportación

function pct(values, q) {
  if (!values.length) return null;
  const s = [...values].sort((a, b) => a - b);
  return Math.round(s[Math.ceil(q * s.length) - 1] * 10) / 10;
}

function summary() {
  const r = metrics.rtt_ms;
  return {
    env: { ...metrics.env, output_latency_ms: state.ctx ? ms(state.ctx.outputLatency ?? 0) : null },
    trial: { salida: $('salida').value, prueba: $('prueba').value },
    rtt_ms: {
      n: r.length, p50: pct(r, 0.5), p95: pct(r, 0.95), max: pct(r, 1),
      samples: r.map((v) => Math.round(v * 10) / 10),
    },
    interruptions: metrics.interruptions,
    tutor: metrics.tutor,
    frames_sent: metrics.frames_sent,
    late_frames_discarded: metrics.late_frames_discarded,
    unknown_frames: metrics.unknown_frames,
    underruns: metrics.underruns,
    server: metrics.server,
  };
}

$('btn-mic').onclick = startMic;
$('btn-connect').onclick = connect;
$('btn-rtt').onclick = async () => {
  for (let i = 0; i < 50; i++) {
    send('spike.ping', { t_client: performance.now() });
    await sleep(20);
  }
  await sleep(300);
  const s = summary().rtt_ms;
  log(`RTT de control: p50 ${s.p50} ms, p95 ${s.p95} ms, máx ${s.max} ms (n=${s.n})`);
};
$('btn-tutor').onclick = () => {
  state.tutorRequestedAt = performance.now();
  send('spike.tutor_say', { text: $('text').value.trim() || null, late_frames: Number($('late').value) });
};
$('btn-stats').onclick = () => send('spike.stats_request', {});
$('btn-summary').onclick = () => { $('summary').textContent = JSON.stringify(summary(), null, 2); };
$('btn-export').onclick = () => {
  const blob = new Blob([JSON.stringify(summary(), null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `spike-audio-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  a.click();
};
