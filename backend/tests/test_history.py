import os
import sys
from datetime import datetime, timedelta

import pytest
from dotenv import load_dotenv
from httpx import AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

load_dotenv(".env")

TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
TEST_DEVICE_ID = os.getenv("TEST_DEVICE_ID", "pytest_test")


async def get_auth_token():
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_response = await client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD, "device_id": TEST_DEVICE_ID},
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["success"] is True
        return login_data["token"]


@pytest.mark.asyncio
async def test_get_historical_bars_success():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Get current time and request bars for the last few days
    end_time = datetime.now()

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "count": 50,
        "to_time": end_time.isoformat(),
        "price_type": "B",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["symbol"] == "EUR/USD"
        assert data["timeframe"] == "H1"
        assert data["price_type"] == "B"
        assert "message" in data
        assert "bars" in data
        assert isinstance(data["bars"], list)


@pytest.mark.asyncio
async def test_get_historical_bars_multiple_bars():
    """Test that we can retrieve multiple bars (verifying the negative bars logic works)"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "M1",
        "count": 25,
        "price_type": "B",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["symbol"] == "EUR/USD"
        assert data["timeframe"] == "M1"
        assert "bars" in data
        assert isinstance(data["bars"], list)

        # We should get multiple bars (though exact count depends on available data)
        if data["bars"]:
            print(f"Retrieved {len(data['bars'])} bars")
            # Verify bar structure
            for bar in data["bars"]:
                assert "timestamp" in bar
                assert "open_price" in bar
                assert "high_price" in bar
                assert "low_price" in bar
                assert "close_price" in bar
                assert isinstance(bar["open_price"], (int, float))
                assert isinstance(bar["high_price"], (int, float))
                assert isinstance(bar["low_price"], (int, float))
                assert isinstance(bar["close_price"], (int, float))

        # If bars are returned, validate structure
        if data["bars"]:
            bar = data["bars"][0]
            assert "timestamp" in bar
            assert "open_price" in bar
            assert "high_price" in bar
            assert "low_price" in bar
            assert "close_price" in bar
            assert isinstance(bar["open_price"], (int, float))
            assert isinstance(bar["high_price"], (int, float))
            assert isinstance(bar["low_price"], (int, float))
            assert isinstance(bar["close_price"], (int, float))


@pytest.mark.asyncio
async def test_get_historical_bars_different_periods():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    end_time = datetime.now()

    # Test different time periods
    periods = ["M1", "M5", "M15", "H1", "D1"]

    for period in periods:
        request_data = {
            "symbol": "EUR/USD",
            "timeframe": period,
            "count": 10,
            "to_time": end_time.isoformat(),
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/market/history", json=request_data, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["timeframe"] == period


@pytest.mark.asyncio
async def test_get_historical_bars_different_price_types():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    end_time = datetime.now()

    # Test both Bid and Ask prices
    price_types = ["B", "A"]

    for price_type in price_types:
        request_data = {
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "count": 5,
            "to_time": end_time.isoformat(),
            "price_type": price_type,
        }

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/market/history", json=request_data, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["price_type"] == price_type


@pytest.mark.asyncio
async def test_get_historical_bars_without_auth():
    end_time = datetime.now()

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "count": 10,
        "to_time": end_time.isoformat(),
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data)

        # FastAPI returns 403 for missing authentication, not 401
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_historical_bars_invalid_token():
    headers = {"Authorization": "Bearer invalid_token"}
    end_time = datetime.now()

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "count": 10,
        "to_time": end_time.isoformat(),
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_historical_bars_validation_errors():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Test missing required fields
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json={}, headers=headers)
        assert response.status_code == 422  # Validation error

        # Test invalid timeframe
        invalid_request = {
            "symbol": "EUR/USD",
            "timeframe": "INVALID",
            "count": 10,
            "to_time": datetime.now().isoformat(),
        }
        response = await client.post("/market/history", json=invalid_request, headers=headers)
        assert response.status_code == 422

        # Test invalid count (too high)
        invalid_request = {
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "count": 50000,  # Above limit
            "to_time": datetime.now().isoformat(),
        }
        response = await client.post("/market/history", json=invalid_request, headers=headers)
        assert response.status_code == 422

        # Test invalid count (too low)
        invalid_request = {
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "count": 0,  # Below limit
            "to_time": datetime.now().isoformat(),
        }
        response = await client.post("/market/history", json=invalid_request, headers=headers)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_historical_bars_invalid_symbol():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "symbol": "INVALID/SYMBOL",
        "timeframe": "H1",
        "count": 10,
        "to_time": datetime.now().isoformat(),
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)

        # Should return 400 for invalid symbol
        assert response.status_code == 400
        data = response.json()
        # The response structure may vary, check for either format
        assert "detail" in data or "message" in data
        if "detail" in data:
            assert "error" in data["detail"]
        else:
            assert "error" in data


@pytest.mark.asyncio
async def test_get_historical_bars_boundary_values():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    end_time = datetime.now()

    # Test minimum bars
    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "count": 1,
        "to_time": end_time.isoformat(),
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)
        assert response.status_code == 200

        # Test maximum bars
        request_data["count"] = 10000
        response = await client.post("/market/history", json=request_data, headers=headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_historical_bars_response_structure():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "count": 5,
        "to_time": datetime.now().isoformat(),
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify required response fields
        required_fields = ["success", "symbol", "timeframe", "price_type", "bars", "message", "timestamp"]
        for field in required_fields:
            assert field in data

        # Verify data types
        assert isinstance(data["success"], bool)
        assert isinstance(data["symbol"], str)
        assert isinstance(data["timeframe"], str)
        assert isinstance(data["price_type"], str)
        assert isinstance(data["bars"], list)
        assert isinstance(data["message"], str)
        assert isinstance(data["timestamp"], str)

        # Optional fields should be present but may be null
        optional_fields = ["request_id", "from_time", "to_time", "error"]
        for field in optional_fields:
            assert field in data


@pytest.mark.asyncio
async def test_get_historical_bars_performance():
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "M5",
        "count": 100,
        "to_time": datetime.now().isoformat(),
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        import time

        start_time = time.time()

        response = await client.post("/market/history", json=request_data, headers=headers)

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        # Response should complete within reasonable time (30 seconds max)
        assert response_time < 30.0

        data = response.json()
        if data["success"]:
            print(f"Historical bars request completed in {response_time:.2f} seconds")
            print(f"Retrieved {len(data['bars'])} bars")


@pytest.mark.asyncio
async def test_get_historical_bars_without_to_time():
    """Test that historical bars request works without specifying to_time (should default to now)"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "H1",
        "count": 10,
        "price_type": "B",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["symbol"] == "EUR/USD"
        assert data["timeframe"] == "H1"
        assert "bars" in data
        assert isinstance(data["bars"], list)


@pytest.mark.asyncio
async def test_get_historical_bars_multiple_bars():
    """Test that we can retrieve multiple bars (verifying the negative bars logic works)"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "symbol": "EUR/USD",
        "timeframe": "M1",
        "count": 25,
        "price_type": "B",
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/market/history", json=request_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["symbol"] == "EUR/USD"
        assert data["timeframe"] == "M1"
        assert "bars" in data
        assert isinstance(data["bars"], list)

        # We should get multiple bars (though exact count depends on available data)
        if data["bars"]:
            print(f"Retrieved {len(data['bars'])} bars")
            # Verify bar structure
            for bar in data["bars"]:
                assert "timestamp" in bar
                assert "open_price" in bar
                assert "high_price" in bar
                assert "low_price" in bar
                assert "close_price" in bar
                assert isinstance(bar["open_price"], (int, float))
                assert isinstance(bar["high_price"], (int, float))
                assert isinstance(bar["low_price"], (int, float))
                assert isinstance(bar["close_price"], (int, float))
