"""
Phase 1 tests: health check, app startup, router registration.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """GET /health must return 200 with status=ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "rrb-alp-backend"


def test_docs_available_in_dev(client: TestClient) -> None:
    """Swagger UI should be available in development mode."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_api_auth_routes_registered(client: TestClient) -> None:
    """Auth router must be registered — returns a response (not 404)."""
    response = client.get("/api/auth/google/login")
    assert response.status_code != 404


def test_api_subjects_routes_registered(client: TestClient) -> None:
    response = client.get("/api/subjects")
    assert response.status_code != 404


def test_api_topics_routes_registered(client: TestClient) -> None:
    response = client.get("/api/topics")
    assert response.status_code != 404


def test_api_questions_routes_registered(client: TestClient) -> None:
    response = client.get("/api/questions")
    assert response.status_code != 404


def test_api_mock_tests_routes_registered(client: TestClient) -> None:
    response = client.get("/api/mock-tests")
    assert response.status_code != 404


def test_api_pdfs_routes_registered(client: TestClient) -> None:
    response = client.get("/api/pdfs")
    assert response.status_code != 404


def test_api_analytics_routes_registered(client: TestClient) -> None:
    response = client.get("/api/analytics/dashboard")
    assert response.status_code != 404


def test_api_mistakes_routes_registered(client: TestClient) -> None:
    response = client.get("/api/mistakes")
    assert response.status_code != 404


def test_unknown_route_returns_404(client: TestClient) -> None:
    """Unknown routes must return 404, not 500."""
    response = client.get("/api/this-route-does-not-exist")
    assert response.status_code == 404
