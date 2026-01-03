from flask import Flask, jsonify, request, render_template, send_file
import requests
import os
import re
import subprocess
import hashlib

app = Flask(__name__)

GITHUB_API = "https://api.github.com/repos/iitmbsc-student-projects/gate-da/contents"
RAW_BASE = "https://raw.githubusercontent.com/iitmbsc-student-projects/gate-da/master"

OUTPUT_MD = "output/mock.md"
OUTPUT_PDF = "output/mock.pdf"


# Extract Question 
def extract_question(md_text):
    parts = md_text.split('---', 2)
    if len(parts) < 3:
        return ""

    body = parts[2]
    question = body.split(':::', 1)[0]
    return question.strip()


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

    extracted = extract_question(md)
    extracted = fix_image_paths(extracted, subject)
    extracted = handle_svg_images(extracted)

    return jsonify({"content": extracted})


# Export PDF 
@app.route("/export", methods=["POST"])
def export():
    try:
        data = request.get_json()
        if not data or "markdown" not in data:
            return jsonify({"error": "No markdown received"}), 400

        markdown = data["markdown"]

        os.makedirs("output", exist_ok=True)

        with open(OUTPUT_MD, "w") as f:
            f.write(markdown)

        cmd = f"pandoc {OUTPUT_MD} -o {OUTPUT_PDF} --pdf-engine=xelatex"
        exit_code = os.system(cmd)

        if exit_code != 0:
            return jsonify({"error": "Pandoc failed"}), 500

        if not os.path.exists(OUTPUT_PDF):
            return jsonify({"error": "PDF not created"}), 500

        return send_file(OUTPUT_PDF, as_attachment=True)

    except Exception as e:
        print("EXPORT ERROR:", e)
        return jsonify({"error": str(e)}), 500




############### Run App ################

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

