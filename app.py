import os
from flask import Flask, render_template, request, jsonify
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.ai.formrecognizer import DocumentAnalysisClient

try:
    import azure.cognitiveservices.speech as speechsdk  # type: ignore
except ImportError:
    speechsdk = None


"""
EduVoice App
-------------

This Flask application provides a simple interface for interacting with several Azure AI
services, including Azure AI Search, Speech Services, and Document Intelligence (also
known as Form Recognizer). The app exposes REST endpoints for searching an index,
transcribing speech from an uploaded audio file, and extracting text from uploaded
documents.

To configure the application, set the following environment variables in your
deployment environment (for example, in Azure App Service settings or a .env file
when running locally):

* ``SEARCH_ENDPOINT`` – The endpoint URI of your Azure AI Search service.
* ``SEARCH_API_KEY`` – An admin or query API key for your search service.
* ``SEARCH_INDEX_NAME`` – The name of the index you want to query.
* ``SPEECH_KEY`` – The subscription key for your Azure Speech resource.
* ``SPEECH_REGION`` – The region associated with your Speech resource (for example, ``eastus``).
* ``FORM_RECOGNIZER_ENDPOINT`` – The endpoint for your Document Intelligence (Form Recognizer) resource.
* ``FORM_RECOGNIZER_API_KEY`` – The API key for your Document Intelligence resource.

The application is intentionally light‐weight and intended as a starting point. For a
production deployment you should handle authentication more securely (for
example, use an Azure Active Directory token service rather than embedding
subscription keys in client‑side code) and validate inputs carefully.
"""


def create_app() -> Flask:
    """Factory to create and configure the Flask app."""
    app = Flask(__name__)

    # Load configuration from environment variables
    search_endpoint = os.environ.get("SEARCH_ENDPOINT")
    search_key = os.environ.get("SEARCH_API_KEY")
    search_index_name = os.environ.get("SEARCH_INDEX_NAME")
    speech_key = os.environ.get("SPEECH_KEY")
    speech_region = os.environ.get("SPEECH_REGION")
    form_endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT")
    form_key = os.environ.get("FORM_RECOGNIZER_API_KEY")

    # Initialise Azure clients lazily. If any required configuration is missing,
    # the corresponding client is left as ``None`` and the route handlers will
    # respond with an error.
    search_client = None
    if search_endpoint and search_key and search_index_name:
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=search_index_name,
            credential=AzureKeyCredential(search_key),
        )

    document_client = None
    if form_endpoint and form_key:
        document_client = DocumentAnalysisClient(
            form_endpoint, AzureKeyCredential(form_key)
        )

    @app.route("/")
    def index():
        """Render the main HTML page."""
        return render_template("index.html")

    @app.route("/search", methods=["POST"])
    def search():
        """Search the configured Azure AI Search index and return the top results."""
        if search_client is None:
            return jsonify({"error": "Search service is not configured."}), 500
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"error": "No query provided."}), 400
        try:
            results = search_client.search(query, top=5)
            items = []
            for result in results:
                # Each result is a SearchResultProxy which behaves like a dict.
                item = {}
                for key, value in result.items():
                    # Exclude the search score unless explicitly desired
                    if key != "@search.score":
                        item[key] = value
                item["score"] = result.get("@search.score", None)
                items.append(item)
            return jsonify({"results": items})
        except Exception as exc:  # pragma: no cover - network exception handling
            return jsonify({"error": str(exc)}), 500

    @app.route("/analyze-document", methods=["POST"])
    def analyze_document():
        """Analyze an uploaded document using Azure Document Intelligence."""
        if document_client is None:
            return jsonify({"error": "Document intelligence service is not configured."}), 500
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded."}), 400
        file = request.files["file"]
        try:
            poller = document_client.begin_analyze_document("prebuilt-layout", file)
            result = poller.result()
            lines = [line.content for page in result.pages for line in page.lines]
            return jsonify({"text": "\n".join(lines)})
        except Exception as exc:  # pragma: no cover - network exception handling
            return jsonify({"error": str(exc)}), 500

    @app.route("/speech-to-text", methods=["POST"])
    def speech_to_text():
        """Transcribe an uploaded audio file using Azure Speech Services."""
        if speechsdk is None:
            return jsonify({"error": "Azure Speech SDK is not installed."}), 500
        if not (speech_key and speech_region):
            return jsonify({"error": "Speech service is not configured."}), 500
        if "file" not in request.files:
            return jsonify({"error": "No audio file uploaded."}), 400
        audio_file = request.files["file"]
        # Save audio temporarily; ensure the filename is safe to use in the container
        temp_path = "/tmp/uploaded_audio.wav"
        audio_file.save(temp_path)
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, region=speech_region
            )
            audio_input = speechsdk.AudioConfig(filename=temp_path)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, audio_config=audio_input
            )
            result = recognizer.recognize_once()
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return jsonify({"text": result.text})
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return jsonify({"error": "No speech could be recognized."}), 400
            else:
                return jsonify({"error": "Speech recognition error."}), 500
        except Exception as exc:  # pragma: no cover - network exception handling
            return jsonify({"error": str(exc)}), 500

    return app


# Expose a module-level WSGI application for Gunicorn or other WSGI servers.
# When imported, ``application`` will hold the Flask app instance. Azure App
# Service and other hosting environments look for this variable by default.
application = create_app()

if __name__ == "__main__":
    # When running via ``python app.py`` locally, start the built‑in server.
    application.run(
        host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True
    )