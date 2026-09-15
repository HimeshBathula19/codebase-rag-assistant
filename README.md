# Codebase RAG Assistant

An AI-powered developer intelligence platform that helps developers understand real GitHub repositories using grounded Retrieval-Augmented Generation (RAG).

## Features

- Real GitHub repository ingestion
- Public repository support
- Repository file discovery and filtering
- Semantic code analysis
- Code embeddings and vector retrieval
- ChromaDB vector storage
- Hybrid semantic + keyword search
- Grounded codebase question answering
- File and line-level evidence
- Repository Explorer
- Dependency Architecture
- Code Search
- Repository Insights
- Index statistics and health monitoring
- Repository re-indexing

## Architecture

GitHub Repository  
↓  
Repository Ingestion  
↓  
File Filtering & Parsing  
↓  
Symbol Extraction  
↓  
Semantic Code Chunking  
↓  
Embeddings  
↓  
ChromaDB  
↓  
Hybrid Retrieval  
↓  
Grounded RAG  
↓  
Evidence-Based Answer

## Tech Stack

### Frontend
- React
- TypeScript
- Vite

### Backend
- Python
- FastAPI

### RAG / AI
- Sentence Transformers
- ChromaDB
- Tree-sitter
- LLM API

## Core Principle

The assistant is designed to answer questions using evidence from the indexed repository rather than inventing files, functions, classes, APIs, or behavior.

## Running Locally

### Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
