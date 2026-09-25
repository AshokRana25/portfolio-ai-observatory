"""Local browser demo and documented HTTP API."""

from contextlib import asynccontextmanager
from importlib.resources import files

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from observatory.service import PortfolioAssistant, Settings


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Question cannot be blank")
        return value.strip()


def create_app(settings: Settings | None = None):
    @asynccontextmanager
    async def lifespan(app):
        load_dotenv()
        assistant = PortfolioAssistant(settings or Settings.from_env())
        app.state.assistant = assistant
        yield
        assistant.close()

    app = FastAPI(title="Portfolio AI Observatory", version="0.1.0", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    def home():
        return files("observatory").joinpath("static/index.html").read_text(encoding="utf-8")

    @app.get("/api/health")
    def health():
        assistant = app.state.assistant
        return {"status": "ok", "mode": assistant.settings.mode,
                "tracing": assistant.settings.tracing, "data": "synthetic"}

    @app.get("/api/projects")
    def projects():
        return app.state.assistant.projects

    @app.post("/api/ask")
    def ask(body: Question):
        try:
            return app.state.assistant.ask(body.question)
        except Exception as error:
            # Do not return provider errors: they can contain credentials or request details.
            raise HTTPException(502, "Assistant unavailable. Check local configuration and retry.") \
                from error

    return app


app = create_app()
