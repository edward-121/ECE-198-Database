import { RepCounter, supportedExerciseType } from "./rep-counter.mjs";

const elements = {
  pageStatus: document.getElementById("page-status"),
  content: document.getElementById("workout-content"),
  patientName: document.getElementById("patient-name"),
  plan: document.getElementById("exercise-plan"),
  exercise: document.getElementById("exercise-select"),
  details: document.getElementById("exercise-details"),
  cameraToggle: document.getElementById("camera-enabled"),
  cameraFacing: document.getElementById("camera-facing"),
  cameraNote: document.getElementById("camera-note"),
  cameraPanel: document.getElementById("camera-panel"),
  video: document.getElementById("camera-video"),
  canvas: document.getElementById("camera-overlay"),
  stage: document.getElementById("rep-stage"),
  reps: document.getElementById("reps-input"),
  decrement: document.getElementById("decrement-reps"),
  increment: document.getElementById("increment-reps"),
  save: document.getElementById("save-set"),
  saveStatus: document.getElementById("save-status"),
};

const token = new URLSearchParams(window.location.search).get("token") || "";
let exercises = [];
let selectedExercise = null;
let cameraStream = null;
let poseLandmarker = null;
let counter = null;
let animationFrame = null;
let lastVideoTime = -1;
let cameraGeneration = 0;

function setRepValue(value, updateCounter = false) {
  const parsed = Number.parseInt(value, 10);
  const repCount = Number.isFinite(parsed) ? Math.min(10000, Math.max(0, parsed)) : 0;
  elements.reps.value = String(repCount);
  if (updateCounter && counter) counter.repCount = repCount;
}

function cameraSupported() {
  return selectedExercise && supportedExerciseType(selectedExercise.name);
}

function showExerciseDetails() {
  if (!selectedExercise) return;
  const dose = selectedExercise.sets && selectedExercise.reps
    ? `${selectedExercise.sets} sets × ${selectedExercise.reps} reps`
    : selectedExercise.duration_minutes
      ? `${selectedExercise.duration_minutes} minutes`
      : "Follow your prescribed plan";
  elements.details.textContent = `${dose} · ${selectedExercise.frequency || "As prescribed"}`
    + (selectedExercise.instructions ? ` · ${selectedExercise.instructions}` : "");
  const supported = Boolean(cameraSupported());
  elements.cameraToggle.disabled = !supported;
  elements.cameraNote.textContent = supported
    ? "Camera is off. Reps will be entered manually."
    : "Auto-counting is only supported for Squats and Bicep Curls. Use manual rep entry.";
  if (!supported && elements.cameraToggle.checked) {
    elements.cameraToggle.checked = false;
    stopCamera();
  }
}

function renderPlan() {
  elements.plan.replaceChildren();
  for (const exercise of exercises) {
    const card = document.createElement("article");
    card.className = "exercise-card";
    const heading = document.createElement("h3");
    heading.textContent = exercise.name;
    const plan = document.createElement("p");
    plan.className = "muted";
    plan.textContent = exercise.sets && exercise.reps
      ? `${exercise.sets} sets × ${exercise.reps} reps · ${exercise.frequency}`
      : `${exercise.duration_minutes || "As prescribed"}${exercise.duration_minutes ? " minutes" : ""} · ${exercise.frequency}`;
    card.append(heading, plan);
    elements.plan.append(card);

    const option = document.createElement("option");
    option.value = String(exercise.id);
    option.textContent = exercise.name;
    elements.exercise.append(option);
  }
  selectedExercise = exercises[0] || null;
  elements.exercise.disabled = exercises.length === 0;
  showExerciseDetails();
}

async function loadPlan() {
  if (!token) throw new Error("This link is missing its patient token.");
  const response = await fetch(`/api/patient-lookup?token=${encodeURIComponent(token)}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not load your exercise plan.");
  elements.patientName.textContent = data.name;
  exercises = data.exercises;
  if (exercises.length === 0) {
    elements.pageStatus.textContent = "There are no exercises assigned to this patient yet.";
    return;
  }
  renderPlan();
  elements.pageStatus.hidden = true;
  elements.content.hidden = false;
}

function drawSkeleton(landmarks) {
  const canvas = elements.canvas;
  const video = elements.video;
  const bounds = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(bounds.width * ratio);
  canvas.height = Math.round(bounds.height * ratio);
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, bounds.width, bounds.height);
  if (!landmarks || !video.videoWidth || !video.videoHeight) return;

  const scale = Math.max(bounds.width / video.videoWidth, bounds.height / video.videoHeight);
  const offsetX = (bounds.width - video.videoWidth * scale) / 2;
  const offsetY = (bounds.height - video.videoHeight * scale) / 2;
  const point = (index) => ({
    x: landmarks[index].x * video.videoWidth * scale + offsetX,
    y: landmarks[index].y * video.videoHeight * scale + offsetY,
  });
  const connections = counter?.exerciseType === "squat"
    ? [[23, 25], [25, 27], [24, 26], [26, 28]]
    : [[11, 13], [13, 15], [12, 14], [14, 16]];
  const trackedLandmarks = new Set(connections.flat());
  context.lineWidth = 3;
  context.strokeStyle = "#69f0d0";
  context.fillStyle = "#ffffff";
  for (const [start, end] of connections) {
    if ((landmarks[start]?.visibility ?? 0) <= 0.6 || (landmarks[end]?.visibility ?? 0) <= 0.6) continue;
    const a = point(start);
    const b = point(end);
    context.beginPath();
    context.moveTo(a.x, a.y);
    context.lineTo(b.x, b.y);
    context.stroke();
  }
  for (const index of trackedLandmarks) {
    const landmark = landmarks[index];
    if ((landmark.visibility ?? 0) <= 0.6) continue;
    const x = landmark.x * video.videoWidth * scale + offsetX;
    const y = landmark.y * video.videoHeight * scale + offsetY;
    context.beginPath();
    context.arc(x, y, 4, 0, Math.PI * 2);
    context.fill();
  }
}

function processFrame() {
  if (!cameraStream) return;
  if (!poseLandmarker || elements.video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    animationFrame = requestAnimationFrame(processFrame);
    return;
  }
  if (elements.video.currentTime !== lastVideoTime) {
    lastVideoTime = elements.video.currentTime;
    const result = poseLandmarker.detectForVideo(elements.video, performance.now());
    const landmarks = result.landmarks?.[0];
    drawSkeleton(landmarks);
    if (landmarks && counter) {
      const state = counter.update(result.worldLandmarks?.[0] || landmarks);
      setRepValue(state.repCount);
      const isSquat = counter.exerciseType === "squat";
      const stageText = isSquat
        ? (state.stage === "up" ? "Stand tall" : "Lower into the squat")
        : (state.stage === "up" ? "Curl complete · extend your arm" : "Arm extended · curl up");
      const visibilityHint = isSquat
        ? "Keep your hip, knee, and ankle visible; a side view helps."
        : "Keep your shoulder, elbow, and wrist visible.";
      elements.stage.textContent = state.angle === null
        ? `${visibilityHint} Move into view.`
        : `${stageText} · Joint angle ${Math.round(state.angle)}°`;
    } else {
      elements.stage.textContent = "Move into view to begin counting";
    }
  }
  animationFrame = requestAnimationFrame(processFrame);
}

function stopCamera() {
  cameraGeneration += 1;
  if (animationFrame !== null) cancelAnimationFrame(animationFrame);
  animationFrame = null;
  if (cameraStream) {
    for (const track of cameraStream.getTracks()) track.stop();
    cameraStream = null;
  }
  if (poseLandmarker) {
    poseLandmarker.close();
    poseLandmarker = null;
  }
  elements.video.srcObject = null;
  elements.cameraPanel.hidden = true;
  elements.cameraNote.textContent = cameraSupported()
    ? "Camera is off. Reps will be entered manually."
    : "Auto-counting is only supported for Squats and Bicep Curls. Use manual rep entry.";
  elements.canvas.getContext("2d").clearRect(0, 0, elements.canvas.width, elements.canvas.height);
}

async function startCamera() {
  if (!cameraSupported()) {
    elements.cameraToggle.checked = false;
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Camera access requires a secure connection (HTTPS or localhost) and a supported browser.");
  }
  const generation = ++cameraGeneration;
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: elements.cameraFacing?.value || "user" } },
    audio: false,
  });
  if (generation !== cameraGeneration) {
    for (const track of stream.getTracks()) track.stop();
    return;
  }
  cameraStream = stream;
  elements.video.srcObject = stream;
  await elements.video.play();

  const { FilesetResolver, PoseLandmarker } = await import(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs"
  );
  if (generation !== cameraGeneration) return;
  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm",
  );
  const landmarker = await PoseLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    },
    runningMode: "VIDEO",
    numPoses: 1,
  });
  if (generation !== cameraGeneration) {
    landmarker.close();
    return;
  }
  poseLandmarker = landmarker;
  counter = new RepCounter(supportedExerciseType(selectedExercise.name));
  lastVideoTime = -1;
  elements.cameraPanel.hidden = false;
  elements.cameraNote.textContent = "Camera is on. Keep the exercise joints visible in the frame.";
  elements.stage.textContent = "Move into view to begin counting";
  elements.saveStatus.textContent = "";
  animationFrame = requestAnimationFrame(processFrame);
}

elements.exercise.addEventListener("change", () => {
  selectedExercise = exercises.find((exercise) => exercise.id === Number(elements.exercise.value)) || null;
  counter = null;
  setRepValue(0);
  showExerciseDetails();
  if (elements.cameraToggle.checked && cameraSupported()) {
    counter = new RepCounter(supportedExerciseType(selectedExercise.name));
  }
});
elements.cameraToggle.addEventListener("change", async () => {
  if (elements.cameraToggle.checked) {
    try {
      await startCamera();
    } catch (error) {
      stopCamera();
      elements.cameraToggle.checked = false;
      elements.cameraNote.textContent = error.message;
    }
  } else {
    stopCamera();
  }
});
elements.cameraFacing?.addEventListener("change", async () => {
  if (!elements.cameraToggle.checked) return;
  stopCamera();
  try {
    await startCamera();
  } catch (error) {
    stopCamera();
    elements.cameraToggle.checked = false;
    elements.cameraNote.textContent = error.message;
  }
});
elements.decrement.addEventListener("click", () => setRepValue(Number(elements.reps.value) - 1, true));
elements.increment.addEventListener("click", () => setRepValue(Number(elements.reps.value) + 1, true));
elements.reps.addEventListener("input", () => setRepValue(elements.reps.value, true));
elements.reps.addEventListener("change", () => setRepValue(elements.reps.value, true));
elements.save.addEventListener("click", async () => {
  elements.save.disabled = true;
  elements.saveStatus.classList.remove("error");
  elements.saveStatus.textContent = "Saving…";
  try {
    if (!selectedExercise) throw new Error("Choose an exercise before saving.");
    const reps = Number(elements.reps.value);
    if (!Number.isInteger(reps) || reps < 0 || reps > 10000) {
      throw new Error("Enter a whole number of reps from 0 to 10000.");
    }
    const response = await fetch("/api/workout-logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        exercise_id: selectedExercise.id,
        reps_completed: reps,
        tracking_mode: elements.cameraToggle.checked ? "camera_auto" : "manual",
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not save this set.");
    elements.saveStatus.textContent = `Saved ${data.reps_completed} reps of ${data.exercise_name}.`;
  } catch (error) {
    elements.saveStatus.classList.add("error");
    elements.saveStatus.textContent = error.message;
  } finally {
    elements.save.disabled = false;
  }
});
window.addEventListener("pagehide", stopCamera);

loadPlan().catch((error) => {
  elements.pageStatus.textContent = error.message;
  elements.pageStatus.classList.add("error-message");
});
