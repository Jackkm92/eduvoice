async function runSearch() {
  const q = document.getElementById("query").value;
  const resultsDiv = document.getElementById("results");

  resultsDiv.innerHTML = "Searching...";

  const res = await fetch("/search", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({query: q})
  });

  const data = await res.json();
  resultsDiv.innerHTML = "";

  if (!data.results || data.results.length === 0) {
    resultsDiv.innerHTML = "<p>No results found.</p>";
    return;
  }

  data.results.forEach(r => {
    resultsDiv.innerHTML += `
      <div class="result">
        <h3>${r.title}</h3>
        <p>${r.content}</p>
      </div>
    `;
  });
}

// Browser speech recognition (student-friendly)
function startMic() {
  if (!('webkitSpeechRecognition' in window)) {
    alert("Speech recognition not supported in this browser.");
    return;
  }

  const recognition = new webkitSpeechRecognition();
  recognition.lang = "en-US";
  recognition.start();

  recognition.onresult = (event) => {
    document.getElementById("query").value = event.results[0][0].transcript;
  };
}
