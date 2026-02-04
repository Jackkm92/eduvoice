from flask import Flask, render_template, request, jsonify
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

app = Flask(__name__)

# --- Azure AI Search config ---
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
SEARCH_INDEX_NAME = os.getenv("SEARCH_INDEX_NAME")

search_client = None
if SEARCH_ENDPOINT and SEARCH_API_KEY and SEARCH_INDEX_NAME:
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_API_KEY)
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/search", methods=["POST"])
def search():
    if not search_client:
        return jsonify({"error": "Search service not configured"}), 500

    query = request.json.get("query")
    if not query:
        return jsonify({"results": []})

    results = []
    search_results = search_client.search(query, top=5)

    for r in search_results:
        results.append({
            "title": r.get("title", "Result"),
            "content": r.get("content", "")
        })

    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
