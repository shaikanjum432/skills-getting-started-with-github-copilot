import copy
import os
import importlib.util
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient


def load_app_module():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app_path = os.path.join(root, "src", "app.py")
    spec = importlib.util.spec_from_file_location("app_module", app_path)
    app_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_mod)
    return app_mod


@pytest.fixture(scope="module")
def app_mod():
    return load_app_module()


@pytest.fixture
def client(app_mod):
    # Arrange: create TestClient for the FastAPI app
    client = TestClient(app_mod.app)
    yield client


@pytest.fixture(autouse=True)
def reset_activities(app_mod):
    # Arrange: save and restore a deep copy of initial activities to keep tests isolated
    initial = copy.deepcopy(app_mod.activities)
    yield
    app_mod.activities = copy.deepcopy(initial)


def test_root_redirect(client):
    # Arrange: client provided by fixture

    # Act: request root without following redirects
    response = client.get("/", follow_redirects=False)

    # Assert: should respond with a redirect to the static index
    assert response.status_code in (301, 302, 307, 308)
    assert response.headers.get("location") == "/static/index.html"


def test_get_activities(client):
    # Arrange

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "Chess Club" in data


def test_signup_activity(client, app_mod):
    # Arrange
    activity = "Chess Club"
    email = "tester@example.com"
    encoded = quote(activity, safe="")

    # Act: sign up
    response = client.post(f"/activities/{encoded}/signup?email={email}")

    # Assert
    assert response.status_code == 200
    assert email in response.json().get("message", "")

    # Act: sign up same email again -> should fail
    response2 = client.post(f"/activities/{encoded}/signup?email={email}")

    # Assert duplicate signup returns 400
    assert response2.status_code == 400


def test_remove_participant(client):
    # Arrange: use an existing participant from the seeded data
    activity = "Chess Club"
    participant = "michael@mergington.edu"
    encoded = quote(activity, safe="")

    # Act: remove participant
    response = client.delete(f"/activities/{encoded}/participants?email={participant}")

    # Assert
    assert response.status_code == 200
    assert participant in response.json().get("message", "")

    # Act: remove again -> not found
    response2 = client.delete(f"/activities/{encoded}/participants?email={participant}")
    assert response2.status_code == 404
