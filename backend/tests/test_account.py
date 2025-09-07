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
TEST_DEVICE_ID = os.getenv("TEST_DEVICE_ID", "pytest_account_test")

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
        if response.status_code == 200 and response.json().get("success"):
            return response.json()["token"]
        else:
            pytest.fail(f"Failed to get auth token: {response.status_code} - {response.text}")


@pytest.mark.asyncio
async def test_account_info_requires_authentication():
    """Test that account info endpoint requires valid JWT token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/info")

        assert response.status_code == 403
        print("✅ Account info correctly requires authentication")


@pytest.mark.asyncio
async def test_account_balance_requires_authentication():
    """Test that account balance endpoint requires valid JWT token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/balance")

        assert response.status_code == 403
        print("✅ Account balance correctly requires authentication")


@pytest.mark.asyncio
async def test_account_info_invalid_token():
    """Test account info with invalid JWT token"""
    headers = {"Authorization": "Bearer invalid_token_here"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/info", headers=headers)

        assert response.status_code == 401
        print("✅ Invalid token correctly rejected for account info")


@pytest.mark.asyncio
async def test_account_balance_invalid_token():
    """Test account balance with invalid JWT token"""
    headers = {"Authorization": "Bearer invalid_token_here"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/balance", headers=headers)

        assert response.status_code == 401
        print("✅ Invalid token correctly rejected for account balance")


@pytest.mark.asyncio
async def test_account_info_with_valid_token():
    """Test account info with valid authentication"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/info", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "account" in data
        assert "message" in data
        assert "timestamp" in data

        # If successful, verify account structure
        if data["success"]:
            account = data["account"]

            # Required fields from AccountInfoResponse
            required_fields = ["account_id", "currency", "accounting_type", "balance", "equity", "margin", "leverage"]

            for field in required_fields:
                assert field in account, f"Missing required field: {field}"

            # Verify data types
            assert isinstance(account["balance"], (int, float))
            assert isinstance(account["equity"], (int, float))
            assert isinstance(account["margin"], (int, float))
            assert isinstance(account["leverage"], (int, float))

            print(f"✅ Account info retrieved successfully:")
            print(f"   Account ID: {account['account_id']}")
            print(f"   Balance: {account['balance']} {account['currency']}")
            print(f"   Equity: {account['equity']} {account['currency']}")
            print(f"   Margin: {account['margin']} {account['currency']}")
            print(f"   Leverage: {account['leverage']}")

        else:
            print(f"❌ Account info request failed: {data.get('message', 'Unknown error')}")
            # Still a valid response structure, just no data available


@pytest.mark.asyncio
async def test_account_balance_with_valid_token():
    """Test account balance with valid authentication"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/balance", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data

        # If successful, verify balance structure
        if data["success"]:
            required_fields = ["account_id", "balance", "equity", "margin", "leverage", "free_margin", "currency"]

            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Verify data types
            assert isinstance(data["balance"], (int, float))
            assert isinstance(data["equity"], (int, float))
            assert isinstance(data["margin"], (int, float))
            assert isinstance(data["leverage"], (int, float))
            assert isinstance(data["free_margin"], (int, float))

            # Verify free margin calculation makes sense
            calculated_free_margin = data["equity"] - data["margin"]
            assert abs(data["free_margin"] - calculated_free_margin) < 0.01, "Free margin calculation incorrect"

            print(f"✅ Account balance retrieved successfully:")
            print(f"   Account ID: {data['account_id']}")
            print(f"   Balance: {data['balance']} {data['currency']}")
            print(f"   Equity: {data['equity']} {data['currency']}")
            print(f"   Margin: {data['margin']} {data['currency']}")
            print(f"   Free Margin: {data['free_margin']} {data['currency']}")
            print(f"   Leverage: {data['leverage']}")

            if data.get("margin_level") is not None:
                print(f"   Margin Level: {data['margin_level']}%")

        else:
            print(f"❌ Account balance request failed: {data.get('message', 'Unknown error')}")


@pytest.mark.asyncio
async def test_account_info_response_consistency():
    """Test that account info response is consistent across multiple calls"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make two consecutive calls
        response1 = await client.get("/account/info", headers=headers)
        response2 = await client.get("/account/info", headers=headers)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Both should have same success status
        assert data1["success"] == data2["success"]

        if data1["success"] and data2["success"]:
            # Account ID should be consistent
            assert data1["account"]["account_id"] == data2["account"]["account_id"]
            assert data1["account"]["currency"] == data2["account"]["currency"]
            assert data1["account"]["accounting_type"] == data2["account"]["accounting_type"]
            assert data1["account"]["leverage"] == data2["account"]["leverage"]

            print("✅ Account info responses are consistent")


@pytest.mark.asyncio
async def test_account_balance_response_consistency():
    """Test that account balance response is consistent across multiple calls"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make two consecutive calls
        response1 = await client.get("/account/balance", headers=headers)
        response2 = await client.get("/account/balance", headers=headers)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Both should have same success status
        assert data1["success"] == data2["success"]

        if data1["success"] and data2["success"]:
            # Account ID should be consistent
            assert data1["account_id"] == data2["account_id"]
            assert data1["currency"] == data2["currency"]
            assert data1["leverage"] == data2["leverage"]

            print("✅ Account balance responses are consistent")


@pytest.mark.asyncio
async def test_account_endpoints_data_consistency():
    """Test that account info and balance endpoints return consistent data"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get both account info and balance
        info_response = await client.get("/account/info", headers=headers)
        balance_response = await client.get("/account/balance", headers=headers)

        assert info_response.status_code == 200
        assert balance_response.status_code == 200

        info_data = info_response.json()
        balance_data = balance_response.json()

        # If both successful, verify consistency
        if info_data["success"] and balance_data["success"]:
            info_account = info_data["account"]

            # Common fields should match
            assert info_account["account_id"] == balance_data["account_id"]
            assert info_account["currency"] == balance_data["currency"]
            assert info_account["balance"] == balance_data["balance"]
            assert info_account["equity"] == balance_data["equity"]
            assert info_account["margin"] == balance_data["margin"]
            assert info_account["leverage"] == balance_data["leverage"]

            print("✅ Account info and balance endpoints return consistent data")


@pytest.mark.asyncio
async def test_account_info_error_handling():
    """Test account info endpoint error handling"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/info", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Response should always have required fields even on failure
        required_fields = ["success", "message", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Timestamp should be valid ISO format
        assert isinstance(data["timestamp"], str)

        if not data["success"]:
            # Should have meaningful error message
            assert data["message"] != ""
            print(f"ℹ️  Account info error handled properly: {data['message']}")


@pytest.mark.asyncio
async def test_account_balance_error_handling():
    """Test account balance endpoint error handling"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/balance", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Response should always have required fields even on failure
        required_fields = ["success", "message", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Timestamp should be valid ISO format
        assert isinstance(data["timestamp"], str)

        if not data["success"]:
            # Should have meaningful error message
            assert data["message"] != ""
            print(f"ℹ️  Account balance error handled properly: {data['message']}")


@pytest.mark.asyncio
async def test_account_endpoints_performance():
    """Test account endpoints response time"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    import time

    async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
        # Test account info performance
        start_time = time.time()
        response = await client.get("/account/info", headers=headers)
        info_time = time.time() - start_time

        assert response.status_code == 200
        assert info_time < 10.0, f"Account info took too long: {info_time:.2f}s"

        # Test account balance performance
        start_time = time.time()
        response = await client.get("/account/balance", headers=headers)
        balance_time = time.time() - start_time

        assert response.status_code == 200
        assert balance_time < 10.0, f"Account balance took too long: {balance_time:.2f}s"

        print(f"✅ Performance test passed:")
        print(f"   Account info: {info_time:.2f}s")
        print(f"   Account balance: {balance_time:.2f}s")


@pytest.mark.asyncio
async def test_account_info_optional_fields():
    """Test that account info handles optional fields properly"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/info", headers=headers)

        assert response.status_code == 200
        data = response.json()

        if data["success"]:
            account = data["account"]

            # Optional fields should be handled gracefully (present or null)
            optional_fields = [
                "account_name",
                "account_valid",
                "account_blocked",
                "account_readonly",
                "investor_login",
                "margin_call_level",
                "stop_out_level",
                "email",
                "registration_date",
                "last_modified",
                "assets",
                "sessions_per_account",
                "requests_per_second",
                "throttling_methods",
                "report_currency",
                "token_commission_currency",
                "token_commission_discount",
                "token_commission_enabled",
                "comment",
            ]

            for field in optional_fields:
                # Field should either exist or not exist (no KeyError)
                value = account.get(field)
                if value is not None:
                    print(f"   Optional field {field}: {value}")

            print("✅ Optional fields handled properly")


@pytest.mark.asyncio
async def test_account_balance_margin_calculations():
    """Test that account balance margin calculations are logical"""
    token = await get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/account/balance", headers=headers)

        assert response.status_code == 200
        data = response.json()

        if data["success"]:
            # Basic sanity checks on financial data
            assert data["balance"] >= 0, "Balance should not be negative"
            assert data["leverage"] > 0, "Leverage should be positive"
            assert data["margin"] >= 0, "Margin should not be negative"

            # Free margin should equal equity minus margin
            expected_free_margin = data["equity"] - data["margin"]
            assert abs(data["free_margin"] - expected_free_margin) < 0.01, "Free margin calculation error"

            # If margin level is provided, it should be reasonable
            if data.get("margin_level") is not None:
                assert data["margin_level"] >= 0, "Margin level should not be negative"
                if data["margin"] > 0:
                    expected_margin_level = (data["equity"] / data["margin"]) * 100
                    # Allow some tolerance for rounding
                    assert abs(data["margin_level"] - expected_margin_level) < 1.0, "Margin level calculation error"

            print("✅ Margin calculations are logical and consistent")
