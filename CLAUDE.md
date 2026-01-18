# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hello-Agents is a comprehensive Chinese educational tutorial by the Datawhale community for building AI-native agents (智能体). The project teaches LLM-based agent development from theory to practice across 16 chapters.

**Primary language:** Chinese (documentation), Python (code), TypeScript/Vue (some frontends)

**License:** CC BY-NC-SA 4.0

## Repository Structure

- `docs/` - Tutorial documentation (16 chapters), served via Docsify
- `code/` - Code examples organized by chapter
- `Co-creation-projects/` - Community-contributed agent projects
- `Extra-Chapter/` - Community blog posts and supplementary content

## Working with Code Examples

Each chapter's code is self-contained. Common setup pattern:

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install chapter-specific dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
```

### Key Projects

**Chapter 13 - Trip Planner (FastAPI + Vue3 + MCP):**
```bash
# Backend
cd code/chapter13/helloagents-trip-planner/backend
pip install -r requirements.txt
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd code/chapter13/helloagents-trip-planner/frontend
npm install
npm run dev
```

**Chapter 15 - AI Town (Godot 4.x + FastAPI):**
```bash
cd code/chapter15/Helloagents-AI-Town/backend
pip install -r requirements.txt
```

## Architecture Concepts

The tutorial teaches building a custom agent framework called "HelloAgents" (separate repo: https://github.com/jjyaoao/helloagents).

**Key agent paradigms covered (Chapter 4):**
- ReAct (Reasoning + Acting)
- Plan-and-Solve
- Reflection

**Framework components (Chapter 7+):**
- `SimpleAgent` - Base agent class
- `HelloAgentsLLM` - LLM abstraction layer
- `ToolRegistry` - Tool management
- Memory systems (Working, Episodic, Semantic)
- MCP (Model Context Protocol) integration

**Frameworks demonstrated (Chapter 6):**
- AutoGen, AgentScope, CAMEL, LangGraph

## Contributing Community Projects

Projects go in `Co-creation-projects/` with naming format: `{GitHub-username}-{project-name}`

Required files: `README.md`, `requirements.txt`, `main.ipynb`
