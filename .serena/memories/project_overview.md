# Lazy Learn — Project Overview

## Purpose
AI-powered study assistant desktop app. Students import PDF textbooks, the app extracts content (TOC, chapters, sections), then provides AI-powered search, explanations, practice questions, and conversations about the content.

## Tech Stack
- **Desktop**: Tauri (Rust shell wrapping web frontend)
- **Frontend**: React + TypeScript + Vite (localhost:5173)
- **Backend**: Python FastAPI (localhost:8000)
- **Database**: SQLite via aiosqlite
- **AI Providers**: DeepSeek (primary, cheaper), OpenAI GPT-4o (vision/fallback)
- **PDF Processing**: PyMuPDF (fitz), MinerU (OCR for scanned PDFs)
- **Package Management**: pip (backend), npm (frontend)

## Architecture
```
Tauri Desktop App
  └── Frontend (React/TS/Vite)
        └── FastAPI Backend (Python)
              ├── 11 Router modules (API layer)
              ├── 30 Service modules (business logic)
              ├── SQLite database
              └── AI providers (DeepSeek, OpenAI)
```

## Core Pipeline
PDF Upload → TOC Extraction → Chapter Verification → Content Extraction → Description Generation

States: uploaded → toc_extracted → awaiting_verification → extracting → partially_extracted → fully_extracted

## Key Components
- `PipelineOrchestrator` — State machine for import pipeline
- `MetadataStore` — SQLite data layer (courses, textbooks, chapters, conversations)
- `TocExtractionService` — 3-tier TOC: bookmarks → MinerU OCR → AI fallback
- `AIRouter` — Routes AI calls to DeepSeek or OpenAI
- `ContentExtractor` — Pulls chapter text from PDFs
- `RelevanceMatcher` — Matches chapters to course topics
