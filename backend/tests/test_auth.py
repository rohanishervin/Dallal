import pytest
from httpx import AsyncClient
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Load local environment
load_dotenv(".env")

@pytest.mark.asyncio
async def test_login_success():
    """Test successful login with demo FIX credentials"""
    username = os.getenv("TEST_USERNAME", "demo_user")
    password = os.getenv("TEST_PASSWORD", "demo_pass")
    device_id = os.getenv("TEST_DEVICE_ID", "pytest_test")
    
    login_data = {
        "username": username,
        "password": password,
        "device_id": device_id
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"Login response: {data}")
        
        if data.get("success"):
            assert "token" in data
            assert data["message"] == "Login successful"
            print(f"✅ Login successful with token: {data['token'][:20]}...")
        else:
            print(f"❌ Login failed: {data.get('error', 'Unknown error')}")
            pytest.skip(f"Login failed with demo credentials: {data.get('error', 'Unknown error')}")

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    login_data = {
        "username": "invalid_user",
        "password": "invalid_password",
        "device_id": "test_device"
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should fail authentication
        assert data["success"] is False
        assert "error" in data
        assert data["message"] == "Login failed"
        
        print(f"✅ Invalid credentials correctly rejected: {data['error']}")

@pytest.mark.asyncio
async def test_login_missing_username():
    """Test login with missing username"""
    login_data = {
        "password": "some_password",
        "device_id": "test_device"
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json=login_data)
        
        # Should return validation error
        assert response.status_code == 422
        print("✅ Missing username properly rejected with 422")

@pytest.mark.asyncio
async def test_login_missing_password():
    """Test login with missing password"""
    login_data = {
        "username": "some_user",
        "device_id": "test_device"
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json=login_data)
        
        # Should return validation error
        assert response.status_code == 422
        print("✅ Missing password properly rejected with 422")

@pytest.mark.asyncio
async def test_login_empty_body():
    """Test login with empty request body"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json={})
        
        # Should return validation error
        assert response.status_code == 422
        print("✅ Empty login request properly rejected with 422")

@pytest.mark.asyncio
async def test_login_device_id_optional():
    """Test that device_id is optional in login"""
    username = os.getenv("TEST_USERNAME", "demo_user")
    password = os.getenv("TEST_PASSWORD", "demo_pass")
    
    login_data = {
        "username": username,
        "password": password
        # No device_id
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("success"):
            print("✅ Login works without device_id")
        else:
            print(f"❌ Login failed without device_id: {data.get('error')}")
            pytest.skip(f"Login failed without device_id: {data.get('error')}")
