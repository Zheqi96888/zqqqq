from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid

app = Flask(__name__)
DOWNLOAD_FOLDER = "/tmp/downloads"
COOKIE_FILE = "cookies.txt"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube to MP3</title>
    <style>
        body {
            background: #121212;
            color: #fff;
            font-family: Arial, sans-serif;
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
        }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border-radius: 6px;
            border: none;
            font-size: 16px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: red;
            color: white;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }
        #status {
            margin-top: 20px;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
        }
    </style>
</head>
<body>
    <h2>YouTube → MP3 Converter</h2>
    <input id="url" placeholder="Paste YouTube URL">
    <button onclick="convert()">Convert to MP3</button>
    <div id="status"></div>

    <script>
        async function convert() {
            const url = document.getElementById("url").value;
            const status = document.getElementById("status");
            status.textContent = "🔄 Converting...";
            status.style.background = "#222";

            const res = await fetch("/convert", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url })
            });

            const data = await res.json();
            if (res.ok) {
                status.textContent = "✅ Downloading...";
                status.style.background = "#050";
                window.location.href = `/download/${data.filename}`;
            } else {
                status.textContent = "❌ Error: " + data.error;
                status.style.background = "#500";
            }
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        filename = str(uuid.uuid4())
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        ydl_opts = {
            "format": "bestaudio/best",
            "extractaudio": True,
            "audioformat": "mp3",
            "audioquality": 320,
            "outtmpl": filepath + ".%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "cookiefile": "cookies.txt",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({"filename": filename + ".mp3"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=False)
