# Lecture Study Assistant

Lecture Study Assistant is a local-first Python application for helping university students turn lecture materials into exam-oriented study guides.

The application is being built incrementally. The current implementation provides
the persistent Course and Lecture Library, basic local material storage, and
traceable text extraction for PDF, DOCX, and PPTX materials.

## Current V1 scope

The current V1 slice supports:

- Creating and opening courses
- Creating and opening lectures within courses
- Viewing materials associated with a lecture
- Uploading PDF, DOCX, and PPTX files without overwriting existing files
- SQLite metadata for courses, lectures, and materials
- Stable local course and lecture directories
- Extracting content into page, slide, and ordered document sections
- Generating validated, source-traceable JSON study guides with an OpenAI provider
- Local OCR fallback for image-based PDF pages and PPTX slides

Planned next work includes:

- ReportLab PDF output from the canonical `Study_Guide.json` artifact

## Feature 3B: OCR / Image-Based Materials

PDF and PPTX extraction first uses their normal text extraction. OCR is used only
for pages or slides where no meaningful text was found and an image is present.
OCR results use the same `Document` and `Section` models, preserving the filename,
page or slide index, and an `extraction_method` of `ocr`. The existing AI generator
consumes these documents without needing to know whether content came from normal
extraction or OCR.

OCR runs locally through `pytesseract` and Pillow. On Windows, install the
Tesseract OCR application separately and make sure `tesseract.exe` is on `PATH`.
For example, the UB Mannheim Windows builds are a common installation option.
The Python package alone does not include the Tesseract executable.

OCR supports English (`eng`) and is intended for lecture screenshots and slides,
not research-grade recognition. Scanned pages with unreadable content produce a
clear extraction error; the application never invents text or sends material to
an OCR cloud service.

The following are intentionally out of scope for V1:

- Telegram integration
- University website integration
- Autonomous agents
- Authentication
- Cloud deployment
- Vector databases and RAG
- Advanced scheduling

PDF output, OCR, and exam planning are not implemented yet.

## Project structure

```text
.
├── app/                 Application package and Streamlit entry point
│   ├── ai/              Provider, schemas, prompts, and guide generation
│   ├── pdf/             PDF generation placeholder
│   ├── processors/      Material parsing placeholder
│   ├── services/        Application services
│   ├── storage/         SQLite and filesystem storage
│   └── ui/              Streamlit views
├── config/              Environment-backed settings
├── data/                Local runtime data (ignored except .gitkeep)
├── .env.example         Local configuration template
├── .gitignore
├── README.md
└── requirements.txt
```

Each feature area is kept separate so future implementation can be added without putting processing, storage, and presentation logic into the Streamlit entry point.

## Setup

Python 3.10 or newer is recommended.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

The requirements install the project itself in editable mode, which keeps the
package-qualified imports working when Streamlit runs `app/main.py` directly.

Review `.env` before adding any provider configuration. Never commit `.env` or API keys.

## Feature 3A: AI Study Guide Generator

Configure the OpenAI provider in `.env`:

```text
OPENAI_API_KEY=your-key
AI_MODEL=your-model-name
AI_CHUNK_THRESHOLD=40000
```

Open a lecture and select **Generate Study Guide**. The application extracts all
stored PDF, DOCX, and PPTX materials, sends source-marked content to the provider,
validates the structured response, verifies every source reference, and saves the
canonical result as `Study_Guide.json` inside the lecture directory.

The guide includes overview, learning objectives, concepts, definitions, formulas,
revision topics, confusions, practice questions, quick revision, knowledge gaps,
and source references. It uses only supplied lecture content. The provider is not
allowed to perform web research, predict exam questions, or silently fill gaps
with general knowledge. Missing explanation is represented as a knowledge gap.

If the API key or model is missing, the UI reports a configuration error. Existing
guides are not overwritten without explicit regeneration confirmation. Generated
guides are JSON only; PDF export is planned as the next feature.

## Run

Start the application from the repository root:

```powershell
python -m streamlit run app/main.py
```

The library creates its SQLite database automatically at the configured database
path. Uploaded files are stored under `data/courses/<course>/<lecture>/Original`.
The lecture view provides an `Extract Content` action for inspecting structured
text without sending data to an AI service. **Generate Study Guide** is the
separate Feature 3A action for provider-backed generation.

## Architecture notes

- `app/main.py` is intentionally thin and delegates rendering to `app.ui`.
- `config/settings.py` loads configuration from environment variables and does not store mutable global state.
- `app/storage` owns SQLite initialization, repositories, and filesystem paths.
- `app/services/library_service.py` coordinates database records and local files.
- `app/processors` contains format-specific parsers and a common structured model.
- `app/processors/ocr.py` defines the OCR interface and local Tesseract provider.
- `app/ai` contains the provider abstraction, OpenAI adapter, prompts, Pydantic schemas, and generator.
- `Study_Guide.json` is the canonical generated artifact for the later PDF renderer.
- SQLite is the source of truth; the application does not scan directories to rebuild records.
- Placeholder modules document future ownership boundaries without adding fake processing behavior.
