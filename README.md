# Universal Neural Intelligence (Uni) Engine

## *Patents Pending*:  
• **TAPESTRY** – Long-Term Memory Summarization System
• **LSP** – Language Structure Protocol for Deterministic Parsing

## Requirements:

Make sure you have an `.env` file in the root of each phase with the GROQ_API_KEY value as `GROQ_API_KEY=gsk_XXX`

## Introduction

The Universal Neural Intelligence (Uni) Engine is a modular, language-driven AI framework designed for real-time command processing and continuous learning. It combines deterministic parsing with optional LLM fallback and includes long-term memory via summarization. The system treats language as a formal protocol: it parses, interprets, stores, and acts on natural language commands with verifiable precision.

## Architecture Overview

### Input and Preprocessing
Supports text input (and optionally voice/sensors) and prepares data for parsing.

### Flexible Language Engine (FLE)
- RegEx Command Layer
- Constituency Parsing
- Dependency Parsing

### Protocol Layer
- Data Protocols (internal execution)
- Actuation Protocols (external control)

### LLM Fallback & L.E.A.R.N.
Fallback to a large language model when deterministic parsing fails. Uses the L.E.A.R.N. loop to refine and store new patterns.

### Long-Term Memory Store (LTMS)
Summarizes conversations and stores them in a SQLite database for recall and continuity.

## Project Structure

Each phase is in a self-contained folder. Each folder includes its own Flask app, database, virtual environment (`env_uni`), and `requirements.txt`.

/
|-- uni-alpha
|-- uni-bravo
|-- uni-charlie
|-- uni-delta
|-- uni-echo
|-- uni-foxtrot
|-- README.md

## Phase Overview

uni-alpha
  Basic LLM-powered chatbot. Stores conversations.

uni-bravo
  Adds summarization and memory. Conversations are compressed into summaries.

uni-charlie
  Adds regex command parsing. Known queries are handled without LLM.

uni-delta
  Adds intent detection and function protocol mapping. Introduces structured execution.

uni-echo
  Full syntactic parsing with Stanza. Handles complex sentences and structures.

uni-foxtrot
  Patterns and configuration are data-driven via the database. Major refactor and stability pass.

## Running a Phase

1. Navigate to a phase folder (e.g., cd uni-charlie)
2. Activate the virtual environment:
   - Windows: env_uni\Scripts\activate
   - Mac/Linux: source env_uni/bin/activate
3. Install dependencies:
   - pip install -r requirements.txt
4. Run the Flask app:
   - python app.py
5. Visit http://localhost:5011 (the port in app.py)

Each phase runs independently. Shut down with Ctrl+C and switch folders to run a different phase.

## Git Ignore

One .gitignore in the root covers everything. It should include patterns like:

**/env_uni/
*.pyc
__pycache__/
*.db
.env

Note: This project uses a PyTorch nightly build. To install correctly, follow PyTorch nightly instructions. The provided requirements.txt expects nightly wheels (e.g., torch==2.9.0.dev...). Use pip install --pre torch or download the specific wheel from the official site.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
