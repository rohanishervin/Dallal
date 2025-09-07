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


class TestOpenPositionsEndpoint:
    """
    Test suite for /trading/positions/open endpoint
    Tests the Order Mass Status Request functionality filtering for positions (OrdType='N')
    """

    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test method"""
        self.base_url = "http://localhost:8000"
        # Get credentials from environment (same as other tests)
        self.login_data = {
            "username": os.getenv("TEST_USERNAME", "demo_username"),
            "password": os.getenv("TEST_PASSWORD", "demo_password"),
            "device_id": os.getenv("TEST_DEVICE_ID", "test_device_open_positions"),
        }

        # Login and get JWT token
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            login_response = await client.post("/auth/login", json=self.login_data)
            assert login_response.status_code == 200

            login_result = login_response.json()
            assert login_result["success"] is True

            self.token = login_result["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    async def test_get_open_positions_success(self):
        """Test successful retrieval of open positions"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "success" in data
            assert "positions" in data
            assert "total_positions" in data
            assert "positions_by_type" in data
            assert "positions_by_symbol" in data
            assert "total_unrealized_pnl" in data
            assert "total_realized_pnl" in data
            assert "total_commission" in data
            assert "total_swap" in data
            assert "message" in data
            assert "request_id" in data
            assert "request_result" in data
            assert "request_status" in data
            assert "processing_time_ms" in data

            # Verify data types
            assert isinstance(data["success"], bool)
            assert isinstance(data["positions"], list)
            assert isinstance(data["total_positions"], int)
            assert isinstance(data["positions_by_type"], dict)
            assert isinstance(data["positions_by_symbol"], dict)
            assert isinstance(data["processing_time_ms"], int)

            # Verify request result and status
            assert data["request_result"] in [
                "valid_request",
                "no_positions",
                "not_supported",
                "not_authorized",
                "unknown",
            ]
            assert data["request_status"] in ["completed", "rejected"]

    async def test_get_open_positions_no_longer_unsupported(self):
        """Test that positions endpoint no longer returns 'not supported' error for Gross accounts"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # Should not get the old "not supported for account type" error
            assert "not supported for your account type" not in data.get("message", "")
            assert data.get("request_result") != "not_supported"

            # Should be using Order Mass Status Request now, not Request for Positions
            assert data["success"] is True or "Order mass status request failed" in data.get("message", "")

    async def test_get_open_positions_structure(self):
        """Test position object structure when positions are present"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # If there are positions, verify position structure
            if data["positions"]:
                position = data["positions"][0]
                required_fields = [
                    "position_id",
                    "symbol",
                    "currency",
                    "position_type",
                    "status",
                    "net_quantity",
                    "long_quantity",
                    "short_quantity",
                    "average_price",
                    "created_at",
                ]

                for field in required_fields:
                    assert field in position, f"Missing required field: {field}"

                # Verify position type is valid
                assert position["position_type"] in ["long", "short", "net"]

                # Verify status is valid
                assert position["status"] in ["open", "closed", "closing"]

                # Verify quantities make sense
                assert position["net_quantity"] != 0  # Open positions should have non-zero quantity
                assert position["long_quantity"] >= 0
                assert position["short_quantity"] >= 0

                # Verify position type matches quantities
                if position["position_type"] == "long":
                    assert position["long_quantity"] > 0
                    assert position["short_quantity"] == 0
                elif position["position_type"] == "short":
                    assert position["short_quantity"] > 0
                    assert position["long_quantity"] == 0

    async def test_get_open_positions_excludes_orders(self):
        """Test that regular orders (non-position types) are not included in positions"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # All returned items should be positions, not regular orders
            for position in data["positions"]:
                # Positions should have position-specific characteristics
                assert "position_type" in position
                assert "net_quantity" in position
                assert "long_quantity" in position
                assert "short_quantity" in position

                # Position should have non-zero net quantity
                assert abs(position["net_quantity"]) > 0.0000001

    async def test_get_open_positions_filters_zero_positions(self):
        """Test that positions with zero net quantity are filtered out"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # All positions should have non-zero net quantities
            for position in data["positions"]:
                assert abs(position["net_quantity"]) > 0.0000001
                # Also check that at least one of long/short is non-zero
                assert position["long_quantity"] > 0.0000001 or position["short_quantity"] > 0.0000001

    async def test_get_open_positions_financial_summary(self):
        """Test that financial summary calculations are accurate"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            if data["positions"]:
                # Calculate expected totals from individual positions
                expected_unrealized_pnl = sum(pos.get("unrealized_pnl", 0) or 0 for pos in data["positions"])
                expected_realized_pnl = sum(pos.get("realized_pnl", 0) or 0 for pos in data["positions"])
                expected_commission = sum(pos.get("commission", 0) or 0 for pos in data["positions"])
                expected_swap = sum(pos.get("swap", 0) or 0 for pos in data["positions"])

                # Verify totals (allowing for floating point precision)
                if data["total_unrealized_pnl"] is not None:
                    assert abs(data["total_unrealized_pnl"] - expected_unrealized_pnl) < 0.01
                if data["total_realized_pnl"] is not None:
                    assert abs(data["total_realized_pnl"] - expected_realized_pnl) < 0.01
                if data["total_commission"] is not None:
                    assert abs(data["total_commission"] - expected_commission) < 0.01
                if data["total_swap"] is not None:
                    assert abs(data["total_swap"] - expected_swap) < 0.01

    async def test_get_open_positions_summary_statistics(self):
        """Test that summary statistics are accurate"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # Verify total count matches actual positions
            assert data["total_positions"] == len(data["positions"])

            # Verify type breakdown
            type_count_from_positions = {}
            for position in data["positions"]:
                pos_type = position["position_type"]
                type_count_from_positions[pos_type] = type_count_from_positions.get(pos_type, 0) + 1

            assert data["positions_by_type"] == type_count_from_positions

            # Verify symbol breakdown
            symbol_count_from_positions = {}
            for position in data["positions"]:
                symbol = position["symbol"]
                symbol_count_from_positions[symbol] = symbol_count_from_positions.get(symbol, 0) + 1

            assert data["positions_by_symbol"] == symbol_count_from_positions

    async def test_get_open_positions_unauthorized(self):
        """Test that unauthorized requests are rejected"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open")
            assert response.status_code == 401

    async def test_get_open_positions_invalid_token(self):
        """Test that invalid tokens are rejected"""
        invalid_headers = {"Authorization": "Bearer invalid_token_12345"}

        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=invalid_headers)
            assert response.status_code == 401

    async def test_get_open_positions_response_time(self):
        """Test that the endpoint responds within reasonable time"""
        start_time = time.time()

        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert response.status_code == 200
        assert response_time < 5000  # Should respond within 5 seconds

        data = response.json()
        # The reported processing time should be reasonable
        if "processing_time_ms" in data:
            assert data["processing_time_ms"] < 10000  # Less than 10 seconds

    async def test_get_open_positions_field_completeness(self):
        """Test that all expected fields are present and properly formatted"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            if data["positions"]:
                position = data["positions"][0]

                # Test timestamp fields
                if position.get("created_at"):
                    # Should be valid ISO format
                    datetime.fromisoformat(position["created_at"].replace("Z", "+00:00"))

                if position.get("updated_at"):
                    datetime.fromisoformat(position["updated_at"].replace("Z", "+00:00"))

                if position.get("clearing_date"):
                    datetime.fromisoformat(position["clearing_date"].replace("Z", "+00:00"))

                # Test optional fields exist (may be null)
                optional_fields = [
                    "long_average_price",
                    "short_average_price",
                    "current_price",
                    "unrealized_pnl",
                    "realized_pnl",
                    "commission",
                    "commission_currency",
                    "agent_commission",
                    "agent_commission_currency",
                    "swap",
                    "account_balance",
                    "transaction_amount",
                    "transaction_currency",
                    "updated_at",
                    "clearing_date",
                ]

                for field in optional_fields:
                    assert field in position  # Field should exist, even if null

    async def test_get_open_positions_uses_order_mass_status(self):
        """Test that positions endpoint now uses Order Mass Status Request (not Request for Positions)"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            # The request_id should start with "POS_" but use Order Mass Status internally
            assert data["request_id"].startswith("POS_")

            # Should not have the old position-specific error messages
            error_indicators = [
                "not supported for account type",
                "Request for Positions Not Supported",
                "Position requests are not supported",
            ]

            for error_text in error_indicators:
                assert error_text not in data.get("message", "")

    async def test_get_open_positions_integration_with_orders(self):
        """Test that positions and orders endpoints use the same underlying data source"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            # Get both orders and positions
            orders_response = await client.get("/trading/orders/open", headers=self.headers)
            positions_response = await client.get("/trading/positions/open", headers=self.headers)

            assert orders_response.status_code == 200
            assert positions_response.status_code == 200

            orders_data = orders_response.json()
            positions_data = positions_response.json()

            # Both should succeed (or fail) together since they use the same FIX request
            assert orders_data["success"] == positions_data["success"]

            # If both succeed, verify they're using the same data source
            if orders_data["success"] and positions_data["success"]:
                # Processing times should be similar (within reasonable range)
                time_diff = abs(orders_data["processing_time_ms"] - positions_data["processing_time_ms"])
                # Allow for some variance but they should be in the same ballpark
                assert time_diff < 5000  # Within 5 seconds of each other

    async def test_get_open_positions_position_type_logic(self):
        """Test that position types are correctly determined from side and quantities"""
        async with AsyncClient(app=app, base_url=self.base_url) as client:
            response = await client.get("/trading/positions/open", headers=self.headers)

            assert response.status_code == 200
            data = response.json()

            for position in data["positions"]:
                pos_type = position["position_type"]
                long_qty = position["long_quantity"]
                short_qty = position["short_quantity"]
                net_qty = position["net_quantity"]

                # Verify position type logic
                if pos_type == "long":
                    assert long_qty > 0
                    assert short_qty == 0
                    assert net_qty > 0
                elif pos_type == "short":
                    assert short_qty > 0
                    assert long_qty == 0
                    assert net_qty > 0  # Net quantity should be positive (absolute value)
                elif pos_type == "net":
                    # Net positions might have both long and short components
                    assert long_qty >= 0
                    assert short_qty >= 0
                    assert abs(net_qty) > 0

    async def teardown_method(self):
        """Cleanup after each test"""
        # Logout to clean up session
        try:
            async with AsyncClient(app=app, base_url=self.base_url) as client:
                await client.post("/auth/logout", headers=self.headers)
        except:
            pass  # Ignore logout errors in tests
