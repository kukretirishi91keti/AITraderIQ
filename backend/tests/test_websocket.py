"""Tests for WebSocket price-streaming endpoint."""

import json
import os

# Force test environment before app import
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("GROQ_API_KEY", "")

from starlette.testclient import TestClient
from main import app


def test_ws_connect_receives_welcome():
    """Connecting to /ws/prices should receive a type=connected message."""
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/prices") as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"


def test_ws_subscribe_confirmed():
    """Subscribing to a symbol should return a subscribed confirmation."""
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/prices") as ws:
            ws.receive_json()  # welcome message
            ws.send_json({"action": "subscribe", "symbols": ["AAPL"]})
            data = ws.receive_json()
            assert "subscri" in data["type"].lower()  # "subscribed"


def test_ws_ping_pong():
    """Sending a ping action should return a pong response."""
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/prices") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"action": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"


def test_ws_unsubscribe_confirmed():
    """Subscribing then unsubscribing should return confirmation."""
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/prices") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"action": "subscribe", "symbols": ["AAPL"]})
            ws.receive_json()  # subscribe confirmation
            ws.send_json({"action": "unsubscribe", "symbols": ["AAPL"]})
            data = ws.receive_json()
            assert data["type"] == "unsubscribed"


def test_ws_invalid_action_returns_error():
    """An unknown action should return an error message."""
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/prices") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"action": "invalid"})
            data = ws.receive_json()
            assert data["type"] == "error"


def test_ws_status():
    """Sending a status action should return connection stats."""
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/prices") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"action": "status"})
            data = ws.receive_json()
            assert "connections" in data
