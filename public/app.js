const bpmInput = document.querySelector('#bpm');
const bpmOutput = document.querySelector('#bpm-output');
const bpmHint = document.querySelector('#bpm-hint');
const targetTime = document.querySelector('#target-time');
const elapsed = document.querySelector('#elapsed');
const recordButton = document.querySelector('#record-button');
const recordLabel = document.querySelector('#record-label');
const recordStatus = document.querySelector('#record-status');
const uploadInput = document.querySelector('#audio-upload');
const sourcePreview = document.querySelector('#source-preview');
const generateButton = document.querySelector('#generate-button');
const message = document.querySelector('#message');
const meter = document.querySelector('#meter');
const countIn = document.querySelector('#count-in');
const countInValue = countIn.querySelector('span');
const resultSection = document.querySelector('#result');

let sourceBars = 4;
let resultBars = 8;
let style = 'indie';
let audioBlob = null;
let mediaRecorder = null;
let activeStream = null;
let stopTimer = null;
let clockTimer = null;
let recordingStartedAt = 0;

function secondsForSelection() {
  return sourceBars * 4 * 60 / Number(bpmInput.value);
}

function formatTime(seconds) {
  const whole = Math.max(0, Math.round(seconds));
  return `${String(Math.floor(whole / 60)).padStart(2, '0')}:${String(whole % 60).padStart(2, '0')}`;
}

function updateDuration() {
  bpmOutput.textContent = bpmInput.value;
  targetTime.textContent = `из ${formatTime(secondsForSelection())}`;
}

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle('is-error', isError);
}

function setRecordingState(active) {
  recordButton.classList.toggle('is-recording', active);
  recordLabel.textContent = active ? 'Остановить' : 'Начать запись';
  recordStatus.dataset.state = active ? 'recording' : 'idle';
  recordStatus.lastChild.textContent = active ? ' Идёт запись' : ' Микрофон готов';
  meter.classList.toggle('is-live', active);
}

async function analyzeTempo(blob) {
  generateButton.disabled = true;
  bpmHint.classList.remove('is-detected');
  bpmHint.textContent = 'Слушаем удары и определяем темп…';
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': blob.type || 'audio/webm' },
      body: blob,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Темп не определён');
    bpmInput.value = String(payload.bpm);
    updateDuration();
    const confidence = Math.round(payload.confidence * 100);
    bpmHint.textContent = `Найдено примерно ${payload.bpm} BPM · уверенность ${confidence}%. Проверь на слух.`;
    bpmHint.classList.add('is-detected');
    setMessage(`Темп найден: ${payload.bpm} BPM. Теперь можно собрать эскиз.`);
  } catch (error) {
    bpmHint.textContent = 'Авто-BPM не сработал — выставь темп вручную.';
    setMessage(`${error.message}. Можно продолжить с ручным BPM.`, true);
  } finally {
    generateButton.disabled = false;
  }
}

async function playClick(audioContext, accent = false) {
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.frequency.value = accent ? 1160 : 840;
  gain.gain.setValueAtTime(0.001, audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.22, audioContext.currentTime + 0.005);
  gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.07);
  oscillator.connect(gain).connect(audioContext.destination);
  oscillator.start();
  oscillator.stop(audioContext.currentTime + 0.08);
}

function wait(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}

async function runCountIn() {
  const audioContext = new AudioContext();
  const beatMs = 60_000 / Number(bpmInput.value);
  countIn.hidden = false;
  for (let beat = 1; beat <= 4; beat += 1) {
    countInValue.textContent = String(beat);
    playClick(audioContext, beat === 1);
    await wait(beatMs);
  }
  countIn.hidden = true;
  await audioContext.close();
}

function stopStream() {
  if (activeStream) activeStream.getTracks().forEach(track => track.stop());
  activeStream = null;
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
  clearTimeout(stopTimer);
  clearInterval(clockTimer);
  setRecordingState(false);
}

async function startRecording() {
  try {
    setMessage('');
    activeStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    await runCountIn();

    const preferred = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
    const mimeType = preferred.find(type => MediaRecorder.isTypeSupported(type));
    mediaRecorder = mimeType ? new MediaRecorder(activeStream, { mimeType }) : new MediaRecorder(activeStream);
    const chunks = [];
    mediaRecorder.addEventListener('dataavailable', event => {
      if (event.data.size) chunks.push(event.data);
    });
    mediaRecorder.addEventListener('stop', async () => {
      audioBlob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
      sourcePreview.src = URL.createObjectURL(audioBlob);
      sourcePreview.hidden = false;
      stopStream();
      setMessage('Партия записана. Определяем BPM…');
      await analyzeTempo(audioBlob);
    });

    mediaRecorder.start(250);
    recordingStartedAt = Date.now();
    elapsed.textContent = '00:00';
    setRecordingState(true);
    clockTimer = setInterval(() => {
      elapsed.textContent = formatTime((Date.now() - recordingStartedAt) / 1000);
    }, 250);
    stopTimer = setTimeout(stopRecording, secondsForSelection() * 1000);
  } catch (error) {
    stopStream();
    setRecordingState(false);
    setMessage(error?.name === 'NotAllowedError' ? 'Нужен доступ к микрофону.' : `Не удалось начать запись: ${error.message}`, true);
  }
}

recordButton.addEventListener('click', () => {
  if (mediaRecorder?.state === 'recording') stopRecording();
  else startRecording();
});

uploadInput.addEventListener('change', async () => {
  const file = uploadInput.files?.[0];
  if (!file) return;
  audioBlob = file;
  sourcePreview.src = URL.createObjectURL(file);
  sourcePreview.hidden = false;
  setMessage(`Загружен файл: ${file.name}. Определяем BPM…`);
  await analyzeTempo(file);
});

bpmInput.addEventListener('input', () => {
  updateDuration();
  bpmHint.textContent = 'Темп скорректирован вручную.';
  bpmHint.classList.remove('is-detected');
});

document.querySelectorAll('.source-bars-option').forEach(button => {
  button.addEventListener('click', () => {
    sourceBars = Number(button.dataset.sourceBars);
    document.querySelectorAll('.source-bars-option').forEach(item => item.classList.toggle('is-active', item === button));
    updateDuration();
  });
});

document.querySelectorAll('.result-bars-option').forEach(button => {
  button.addEventListener('click', () => {
    resultBars = Number(button.dataset.resultBars);
    document.querySelectorAll('.result-bars-option').forEach(item => item.classList.toggle('is-active', item === button));
  });
});

document.querySelectorAll('.style-card').forEach(button => {
  button.addEventListener('click', () => {
    style = button.dataset.style;
    document.querySelectorAll('.style-card').forEach(item => item.classList.toggle('is-active', item === button));
  });
});

generateButton.addEventListener('click', async () => {
  if (!audioBlob) return;
  generateButton.disabled = true;
  generateButton.classList.add('is-loading');
  generateButton.querySelector('span').textContent = 'Собираем эскиз';
  setMessage('Создаём бас, клавиши и общий микс…');

  try {
    const params = new URLSearchParams({ bpm: bpmInput.value, bars: String(resultBars), style });
    const response = await fetch(`/api/render?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': audioBlob.type || 'audio/webm' },
      body: audioBlob,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Не удалось собрать эскиз');

    document.querySelector('#mix-player').src = payload.mix_url;
    document.querySelector('#drums-player').src = payload.stems.drums;
    document.querySelector('#bass-player').src = payload.stems.bass;
    document.querySelector('#keys-player').src = payload.stems.keys;
    document.querySelector('#download-link').href = payload.mix_url;
    const extension = payload.drums_extension.extended
      ? ` · грув повторён ${payload.drums_extension.repeats}×`
      : '';
    document.querySelector('#result-meta').textContent = `${payload.style_name} · ${payload.key} · ${payload.bpm} BPM · ${payload.bars} тактов${extension}`;
    resultSection.hidden = false;
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setMessage('Эскиз готов.');
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    generateButton.disabled = false;
    generateButton.classList.remove('is-loading');
    generateButton.querySelector('span').textContent = 'Собрать музыкальный эскиз';
  }
});

updateDuration();
