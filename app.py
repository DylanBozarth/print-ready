import os
import io
import requests
from flask import Flask, request, send_file, render_template_string
from printready import scrape_tags, save_pdf

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Print Ready</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f4f5;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }

    .card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
      padding: 48px 40px;
      width: 100%;
      max-width: 540px;
    }

    h1 {
      font-size: 1.6rem;
      font-weight: 700;
      margin-bottom: 8px;
      color: #18181b;
    }

    p.subtitle {
      color: #71717a;
      font-size: 0.95rem;
      margin-bottom: 32px;
    }

    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      color: #3f3f46;
      margin-bottom: 6px;
    }

    input[type="url"] {
      width: 100%;
      padding: 10px 14px;
      border: 1px solid #d4d4d8;
      border-radius: 8px;
      font-size: 0.95rem;
      color: #18181b;
      outline: none;
      transition: border-color 0.2s;
    }

    input[type="url"]:focus {
      border-color: #6366f1;
    }

    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 16px;
    }

    .checkbox-row input { width: 16px; height: 16px; cursor: pointer; }
    .checkbox-row label { margin: 0; font-weight: 500; cursor: pointer; }

    button {
      margin-top: 28px;
      width: 100%;
      padding: 12px;
      background: #6366f1;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }

    button:hover { background: #4f46e5; }
    button:disabled { background: #a5b4fc; cursor: not-allowed; }

    .error {
      margin-top: 20px;
      padding: 12px 16px;
      background: #fef2f2;
      border: 1px solid #fca5a5;
      border-radius: 8px;
      color: #b91c1c;
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Print Ready</h1>
    <p class="subtitle">Paste a URL to scrape the page and download it as a clean PDF.</p>

    <form method="POST" action="/scrape" id="form">
      <label for="url">Page URL</label>
      <input type="url" id="url" name="url" placeholder="https://example.com/article"
             value="{{ url or '' }}" required autofocus />

      <div class="checkbox-row">
        <input type="checkbox" id="images" name="images" {{ 'checked' if images else '' }} />
        <label for="images">Include images (greyscale)</label>
      </div>

      <button type="submit" id="btn">Generate PDF</button>
    </form>

    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
  </div>

  <script>
    document.getElementById("form").addEventListener("submit", function(e) {
      const btn = document.getElementById("btn");
      const input = document.getElementById("url");
      btn.disabled = true;
      btn.textContent = "Generating…";

      // Poll until the browser starts downloading, then reset
      const interval = setInterval(() => {
        clearInterval(interval);
        btn.disabled = false;
        btn.textContent = "Generate PDF";
        input.value = "";
        input.focus();
      }, 3000);
    });
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/scrape", methods=["POST"])
def scrape():
    url = request.form.get("url", "").strip()
    include_images = "images" in request.form

    try:
        title, items = scrape_tags(url, include_images=include_images)
    except requests.exceptions.MissingSchema:
        return render_template_string(HTML, error=f"'{url}' is not a valid URL. Make sure it starts with http:// or https://", url=url, images=include_images)
    except requests.exceptions.ConnectionError:
        return render_template_string(HTML, error=f"Could not connect to '{url}'. Check the URL or your internet connection.", url=url, images=include_images)
    except requests.exceptions.HTTPError as e:
        return render_template_string(HTML, error=f"The page returned a {e.response.status_code} error. It may not be publicly accessible.", url=url, images=include_images)
    except requests.exceptions.Timeout:
        return render_template_string(HTML, error=f"The request timed out. The server may be slow or unreachable.", url=url, images=include_images)

    buf = io.BytesIO()
    save_pdf(items, buf)
    buf.seek(0)

    filename = f"{title}.pdf"
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
