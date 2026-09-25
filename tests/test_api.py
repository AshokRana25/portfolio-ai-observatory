from unittest.mock import patch

from fastapi.testclient import TestClient

from observatory.api import create_app
from observatory.service import Settings


def test_dashboard_and_api():
    with TestClient(create_app(Settings())) as client:
        assert "Portfolio AI Observatory" in client.get("/").text
        assert client.get("/api/health").json()["mode"] == "demo"
        assert len(client.get("/api/projects").json()) == 4
        response = client.post("/api/ask", json={"question": "Which projects are over budget?"})
        assert response.status_code == 200
        assert len(response.json()["sources"]) == 2


def test_invalid_questions():
    with TestClient(create_app(Settings())) as client:
        for question in ["", "  ", "x" * 2001]:
            assert client.post("/api/ask", json={"question": question}).status_code == 422
        assert client.post("/api/ask", json={}).status_code == 422


def test_provider_error_is_not_exposed():
    with TestClient(create_app(Settings())) as client:
        with patch("observatory.service.PortfolioAssistant.ask",
                   side_effect=RuntimeError("private-provider-debug-data")):
            response = client.post("/api/ask", json={"question": "Project risks"})
        assert response.status_code == 502
        assert "private-provider-debug-data" not in response.text
