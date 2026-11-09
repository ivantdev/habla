// Spike desechable (S05-P-01, C-04). Convierte la entrada del micrófono, a la frecuencia
// real del AudioContext, en PCM s16le mono de 16 kHz y la entrega en frames de 20 ms.
const OUT_RATE = 16000;
const FRAME = 320; // 20 ms a 16 kHz = 640 bytes
const TAPS = 127;

// Paso bajo FIR (sinc con ventana Blackman) para no plegar frecuencias por encima de 8 kHz.
function lowpass(n, fc) {
  const h = new Float32Array(n);
  const m = (n - 1) / 2;
  let sum = 0;
  for (let i = 0; i < n; i++) {
    const x = i - m;
    const sinc = x === 0 ? 2 * fc : Math.sin(2 * Math.PI * fc * x) / (Math.PI * x);
    const w = 0.42 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1)) + 0.08 * Math.cos((4 * Math.PI * i) / (n - 1));
    h[i] = sinc * w;
    sum += h[i];
  }
  for (let i = 0; i < n; i++) h[i] /= sum;
  return h;
}

class Capture16k extends AudioWorkletProcessor {
  constructor() {
    super();
    this.step = sampleRate / OUT_RATE; // muestras de entrada por muestra de salida
    this.taps = lowpass(TAPS, 7000 / sampleRate);
    this.hist = new Float32Array(TAPS); // línea de retardo circular
    this.h = 0;
    this.n = 0; // índice de la muestra de entrada actual
    this.k = 0; // índice de la próxima muestra de salida
    this.prev = 0; // muestra filtrada anterior
    this.frame = new Int16Array(FRAME);
    this.len = 0;
    this.energy = 0;
  }

  process(inputs) {
    const x = inputs[0][0];
    if (!x) return true;
    for (let i = 0; i < x.length; i++) {
      this.hist[this.h] = x[i];
      let y = 0;
      for (let k = 0, j = this.h; k < TAPS; k++) {
        y += this.taps[k] * this.hist[j];
        j = j === 0 ? TAPS - 1 : j - 1;
      }
      this.h = this.h === TAPS - 1 ? 0 : this.h + 1;
      // Salidas cuya posición cae entre la muestra filtrada anterior y la actual.
      for (let t = this.k * this.step; t <= this.n; t = ++this.k * this.step) {
        const frac = t - (this.n - 1);
        this.push(this.prev + (y - this.prev) * frac, i);
      }
      this.prev = y;
      this.n++;
    }
    return true;
  }

  push(s, i) {
    const v = Math.max(-1, Math.min(1, s));
    this.frame[this.len++] = Math.round(v < 0 ? v * 0x8000 : v * 0x7fff);
    this.energy += v * v;
    if (this.len === FRAME) {
      const pcm = this.frame.buffer;
      // t: instante del AudioContext en que termina el frame.
      this.port.postMessage({ pcm, rms: Math.sqrt(this.energy / FRAME), t: currentTime + (i + 1) / sampleRate }, [pcm]);
      this.frame = new Int16Array(FRAME);
      this.len = 0;
      this.energy = 0;
    }
  }
}

registerProcessor('capture-16k', Capture16k);
