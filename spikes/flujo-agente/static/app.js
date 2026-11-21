// MVP desechable del flujo de voz (S05). Envía el micrófono a 16 kHz, reproduce la voz
// del tutor y muestra la transcripción de ambos lados.
const toggle = document.getElementById('toggle');
const stateEl = document.querySelector('#state b');
const logEl = document.getElementById('log');
let ws, ctx, stream, outRate, playHead = 0, tutorEl, waitingPlayback = false;

function add(cls, who, text) {
  const el = document.createElement('div');
  el.className = `msg ${cls}`;
  el.innerHTML = `<div class="who">${who}</div><div class="text"></div><div class="meta"></div>`;
  el.querySelector('.text').textContent = text;
  logEl.appendChild(el);
  logEl.scrollTop = logEl.scrollHeight;
  return el;
}

function play(buf) {
  const pcm = new Int16Array(buf);
  const audio = ctx.createBuffer(1, pcm.length, outRate);
  const ch = audio.getChannelData(0);
  for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 32768;
  const src = ctx.createBufferSource();
  src.buffer = audio;
  src.connect(ctx.destination);
  playHead = Math.max(playHead, ctx.currentTime);
  src.start(playHead);
  playHead += audio.duration;
}

// Avisa al servidor cuando termina de sonar el tutor, para que vuelva a escuchar.
function checkPlayback() {
  if (!waitingPlayback || !ws) return;
  if (ctx.currentTime >= playHead) {
    waitingPlayback = false;
    ws.send(JSON.stringify({ type: 'playback_ended' }));
  } else {
    setTimeout(checkPlayback, 100);
  }
}

function onEvent(ev) {
  switch (ev.type) {
    case 'config':
      outRate = ev.sample_rate;
      document.getElementById('config').textContent = `Nivel ${ev.level} · tema ${ev.topic}`;
      break;
    case 'state':
      stateEl.textContent = ev.value;
      break;
    case 'student':
      add('student', 'Estudiante', ev.text || '(sin texto)').querySelector('.meta').textContent =
        `${ev.audio_s} s de audio`;
      break;
    case 'tutor_start':
      tutorEl = add('tutor', 'Tutor', '');
      break;
    case 'tutor_delta':
      tutorEl.querySelector('.text').textContent += ev.text;
      logEl.scrollTop = logEl.scrollHeight;
      break;
    case 'tutor_done': {
      const t = ev.timings;
      tutorEl.querySelector('.meta').textContent = [
        t.asr_ms != null && `ASR ${t.asr_ms} ms`,
        `primer token ${t.ttft_ms} ms`,
        `primer audio ${t.first_audio_ms} ms`,
      ].filter(Boolean).join(' · ');
      break;
    }
    case 'error':
      add('error', 'Error', ev.message);
      break;
    case 'playback_wait':
      waitingPlayback = true;
      checkPlayback();
      break;
  }
}

async function start() {
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  ctx = new AudioContext();
  await ctx.audioWorklet.addModule('capture-worklet.js');
  const mic = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, 'capture-16k');
  mic.connect(node);
  logEl.innerHTML = '';
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.binaryType = 'arraybuffer';
  ws.onmessage = (m) => (typeof m.data === 'string' ? onEvent(JSON.parse(m.data)) : play(m.data));
  ws.onclose = () => stop();
  node.port.onmessage = (e) => ws.readyState === WebSocket.OPEN && ws.send(e.data.pcm);
  toggle.textContent = 'Terminar';
  toggle.classList.add('stop');
}

function stop() {
  if (!ws) return;
  const s = ws;
  ws = null;
  s.close();
  stream.getTracks().forEach((t) => t.stop());
  ctx.close();
  playHead = 0;
  waitingPlayback = false;
  stateEl.textContent = 'detenido';
  toggle.textContent = 'Empezar';
  toggle.classList.remove('stop');
}

toggle.onclick = () => (ws ? stop() : start().catch((e) => { add('error', 'Error', String(e)); stop(); }));
