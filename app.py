from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid

app = Flask(__name__)
# 🔥 关键：Render 项目根目录绝对路径，确保 cookies 被正确加载
COOKIE_FILE = "/opt/render/project/src/cookies.txt"
# 临时下载目录，容器内内存级存储，无需持久化
DOWNLOAD_FOLDER = "/tmp/downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 前端页面（适配手机/电脑，样式优化）
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube → MP3 Converter</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        body {
            background: #121212;
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            width: 100%;
            max-width: 600px;
        }
        h1 {
            text-align: center;
            color: #ff0000;
            margin-bottom: 30px;
            font-size: 2.5rem;
        }
        #url-input {
            width: 100%;
            padding: 16px;
            margin-bottom: 16px;
            border-radius: 12px;
            border: 2px solid #333;
            background: #1e1e1e;
            color: #fff;
            font-size: 1.2rem;
            outline: none;
            transition: border 0.2s;
        }
        #url-input:focus {
            border-color: #ff0000;
        }
        #convert-btn {
            width: 100%;
            padding: 16px;
            background: #ff0000;
            color: #fff;
            border: none;
            border-radius: 12px;
            font-size: 1.5rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            margin-bottom: 24px;
        }
        #convert-btn:hover {
            background: #cc0000;
        }
        #status {
            width: 100%;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            font-size: 1.2rem;
            display: none;
        }
        .loading {
            background: #1a1a3a;
            border: 1px solid #3333ff;
            color: #3333ff;
        }
        .success {
            background: #1a3a1a;
            border: 1px solid #33ff33;
            color: #33ff33;
        }
        .error {
            background: #3a1a1a;
            border: 1px solid #ff3333;
            color: #ff3333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>YouTube → MP3 转换器</h1>
        <input type="text" id="url-input" placeholder="粘贴 YouTube 链接...">
        <button id="convert-btn">转换为 MP3</button>
        <div id="status"></div>
    </div>

    <script>
        const urlInput = document.getElementById('url-input');
        const convertBtn = document.getElementById('convert-btn');
        const status = document.getElementById('status');

        convertBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) {
                status.textContent = "❌ 请输入有效的 YouTube 链接";
                status.className = "error";
                status.style.display = "block";
                return;
            }

            status.textContent = "🔄 转换中，请稍候...";
            status.className = "loading";
            status.style.display = "block";

            try {
                const res = await fetch('/convert', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "转换失败");

                status.textContent = `✅ 成功！正在下载：${data.title}`;
                status.className = "success";
                // 自动触发下载
                const a = document.createElement('a');
                a.href = `/download/${data.file_id}`;
                a.download = data.filename;
                a.click();
            } catch (err) {
                status.textContent = `❌ 错误：${err.message}`;
                status.className = "error";
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json
    url = data.get("url")
    
    if not url:
        return jsonify({"error": "请输入 YouTube 链接"}), 400

    # 🔥 强制校验 cookies 是否存在，避免静默失败
    if not os.path.exists(COOKIE_FILE):
        return jsonify({"error": f"❌ 未找到 Cookie 文件！路径：{COOKIE_FILE}"}), 500

    try:
        file_id = str(uuid.uuid4())
        outtmpl = f"{DOWNLOAD_FOLDER}/{file_id}.%(ext)s"

        # 🔥 核心修复：兼容性拉满的格式配置 + ffmpeg 转码兜底
        ydl_opts = {
            "format": "bestaudio/best",  # 自动匹配最佳可用音频，不限制格式
            "extractaudio": True,
            "audioformat": "mp3",
            "audioquality": "320",  # 强制 320K 高音质
            "outtmpl": outtmpl,
            "quiet": True,
            "noplaylist": True,
            "cookiefile": “cookies.txt",  # 加载 cookies 绕过机器人验证
            "no_warnings": True,
            # 🔥 兜底：强制用 ffmpeg 转码为 mp3，彻底解决格式不可用问题
            "postprocessor_args": ["-acodec", "libmp3lame", "-b:a", "320k"],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # 自动匹配最终 mp3 文件路径
            original_filename = ydl.prepare_filename(info)
            mp3_filename = original_filename.rsplit('.', 1)[0] + '.mp3'

        return jsonify({
            "title": info.get("title", "YouTube 音频"),
            "file_id": file_id,
            "filename": f"{info.get('title', '音频')}.mp3"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<file_id>")
def download(file_id):
    # 匹配对应的 mp3 文件
    for file in os.listdir(DOWNLOAD_FOLDER):
        if file.startswith(file_id) and file.endswith(".mp3"):
            file_path = os.path.join(DOWNLOAD_FOLDER, file)
            return send_file(file_path, as_attachment=True)
    return jsonify({"error": "文件未找到"}), 404

if __name__ == "__main__":
    # 🔥 适配 Render 端口，优先读取环境变量，默认 9000
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 9000)), debug=False)
