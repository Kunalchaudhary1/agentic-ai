from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from flask import Flask, request, render_template, jsonify
import os
import threading
import google.generativeai as genai
import time

app = Flask(__name__)
CONTENT_FILE = "website_content.txt"
SCRAPE_STATUS = {"status": "idle", "current": "", "error": ""}
SCRAPE_STOP = {"stop": False}

GENAI_API_KEY = "AIzaSyCVIk_R0b_SRDHRUNpHCCmj45pbEfB8yTk"
genai.configure(api_key=GENAI_API_KEY)

def is_internal_link(link, base_netloc):
    parsed = urlparse(link)
    # Only allow http/https or empty scheme (relative links)
    if parsed.scheme not in ("", "http", "https"):
        return False
    return (parsed.netloc == "" or parsed.netloc == base_netloc)

def crawl_website_selenium(start_url, output_file, max_pages=20):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    visited = set()
    to_visit = [start_url]
    base_netloc = urlparse(start_url).netloc
    all_text = []
    SCRAPE_STATUS["status"] = "running"
    SCRAPE_STATUS["error"] = ""
    SCRAPE_STOP["stop"] = False
    try:
        while to_visit and len(visited) < max_pages:
            if SCRAPE_STOP["stop"]:
                SCRAPE_STATUS["status"] = "stopped"
                SCRAPE_STATUS["current"] = ""
                break
            url = to_visit.pop(0)
            SCRAPE_STATUS["current"] = url
            if url in visited:
                continue
            try:
                driver.get(url)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                all_text.append(f"URL: {url}\n{text}\n")
                visited.add(url)
                for a in soup.find_all("a", href=True):
                    link = urljoin(url, a["href"])
                    # Skip javascript:, mailto:, tel:, etc.
                    if not link.startswith("http") and not link.startswith("/"):
                        continue
                    if is_internal_link(link, base_netloc) and link not in visited and link not in to_visit:
                        to_visit.append(link)
            except Exception as e:
                SCRAPE_STATUS["error"] = f"Failed to crawl {url}: {e}"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_text))
        if not SCRAPE_STOP["stop"]:
            SCRAPE_STATUS["status"] = "completed"
        SCRAPE_STATUS["current"] = ""
    except Exception as e:
        SCRAPE_STATUS["status"] = "error"
        SCRAPE_STATUS["error"] = str(e)
        SCRAPE_STATUS["current"] = ""
    finally:
        driver.quit()

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        url = request.form.get("url")
        if url and url.strip().startswith("http"):
            threading.Thread(target=crawl_website_selenium, args=(url.strip(), CONTENT_FILE, 20), daemon=True).start()
            message = "Scraping started!"
        else:
            message = "Please enter a valid URL."
    return render_template("index.html", message=message)

@app.route("/status")
def status():
    return jsonify(SCRAPE_STATUS)

@app.route("/stop", methods=["POST"])
def stop():
    SCRAPE_STOP["stop"] = True
    SCRAPE_STATUS["status"] = "stopped"
    SCRAPE_STATUS["current"] = ""
    return jsonify({"stopped": True})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    if not os.path.exists(CONTENT_FILE):
        return jsonify({"answer": "No website content found. Please scrape a website first."})
    with open(CONTENT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    prompt = f"Website content:\n{content}\n\nQuestion: {question}"
    try:

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        answer = response.text
    except Exception as e:
        answer = f"Error: {str(e)}"
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)