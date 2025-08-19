async function fetchState() {
  try {
    const res = await fetch('/get_sentence');
    const data = await res.json();

    document.getElementById("current-letter").innerText = data.letter || "??";
    document.getElementById("sentence").value = data.sentence || "";

    // Update confidence & stability bars
    document.getElementById("conf-bar").style.width = `${Math.floor(data.confidence * 100)}%`;
    document.getElementById("stab-bar").style.width = `${Math.floor(data.stability * 100)}%`;

    document.getElementById("conf-val").innerText = `${Math.floor(data.confidence * 100)}%`;
    document.getElementById("stab-val").innerText = `${Math.floor(data.stability * 100)}%`;

  } catch (err) {
    console.error("Error fetching state:", err);
  }
}

setInterval(fetchState, 300);

// Button actions
document.getElementById("btn-clear").addEventListener("click", () => {
  fetch('/clear_sentence', { method: "POST" });
});

document.getElementById("btn-backspace").addEventListener("click", () => {
  fetch('/backspace', { method: "POST" });
});

document.getElementById("btn-space").addEventListener("click", () => {
  fetch('/commit_space', { method: "POST" });
});

// ✅ Keyboard backspace support (ignore when typing in input/textarea)
document.addEventListener("keydown", (e) => {
  const active = document.activeElement;
  const isTyping = active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA");

  if (e.key === "Backspace" && !isTyping) {
    fetch('/backspace', { method: "POST" });
    e.preventDefault(); // block default only outside inputs
  }
});

// ✅ Speak button
document.getElementById("btn-speak").addEventListener("click", () => {
  const sentence = document.getElementById("sentence").value; // textarea uses .value
  if (sentence.trim().length > 0) {
    const utterance = new SpeechSynthesisUtterance(sentence);
    
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name === "Google UK English Female");
    if (preferred) {
      utterance.voice = preferred;
    }

    utterance.rate = 1;
    utterance.pitch = 1;
    
    window.speechSynthesis.speak(utterance);
  }
});


/* =======================
   Search in Gesture Gallery
   ======================= */
const searchInput = document.getElementById("searchInput");
const galleryGrid = document.getElementById("galleryGrid");

if (searchInput && galleryGrid) {
  const cards = galleryGrid.getElementsByClassName("card");

  // Use 'input' so it reacts to typing, backspace, delete, paste etc.
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase();

    Array.from(cards).forEach(card => {
      const letter = card.getAttribute("data-letter").toLowerCase();
      card.style.display = letter.includes(query) ? "" : "none";
    });
  });
}
