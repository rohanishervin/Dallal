import os
import sys

import pytest
from dotenv import load_dotenv
from httpx import AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

load_dotenv(".env")

TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
TEST_DEVICE_ID = os.getenv("TEST_DEVICE_ID", "pytest_trading_test")

if not TEST_USERNAME or not TEST_PASSWORD:
    pytest.skip("Missing TEST_USERNAME or TEST_PASSWORD environment variables", allow_module_level=True)


async def get_auth_token():
    """Helper function to get JWT token for authenticated tests"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "device_id": TEST_DEVICE_ID,
            },
        )
        if response.status_code == 200:
            return response.json()["token"]
        else:
            pytest.fail(f"Failed to get auth token: {response.status_code} - {response.text}")


@pytest.mark.asyncio
async def test_market_order_with_auth():
    """Test placing a market order with valid authentication"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/market",
            json={
                "symbol": "EUR/USD",
                "side": "1",  # Buy
                "quantity": 0.01,
                "comment": "Test market order from pytest",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "success" in data
        assert "client_order_id" in data
        assert "message" in data
        assert "timestamp" in data

        # Log results for debugging
        print(f"Market order response: {data}")

        if data["success"]:
            assert "order_id" in data
            assert "execution_report" in data
            assert data["execution_report"] is not None

            # Check execution report structure
            exec_report = data["execution_report"]
            assert "order_id" in exec_report
            assert "client_order_id" in exec_report
            assert "symbol" in exec_report
            assert exec_report["symbol"] == "EUR/USD"
            assert exec_report["side"] == "1"
        else:
            # If order fails, we should have an error message
            assert "error" in data
            print(f"Market order failed as expected: {data['error']}")


@pytest.mark.asyncio
async def test_limit_order_with_auth():
    """Test placing a limit order with valid authentication"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/limit",
            json={
                "symbol": "EUR/USD",
                "side": "1",  # Buy
                "quantity": 0.01,
                "price": 1.0500,  # Well below current market price
                "time_in_force": "1",  # GTC
                "comment": "Test limit order from pytest",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "success" in data
        assert "client_order_id" in data
        assert "message" in data

        print(f"Limit order response: {data}")

        if data["success"]:
            assert "execution_report" in data
            exec_report = data["execution_report"]
            assert exec_report["symbol"] == "EUR/USD"
            assert exec_report["side"] == "1"
            assert exec_report["order_type"] == "2"  # Limit order


@pytest.mark.asyncio
async def test_stop_order_with_auth():
    """Test placing a stop order with valid authentication"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/stop",
            json={
                "symbol": "EUR/USD",
                "side": "2",  # Sell
                "quantity": 0.01,
                "stop_price": 1.0800,  # Well above current market price
                "comment": "Test stop order from pytest",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert "client_order_id" in data

        print(f"Stop order response: {data}")

        if data["success"]:
            exec_report = data["execution_report"]
            assert exec_report["symbol"] == "EUR/USD"
            assert exec_report["side"] == "2"
            assert exec_report["order_type"] == "3"  # Stop order


@pytest.mark.asyncio
async def test_stop_limit_order_with_auth():
    """Test placing a stop-limit order with valid authentication"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/stop-limit",
            json={
                "symbol": "EUR/USD",
                "side": "2",  # Sell
                "quantity": 0.01,
                "stop_price": 1.0800,  # Stop trigger price
                "price": 1.0790,  # Limit price after trigger
                "comment": "Test stop-limit order from pytest",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert "client_order_id" in data

        print(f"Stop-limit order response: {data}")

        if data["success"]:
            exec_report = data["execution_report"]
            assert exec_report["symbol"] == "EUR/USD"
            assert exec_report["side"] == "2"
            assert exec_report["order_type"] == "4"  # Stop-limit order


@pytest.mark.asyncio
async def test_generic_order_endpoint():
    """Test the generic order endpoint with different order types"""
    token = await get_auth_token()

    # Test market order via generic endpoint
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders",
            json={
                "symbol": "EUR/USD",
                "order_type": "1",  # Market
                "side": "1",  # Buy
                "quantity": 0.01,
                "comment": "Generic endpoint market order test",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "client_order_id" in data

        print(f"Generic market order response: {data}")


@pytest.mark.asyncio
async def test_trading_without_auth():
    """Test that trading endpoints require authentication"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/market", json={"symbol": "EUR/USD", "side": "1", "quantity": 0.01}
        )

        assert response.status_code == 403  # Forbidden without auth


@pytest.mark.asyncio
async def test_trading_with_invalid_token():
    """Test trading endpoints with invalid token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/market",
            json={"symbol": "EUR/USD", "side": "1", "quantity": 0.01},
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
async def test_order_validation_errors():
    """Test order validation with invalid data"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test missing required fields
        response = await client.post(
            "/trading/orders/market",
            json={
                "symbol": "EUR/USD",
                "side": "1"
                # Missing quantity
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation error

        # Test invalid quantity
        response = await client.post(
            "/trading/orders/market",
            json={"symbol": "EUR/USD", "side": "1", "quantity": -0.01},  # Negative quantity
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation error

        # Test limit order without price
        response = await client.post(
            "/trading/orders/limit",
            json={
                "symbol": "EUR/USD",
                "side": "1",
                "quantity": 0.01
                # Missing price for limit order
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_order_with_stop_loss_take_profit():
    """Test order with stop loss and take profit"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/market",
            json={
                "symbol": "EUR/USD",
                "side": "1",  # Buy
                "quantity": 0.01,
                "stop_loss": 1.0500,  # Stop loss below entry
                "take_profit": 1.1000,  # Take profit above entry
                "comment": "Market order with SL/TP",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        print(f"Order with SL/TP response: {data}")


@pytest.mark.asyncio
async def test_order_with_time_in_force():
    """Test limit order with different time in force options"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test GTC (Good Till Cancel)
        response = await client.post(
            "/trading/orders/limit",
            json={
                "symbol": "EUR/USD",
                "side": "1",
                "quantity": 0.01,
                "price": 1.0500,
                "time_in_force": "1",  # GTC
                "comment": "GTC limit order",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        print(f"GTC order response: {data}")


@pytest.mark.asyncio
async def test_order_with_metadata():
    """Test order with comment, tag, and magic number"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/market",
            json={
                "symbol": "EUR/USD",
                "side": "1",
                "quantity": 0.01,
                "comment": "Test order with metadata from pytest",
                "tag": "PYTEST_TAG",
                "magic": 12345,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        print(f"Order with metadata response: {data}")


@pytest.mark.asyncio
async def test_invalid_symbol():
    """Test order with invalid symbol"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/market",
            json={"symbol": "INVALID/PAIR", "side": "1", "quantity": 0.01},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # The order should be processed but likely fail due to invalid symbol
        assert "success" in data
        if not data["success"]:
            assert "error" in data
            print(f"Invalid symbol error (expected): {data['error']}")


@pytest.mark.asyncio
async def test_trading_health_check():
    """Test trading service health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/trading/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "trading"


@pytest.mark.asyncio
async def test_order_response_structure():
    """Test that order responses have the expected structure"""
    token = await get_auth_token()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/trading/orders/market",
            json={"symbol": "EUR/USD", "side": "1", "quantity": 0.01},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = ["success", "client_order_id", "message", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check timestamp format
        assert isinstance(data["timestamp"], str)

        # If successful, check additional fields
        if data["success"]:
            assert "order_id" in data
            if "execution_report" in data and data["execution_report"]:
                exec_report = data["execution_report"]
                exec_required_fields = [
                    "order_id",
                    "client_order_id",
                    "exec_id",
                    "order_status",
                    "exec_type",
                    "symbol",
                    "side",
                    "order_type",
                ]
                for field in exec_required_fields:
                    assert field in exec_report, f"Missing execution report field: {field}"


# Performance test
@pytest.mark.asyncio
async def test_multiple_orders_performance():
    """Test placing multiple orders to check performance"""
    token = await get_auth_token()

    import time

    start_time = time.time()

    async with AsyncClient(app=app, base_url="http://test", timeout=60.0) as client:
        # Place 3 orders sequentially
        for i in range(3):
            response = await client.post(
                "/trading/orders/market",
                json={"symbol": "EUR/USD", "side": "1", "quantity": 0.01, "comment": f"Performance test order {i+1}"},
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            print(f"Order {i+1} response: {data['success']}")

    end_time = time.time()
    total_time = end_time - start_time

    print(f"Total time for 3 orders: {total_time:.2f} seconds")
    assert total_time < 30.0, "Orders took too long to process"
