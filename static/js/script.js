const video = document.getElementById("video");
const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d");

// Send frame to server for prediction
async function sendFrame() {
  if (video.readyState === video.HAVE_ENOUGH_DATA) {
    const videoWidth = video.videoWidth;
    const videoHeight = video.videoHeight;

    canvas.width = videoWidth;
    canvas.height = videoHeight;
    ctx.drawImage(video, 0, 0, videoWidth, videoHeight);

    const imageData = canvas.toDataURL("image/jpeg");

    try {
      const res = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: imageData })
      });

      const data = await res.json();
      if (!data.error) {
        // Update UI
        document.getElementById("current-letter").innerText = data.letter || "??";
        document.getElementById("sentence").value = data.sentence || "";
        document.getElementById("conf-bar").style.width = Math.floor(data.confidence * 100) + "%";
        document.getElementById("conf-val").innerText = Math.floor(data.confidence * 100) + "%";
        document.getElementById("stab-bar").style.width = Math.floor(data.stability * 100) + "%";
        document.getElementById("stab-val").innerText = Math.floor(data.stability * 100) + "%";
      }
    } catch (err) {
      console.error("Prediction error:", err);
    }
  }
  requestAnimationFrame(sendFrame);
}

// Initialize camera
async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    video.play();
    sendFrame();
  } catch (err) {
    console.error("Cannot access camera:", err);
  }
}

initCamera();

// =======================
// Button actions
// =======================
document.getElementById("btn-clear").addEventListener("click", () => {
  fetch('/clear_sentence', { method: "POST" });
});
document.getElementById("btn-backspace").addEventListener("click", () => {
  fetch('/backspace', { method: "POST" });
});
document.getElementById("btn-space").addEventListener("click", () => {
  fetch('/commit_space', { method: "POST" });
});

// Keyboard backspace support (ignore when typing in input/textarea)
document.addEventListener("keydown", (e) => {
  const active = document.activeElement;
  const isTyping = active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA");

  if (e.key === "Backspace" && !isTyping) {
    fetch('/backspace', { method: "POST" });
    e.preventDefault();
  }
});

// Speak button
document.getElementById("btn-speak").addEventListener("click", () => {
  const sentence = document.getElementById("sentence").value;
  if (sentence.trim().length > 0) {
    const utterance = new SpeechSynthesisUtterance(sentence);
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name === "Google UK English Female");
    if (preferred) utterance.voice = preferred;
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }
});

// =======================
// Search in Gesture Gallery
// =======================
const searchInput = document.getElementById("searchInput");
const galleryGrid = document.getElementById("galleryGrid");
if (searchInput && galleryGrid) {
  const cards = galleryGrid.getElementsByClassName("card");
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase();
    Array.from(cards).forEach(card => {
      const letter = card.getAttribute("data-letter").toLowerCase();
      card.style.display = letter.includes(query) ? "" : "none";
    });
  });
}
