import asyncio
import os
import sys
import time
from datetime import datetime

import pytest
from dotenv import load_dotenv
from httpx import AsyncClient

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Load local environment
load_dotenv(".env")


class TestOpenOrdersEndpoint:
    """
    Test suite for /trading/orders/open endpoint
    Tests the Order Mass Status Request functionality with real FIX integration
    """

    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test method"""
        self.base_url = "http://localhost:8000"
        # Get credentials from environment (same as other tests)
        self.login_data = {
            "username": os.getenv("TEST_USERNAME", "demo_username"),
            "password": os.getenv("TEST_PASSWORD", "demo_password"),
            "device_id": os.getenv("TEST_DEVICE_ID", "test_device_open_orders"),
        }

        # Login and get JWT token
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            login_response = await client.post("/auth/login", json=self.login_data)
            assert login_response.status_code == 200

            login_result = login_response.json()
            assert login_result["success"] is True

            self.token = login_result["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    async def test_get_open_orders_success(self):
        """Test successful retrieval of open orders"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "success" in data
            assert "orders" in data
            assert "total_orders" in data
            assert "orders_by_status" in data
            assert "orders_by_symbol" in data
            assert "message" in data
            assert "request_id" in data
            assert "processing_time_ms" in data

            # Verify data types
            assert isinstance(data["success"], bool)
            assert isinstance(data["orders"], list)
            assert isinstance(data["total_orders"], int)
            assert isinstance(data["orders_by_status"], dict)
            assert isinstance(data["orders_by_symbol"], dict)
            assert isinstance(data["processing_time_ms"], int)

            # If there are orders, verify order structure
            if data["orders"]:
                order = data["orders"][0]
                required_fields = [
                    "order_id",
                    "client_order_id",
                    "symbol",
                    "order_type",
                    "side",
                    "status",
                    "original_quantity",
                    "remaining_quantity",
                    "executed_quantity",
                    "created_at",
                ]

                for field in required_fields:
                    assert field in order, f"Missing required field: {field}"

                # Verify order type is valid
                assert order["order_type"] in ["market", "limit", "stop", "stop_limit"]

                # Verify side is valid
                assert order["side"] in ["buy", "sell"]

                # Verify status is valid for open orders
                assert order["status"] in ["pending", "partial", "cancelling", "modifying"]

                # Verify quantities are non-negative
                assert order["original_quantity"] >= 0
                assert order["remaining_quantity"] >= 0
                assert order["executed_quantity"] >= 0

    async def test_get_open_orders_filters_filled_orders(self):
        """Test that filled orders are not included in open orders"""
        # First, place a market order that should execute immediately
        order_data = {
            "symbol": "EUR/USD",
            "side": "1",  # Buy
            "quantity": 0.01,
            "comment": "Test market order for filtering",
        }

        async with AsyncClient(app=app, base_url=self.base_url) as client:
            # Place market order
            place_response = await client.post("/trading/orders/market", json=order_data, headers=self.headers)
            assert place_response.status_code == 200

            place_result = place_response.json()
            if not place_result.get("success"):
                pytest.skip(f"Could not place test order: {place_result.get('error', 'Unknown error')}")

            # Wait a bit for order to process
            await asyncio.sleep(2)

            # Get open orders
            open_response = await client.get("/trading/orders/open", headers=self.headers)
            assert open_response.status_code == 200

            open_data = open_response.json()
            assert open_data["success"] is True

            # Check that filled orders are not in the open orders list
            placed_order_id = place_result.get("client_order_id")
            if placed_order_id:
                order_ids = [order["client_order_id"] for order in open_data["orders"]]
                # If the order was filled, it should not be in open orders
                # If it's still pending, it should be there
                for order in open_data["orders"]:
                    if order["client_order_id"] == placed_order_id:
                        # If it's in open orders, it should not be filled
                        assert order["status"] != "filled"

    async def test_get_open_orders_excludes_positions(self):
        """Test that positions (OrdType='N') are not included in orders"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # All returned items should be actual orders, not positions
            # Positions would have different characteristics
            for order in data["orders"]:
                # Orders should have standard order types, not position type
                assert order["order_type"] in ["market", "limit", "stop", "stop_limit"]

                # Orders should have remaining quantity > 0 (otherwise they'd be filtered out)
                assert order["remaining_quantity"] > 0

    async def test_get_open_orders_status_accuracy(self):
        """Test that order statuses are accurately determined from FIX data"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            for order in data["orders"]:
                # Validate status logic
                if order["status"] == "filled":
                    # Filled orders should not be in open orders (this would be a bug)
                    pytest.fail(f"Filled order {order['order_id']} found in open orders")

                elif order["status"] == "partial":
                    # Partially filled orders should have some execution
                    assert order["executed_quantity"] > 0
                    assert order["remaining_quantity"] > 0

                elif order["status"] == "pending":
                    # Pending orders should have no execution or be market orders waiting
                    # (Market orders might show pending briefly before execution)
                    pass  # This is valid for open orders

                # Verify quantities make sense
                total_handled = order["executed_quantity"] + order["remaining_quantity"]
                # Allow small floating point differences
                assert abs(total_handled - order["original_quantity"]) < 0.0001

    async def test_get_open_orders_unauthorized(self):
        """Test that unauthorized requests are rejected"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open")
            assert response.status_code == 401

    async def test_get_open_orders_invalid_token(self):
        """Test that invalid tokens are rejected"""
        invalid_headers = {"Authorization": "Bearer invalid_token_12345"}

        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open", headers=invalid_headers)
            assert response.status_code == 401

    async def test_get_open_orders_response_time(self):
        """Test that the endpoint responds within reasonable time"""
        start_time = time.time()

        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open", headers=self.headers)

        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert response.status_code == 200
        assert response_time < 5000  # Should respond within 5 seconds

        data = response.json()
        # The reported processing time should be reasonable
        if "processing_time_ms" in data:
            assert data["processing_time_ms"] < 10000  # Less than 10 seconds

    async def test_get_open_orders_summary_statistics(self):
        """Test that summary statistics are accurate"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # Verify total count matches actual orders
            assert data["total_orders"] == len(data["orders"])

            # Verify status breakdown
            status_count_from_orders = {}
            for order in data["orders"]:
                status = order["status"]
                status_count_from_orders[status] = status_count_from_orders.get(status, 0) + 1

            assert data["orders_by_status"] == status_count_from_orders

            # Verify symbol breakdown
            symbol_count_from_orders = {}
            for order in data["orders"]:
                symbol = order["symbol"]
                symbol_count_from_orders[symbol] = symbol_count_from_orders.get(symbol, 0) + 1

            assert data["orders_by_symbol"] == symbol_count_from_orders

    async def test_get_open_orders_field_completeness(self):
        """Test that all expected fields are present and properly formatted"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/orders/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            if data["orders"]:
                order = data["orders"][0]

                # Test timestamp fields
                if order.get("created_at"):
                    # Should be valid ISO format
                    datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))

                if order.get("updated_at"):
                    datetime.fromisoformat(order["updated_at"].replace("Z", "+00:00"))

                # Test optional fields exist (may be null)
                optional_fields = [
                    "price",
                    "stop_price",
                    "average_price",
                    "expire_time",
                    "stop_loss",
                    "take_profit",
                    "max_visible_quantity",
                    "immediate_or_cancel",
                    "market_with_slippage",
                    "commission",
                    "swap",
                    "slippage",
                    "comment",
                    "tag",
                    "magic",
                    "parent_order_id",
                ]

                for field in optional_fields:
                    assert field in order  # Field should exist, even if null

    async def teardown_method(self):
        """Cleanup after each test"""
        # Logout to clean up session
        try:
            async with AsyncClient(app=app, base_url=self.base_url) as client:
                await client.post("/auth/logout", headers=self.headers)
        except:
            pass  # Ignore logout errors in tests
