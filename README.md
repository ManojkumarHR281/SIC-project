# Evidence-Calibrated Code Review

A local-first Flask application for static code review that pairs each finding with its location, supporting evidence, an evidence-based confidence estimate, an uncertainty estimate, and a remediation suggestion. Source code is analyzed as untrusted text and is never executed.

## Problem and solution

Automated review tools can present weakly supported suggestions with unwarranted certainty. This application records the rule, evidence strength, certainty, code context, and independent confirmation (when available), then produces a transparent, reproducible score. Findings that depend on runtime context are labeled accordingly. Scores are estimates and are not claimed to be empirically calibrated probabilities.

## Architecture and stack

- Python 3, Flask application factory and blueprints
- SQLite with Flask-SQLAlchemy; reviews, findings, and evidence are persisted
- Python `ast` analysis and supplementary safe lexical security rules
- Bootstrap 5, Bootstrap Icons, Chart.js, responsive CSS and vanilla JavaScript
- Flask-WTF CSRF protection for browser forms

Key modules: `app/services/code_analyzer.py`, `security_analyzer.py`, `review_engine.py`, `evidence_engine.py`, and `uncertainty_engine.py`; persistence is in `app/models.py`; routes are separated by dashboard, review, history, and settings.

## Features

- Dashboard statistics and charts populated from SQLite, with useful empty states
- Paste or upload supported source files; configure language, analysis mode, and sensitivity
- Python AST checks for syntax errors, mutable defaults, broad swallowed exceptions, `eval`/`exec`, pickle loading, SQL concatenation, credential-like literals, division risks, identity comparisons, long functions, and nested loops
- Security patterns for shell-enabled subprocess calls and credential assignments
- Findings include severity, line/snippet, evidence source, evidence strength, verification status, confidence, uncertainty, rationale, and remediation
- Results filtering, review history, deletion, JSON, CSV, and Markdown report export
- JSON APIs at `/api/review`, `/api/reviews`, `/api/reviews/<id>`, and `/api/dashboard/stats`
- Stores source digest and size, not the complete submitted file. Finding snippets are retained with review results.

## Installation

Windows PowerShell:

```powershell
cd evidence_calibrated_code_review
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cd evidence_calibrated_code_review
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set a private random `SECRET_KEY` in the environment for deployments. The included default is only for local development.

## Run and test

```bash
python run.py
```

Open <http://127.0.0.1:7000>. The first startup creates `instance/reviews.sqlite3`.

```bash
python -m pytest
```

The debug server is intended for development only. Deploy behind a production WSGI server with debug disabled.

## Confidence methodology

Base weights: 0.30 rule reliability, 0.25 evidence strength, 0.20 detection certainty, 0.15 context completeness, and 0.10 independent confirmation. Weights for unavailable factors are removed and the remainder normalized. A completeness penalty is applied when evidence factors are missing. A deterministic parser finding receives a minimum score of 0.82 because the parser's syntactic observation is verified; this does not certify broader runtime impact. Independent confirmation is currently unavailable and is never inferred from duplicate checks by the same local engine. Confidence classes are high ≥ 80%, medium ≥ 50%, low < 50%.

Uncertainty begins at `1 - confidence`, with increments for missing context and context-dependent behavior. It is capped at 1. These heuristic scores need labeled real-world outcomes before they can be called calibrated probabilities.

## Security limitations

Uploads are restricted by extension and size and filenames are reduced to basenames. The backend reads source content in memory and never invokes it or runs analyzers through subprocess. SQLite persists findings and nearby code snippets; delete reviews when those records are no longer needed. CSRF protection is enabled for browser forms. For production, set a strong secret key, use HTTPS, apply authentication and rate limits, isolate the instance database, and review retention requirements. Non-Python languages currently have only limited generic security pattern checks, not language-complete parsers. No LLM integration is implemented; the interface truthfully operates in local mode.

## Future enhancements

Add dedicated analyzers for additional languages, optional validated provider integrations, empirically evaluated calibration using labeled outcomes, authentication and project-level access controls, migrations, richer diff/repository analysis, and review status workflows.
