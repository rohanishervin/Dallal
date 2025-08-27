import asyncio
import os
import sys

import pytest
from dotenv import load_dotenv
from httpx import AsyncClient

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Load local environment
load_dotenv(".env")


async def get_auth_token():
    """Helper function to get authentication token"""
    username = os.getenv("TEST_USERNAME", "demo_user")
    password = os.getenv("TEST_PASSWORD", "demo_pass")
    device_id = os.getenv("TEST_DEVICE_ID", "pytest_test")

    login_data = {"username": username, "password": password, "device_id": device_id}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json=login_data)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data["token"]

        return None


@pytest.mark.asyncio
async def test_session_status_requires_authentication():
    """Test that session status requires valid JWT token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/session/status")

        # Should return 401 or 403 without token
        assert response.status_code in [401, 403]
        print("✅ Session status correctly requires authentication")


@pytest.mark.asyncio
async def test_session_status_invalid_token():
    """Test session status with invalid JWT token"""
    headers = {"Authorization": "Bearer invalid_token_here"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/session/status", headers=headers)

        # Should return 401 or 403 with invalid token
        assert response.status_code in [401, 403]
        print("✅ Invalid token correctly rejected")


@pytest.mark.asyncio
async def test_session_status_with_valid_token():
    """Test session status with valid authentication"""
    # Get authentication token
    token = await get_auth_token()

    if not token:
        pytest.skip("Could not get authentication token")

    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/session/status", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert "session" in data
        assert "message" in data

        session = data["session"]

        # Verify session structure
        assert "user_id" in session
        assert "overall_active" in session
        assert isinstance(session["overall_active"], bool)

        # Should have both trade and feed sessions after login
        assert "trade_session" in session
        assert "feed_session" in session

        # Log session details
        if session["overall_active"]:
            print("✅ Session status shows active sessions:")
            if session["trade_session"]:
                trade = session["trade_session"]
                print(
                    f"   Trade: {trade['connection_type']}, Active: {trade['is_active']}, Heartbeat: {trade['heartbeat_status']}"
                )
            if session["feed_session"]:
                feed = session["feed_session"]
                print(
                    f"   Feed: {feed['connection_type']}, Active: {feed['is_active']}, Heartbeat: {feed['heartbeat_status']}"
                )
        else:
            print("ℹ️  Session status shows no active sessions")


@pytest.mark.asyncio
async def test_session_heartbeat_tracking():
    """Test that heartbeat tracking works over time"""
    token = await get_auth_token()

    if not token:
        pytest.skip("Could not get authentication token")

    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get initial status
        response1 = await client.get("/session/status", headers=headers)
        assert response1.status_code == 200
        data1 = response1.json()

        if not data1["session"]["overall_active"]:
            pytest.skip("No active sessions to test heartbeat tracking")

        initial_age = data1["session"]["trade_session"]["session_age_seconds"]

        # Wait a few seconds
        await asyncio.sleep(3)

        # Get status again
        response2 = await client.get("/session/status", headers=headers)
        assert response2.status_code == 200
        data2 = response2.json()

        new_age = data2["session"]["trade_session"]["session_age_seconds"]

        # Age should have increased
        assert new_age > initial_age

        # Heartbeat status should be trackable
        trade_heartbeat = data2["session"]["trade_session"]["heartbeat_status"]
        feed_heartbeat = data2["session"]["feed_session"]["heartbeat_status"]

        assert trade_heartbeat in ["healthy", "warning", "failed", "pending"]
        assert feed_heartbeat in ["healthy", "warning", "failed", "pending"]

        print(f"✅ Session age tracking works: {initial_age}s -> {new_age}s")
        print(f"   Trade heartbeat: {trade_heartbeat}")
        print(f"   Feed heartbeat: {feed_heartbeat}")


@pytest.mark.asyncio
async def test_logout():
    """Test session logout functionality"""
    # First login
    token = await get_auth_token()

    if not token:
        pytest.skip("Could not get authentication token for logout test")

    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Verify sessions are active before logout
        status_response = await client.get("/session/status", headers=headers)
        assert status_response.status_code == 200
        status_data = status_response.json()

        if not status_data["session"]["overall_active"]:
            pytest.skip("No active sessions to logout")

        print("ℹ️  Sessions active before logout")

        # Logout
        logout_response = await client.post("/session/logout", headers=headers)
        assert logout_response.status_code == 200

        logout_data = logout_response.json()
        assert logout_data["success"] is True
        assert "message" in logout_data

        print(f"✅ Logout successful: {logout_data['message']}")

        # Verify sessions are cleaned up
        status_response_after = await client.get("/session/status", headers=headers)
        assert status_response_after.status_code == 200

        status_data_after = status_response_after.json()
        assert status_data_after["session"]["overall_active"] is False

        print("✅ Sessions properly cleaned up after logout")


@pytest.mark.asyncio
async def test_logout_requires_authentication():
    """Test that logout requires valid JWT token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/session/logout")

        # Should return 401 or 403 without token
        assert response.status_code in [401, 403]
        print("✅ Logout correctly requires authentication")


@pytest.mark.asyncio
async def test_logout_when_no_sessions():
    """Test logout when no sessions are active"""
    # Login first
    token = await get_auth_token()

    if not token:
        pytest.skip("Could not get authentication token")

    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Logout first time
        logout_response1 = await client.post("/session/logout", headers=headers)
        assert logout_response1.status_code == 200

        # Logout second time (no active sessions)
        logout_response2 = await client.post("/session/logout", headers=headers)
        assert logout_response2.status_code == 200

        logout_data = logout_response2.json()
        assert logout_data["success"] is True
        assert "no active sessions" in logout_data["message"].lower()

        print("✅ Multiple logout attempts handled gracefully")
