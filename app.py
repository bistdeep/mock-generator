from flask import Flask, jsonify, request, render_template, send_file
import requests
import os
import re
import subprocess
import hashlib
import csv
import io 

app = Flask(__name__)

GITHUB_API = "https://api.github.com/repos/iitmbsc-student-projects/gate-da/contents"
RAW_BASE = "https://raw.githubusercontent.com/iitmbsc-student-projects/gate-da/master"

OUTPUT_MD = "output/mock.md"
OUTPUT_PDF = "output/mock.pdf"


# Extract Question and Answer
def extract_ques_ans(md_text):
    parts = md_text.split('---', 2)
    if len(parts) < 3:
        return {"question": "", "answer": ""}

    body = parts[2]

    # Question = everything before first callout
    question = body.split(':::', 1)[0].strip()

    # Regex to extract ONLY the Answer callout
    pattern = r':::\s*\{\.callout-note\s+title="Answer".*?\}\s*(.*?)\s*:::'
    match = re.search(pattern, body, re.DOTALL)

    answer = match.group(1).strip() if match else ""

    return {
        "question": question,
        "answer": answer
    }



# Handle Questions with Images 
def fix_image_paths(md, subject):
    base = f"https://raw.githubusercontent.com/iitmbsc-student-projects/gate-da/master/{subject}/bank/"
    
    # Replace markdown image paths
    pattern = r'!\[(.*?)\]\((.*?)\)'
    
    def repl(match):
        alt, path = match.groups()
        if path.startswith("http"):
            return match.group(0)
        return f"![{alt}]({base}{path})"

    return re.sub(pattern, repl, md)


# Handle SVG
def handle_svg_images(md):
    os.makedirs("output/images", exist_ok=True)

    def repl(match):
        alt, url = match.groups()
        if not url.endswith(".svg"):
            return match.group(0)

        # Unique filename
        name = hashlib.md5(url.encode()).hexdigest()
        svg_path = f"output/images/{name}.svg"
        png_path = f"output/images/{name}.png"

        # Download SVG
        if not os.path.exists(svg_path):
            r = requests.get(url)
            with open(svg_path, "wb") as f:
                f.write(r.content)

        # Convert to PNG
        if not os.path.exists(png_path):
            subprocess.run([
                "rsvg-convert", svg_path,
                "-o", png_path
            ], check=True)

        return f"![{alt}]({png_path})"

    return re.sub(r'!\[(.*?)\]\((.*?)\)', repl, md)


# Filename
def safe_filename(name):
    name = name.strip()
    name = re.sub(r"[^\w\-]", "_", name)  # keep a-z A-Z 0-9 _ -
    return name or "mock"

############### API Setup ################

# Home 
@app.route("/")
def index():
    return render_template("index.html")

# Get Subjects
@app.route("/subjects")
def get_subjects():
    r = requests.get(GITHUB_API)
    data = r.json()

    subjects = [
        item["name"]
        for item in data
        if item["type"] == "dir"
    ]
    return jsonify(subjects)


# Get Questions for Subject
@app.route("/questions/<subject>")
def get_questions(subject):
    url = f"{GITHUB_API}/{subject}/bank"
    r = requests.get(url)

    questions = [
        f["name"].replace(".md", "")
        for f in r.json()
        if f["name"].startswith("question-")
    ]
    return jsonify(questions)


# Extract Question Markdown 
@app.route("/extract", methods=["POST"])
def extract():
    data = request.json
    subject = data["subject"]
    qid = data["question"]

    raw_url = f"{RAW_BASE}/{subject}/bank/{qid}.md"
    md = requests.get(raw_url).text

    # Extract Q&A
    qa = extract_ques_ans(md)

    # Fix images & SVGs
    question = fix_image_paths(qa["question"], subject)
    question = handle_svg_images(question)

    answer = fix_image_paths(qa["answer"], subject)
    answer = handle_svg_images(answer)

    return jsonify({
        "question": question,
        "answer": answer
    })



# Export PDF 
@app.route("/export", methods=["POST"])
def export():
    try:
        data = request.get_json()
        if not data or "markdown" not in data:
            return jsonify({"error": "No markdown received"}), 400

        markdown = data["markdown"]
        filename = safe_filename(data.get("filename", "mock"))

        os.makedirs("output", exist_ok=True)

        md_path = os.path.join("output", f"{filename}.md")
        pdf_path = os.path.join("output", f"{filename}.pdf")

        # ✅ WRITE markdown to file (THIS WAS MISSING)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        # ✅ SAFE pandoc execution
        cmd = [
            "pandoc",
            md_path,
            "-o",
            pdf_path,
            "--pdf-engine=xelatex"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("PANDOC STDOUT:\n", result.stdout)
            print("PANDOC STDERR:\n", result.stderr)
            return jsonify({"error": "Pandoc failed"}), 500

        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF not created"}), 500

        return send_file(pdf_path, as_attachment=True)

    except Exception as e:
        print("EXPORT ERROR:", e)
        return jsonify({"error": str(e)}), 500


# Upload CSV and Generate Mock Test 
@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    if "file" not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Invalid file type"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)

        # Validate headers strictly
        if not reader.fieldnames or "subject" not in reader.fieldnames or "q_ids" not in reader.fieldnames:
            return jsonify({
                "error": "CSV must have headers: subject,q_ids"
            }), 400


        title = request.form.get("title", "GATE Mock Test").strip() or "GATE Mock Test"

        buffer = f"""\\begin{{center}}\n\\LARGE\\textbf{{{title}}}\n\\end{{center}}\n\n\\vspace{{1cm}}\n\n---\n\n"""

        current_subject = None
        q_counter = 1
        questions_added = 0

        for row in reader:
            subject = row["subject"].strip()
            q_ids_raw = row["q_ids"].strip()

            if not subject or not q_ids_raw:
                continue

            # New subject section
            if subject != current_subject:
                buffer += f"## Subject: {subject.replace('_', ' ').title()}\n\n"
                current_subject = subject
                q_counter = 1

            q_ids = q_ids_raw.split()

            for q in q_ids:
                qid = f"question-{int(q):03d}"
                raw_url = f"{RAW_BASE}/{subject}/bank/{qid}.md"

                r = requests.get(raw_url)
                if r.status_code != 200:
                    print("FAILED FETCH:", raw_url)
                    continue

                qa = extract_ques_ans(r.text)

                question = handle_svg_images(
                    fix_image_paths(qa["question"], subject)
                )
                answer = handle_svg_images(
                    fix_image_paths(qa["answer"], subject)
                )

                buffer += f"### Question {q_counter}\n\n{question}\n\n"

                if answer.strip():
                    buffer += f"#### Answer\n\n{answer}\n\n"

                q_counter += 1
                questions_added += 1

        if questions_added == 0:
            return jsonify({
                "error": "No questions could be generated. Check subject names and question IDs."
            }), 400

        return jsonify({"markdown": buffer})

    except Exception as e:
        print("CSV ERROR:", e)
        return jsonify({"error": str(e)}), 500


############### Run App ################

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

