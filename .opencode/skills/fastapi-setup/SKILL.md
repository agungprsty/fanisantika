---
name: fastapi-setup
description: Set up FastAPI projects with Vercel serverless deployment, Pydantic models, and Jinja2 templates
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: python-backend
---

## What I do
- Scaffold FastAPI project structure (app/, api/, services/)
- Configure Vercel serverless deployment with `vercel.json` and `api/index.py`
- Set up Pydantic models for request/response validation
- Configure Jinja2 template rendering
- Wire up environment variables via pydantic-settings

## When to use me
Use this when creating or modifying a FastAPI project. Specifically:
- Creating new routes in `app/main.py`
- Adding new services under `app/services/`
- Setting up Vercel deployment configuration
- Adding Pydantic models in `app/models.py`
- Configuring Jinja2 templates

## Key patterns
- Entry point for Vercel: `api/index.py` imports from `app.main`
- Settings class: use `pydantic-settings.BaseSettings` with `.env` loading
- Template folder: `app/templates/` auto-discovered by FastAPI's `Jinja2Templates`
- Service layer: keep business logic in `services/`, keep routes thin
