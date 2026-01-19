let buffer = "";
let qCounter = 1;
let currentSubject = null;

/*
  Functions 
*/

// Initialise buffer with title
function initBuffer() {
  const titleInput = document.getElementById("mockTitle");
  const title = titleInput.value.trim() || "GATE Mock Test";

  buffer = `\\begin{center}
\\LARGE\\textbf{${title}}
\\end{center}

\\vspace{1cm}

---\n\n`;

  qCounter = 1;
  preview.value = buffer;
}

function getSubjectLabel(code) {
  return SUBJECT_LABELS[code] || code.replace(/_/g, " ");
}

function exportPDF() {
  const titleInput = document.getElementById("mockTitle");
  const title =
    titleInput && titleInput.value.trim()
      ? titleInput.value.trim()
      : "GATE_Mock_Test";

  const safeFilename = title.replace(/\s+/g, "_");

  fetch("/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      markdown: buffer,
      filename: safeFilename,
    }),
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
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeFilename}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    })
    .catch((error) => {
      alert("Error: " + error.message);
    });
}

function downloadMarkdown() {
  if (!buffer || buffer.trim() === "") {
    alert("No content to download.");
    return;
  }

  const titleInput = document.getElementById("mockTitle");
  const title =
    titleInput && titleInput.value.trim()
      ? titleInput.value.trim()
      : "GATE_Mock_Test";

  const safeFilename = title.replace(/[^\w\-]+/g, "_");

  const blob = new Blob([buffer], { type: "text/markdown;charset=utf-8;" });
  const url = window.URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = `${safeFilename}.md`;
  document.body.appendChild(a);
  a.click();

  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

function uploadCSV() {
  const fileInput = document.getElementById("csvFile");
  if (!fileInput.files.length) {
    alert("Please select a CSV file");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("title", document.getElementById("mockTitle").value);

  showLoader();

  fetch("/upload-csv", {
    method: "POST",
    body: formData,
  })
    .then((r) => r.json())
    .then((data) => {
      hideLoader();

      if (data.error) {
        alert(data.error);
        return;
      }

      // Initialize buffer with title if empty
      if (!buffer) {
        initBuffer();
      }

      buffer = data.markdown;
      preview.value = buffer;
    })
    .catch(() => {
      hideLoader();
      alert("Failed to generate mock from CSV");
    });
}

// Save changes made in the preview textarea to the buffer
function saveChanges() {
  const preview = document.getElementById("preview");

  buffer = preview.value;

  alert("Changes saved successfully!");
}

// Update file name display when file is selected
function updateFileName(input) {
  const label = input.nextElementSibling;
  const fileNameSpan = label.querySelector(".file-name");

  if (input.files && input.files.length > 0) {
    fileNameSpan.textContent = input.files[0].name;
    label.classList.add("has-file");
  } else {
    fileNameSpan.textContent = "Choose a CSV file...";
    label.classList.remove("has-file");
  }
}

// Loader Animation
function showLoader() {
  document.getElementById("loadingOverlay").classList.remove("hidden");
}

function hideLoader() {
  document.getElementById("loadingOverlay").classList.add("hidden");
}
