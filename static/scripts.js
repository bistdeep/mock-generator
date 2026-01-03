let buffer = "# GATE Mock Test | IIT Madras BS\n\n---\n\n";
let qCounter = 1;

// Define allowed subjects
const allowedSubjects = [
  "ai",
  "calculus",
  "dbms",
  "linear_algebra",
  "machine_learning",
  "pdsa",
  "prob_stats",
];

fetch("/subjects")
  .then((r) => r.json())
  .then((data) => {
    let s = document.getElementById("subject");
    // Filter to only show allowed subjects
    data
      .filter((sub) => allowedSubjects.includes(sub))
      .forEach((sub) => {
        let o = document.createElement("option");
        o.value = sub;
        o.text = sub;
        s.add(o);
      });
  });

function loadQuestions() {
  let sub = subject.value;
  fetch(`/questions/${sub}`)
    .then((r) => r.json())
    .then((data) => {
      questions.innerHTML = "";
      data.forEach((q) => {
        let o = document.createElement("option");
        o.value = q;
        o.text = q;
        questions.add(o);
      });
    });
}

function addQuestion() {
  fetch("/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject: subject.value,
      question: questions.value,
    }),
  })
    .then((r) => r.json())
    .then((data) => {
      buffer += `## Question ${qCounter}\n\n${data.content}\n\n---\n\n`;
      qCounter++;
      preview.value = buffer;
    });
}

function exportPDF() {
  fetch("/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown: buffer }),
  })
    .then((r) => {
      if (!r.ok) {
        return r.json().then((err) => {
          throw new Error(err.error || "Failed to export PDF");
        });
      }
      return r.blob();
    })
    .then((blob) => {
      let url = window.URL.createObjectURL(blob);
      let a = document.createElement("a");
      a.href = url;
      a.download = "mock.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    })
    .catch((error) => {
      alert("Error: " + error.message);
    });
}
