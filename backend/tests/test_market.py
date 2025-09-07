import os
import sys

import pytest
from dotenv import load_dotenv
from httpx import AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

load_dotenv(".env")


class TestMarketEndpoints:
    async def get_auth_token(self):
        """Helper function to get JWT token for authenticated tests"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            login_response = await client.post(
                "/auth/login",
                json={
                    "username": os.getenv("TEST_USERNAME"),
                    "password": os.getenv("TEST_PASSWORD"),
                    "device_id": "pytest_market_test",
                },
            )

            if login_response.status_code == 200:
                return login_response.json()["token"]
            else:
                pytest.fail(f"Failed to get auth token: {login_response.status_code} - {login_response.text}")

    @pytest.mark.asyncio
    async def test_get_instruments_success(self):
        """Test successful retrieval of trading instruments"""
        token = await self.get_auth_token()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert data["success"] is True
            assert "request_id" in data
            assert "response_id" in data
            assert "symbols" in data
            assert "message" in data
            assert "timestamp" in data
            assert isinstance(data["symbols"], list)
            assert len(data["symbols"]) > 0

            # Should get multiple symbols (expecting 300+ based on your tests)
            assert len(data["symbols"]) > 100

            print(f"Retrieved {len(data['symbols'])} trading instruments")

    @pytest.mark.asyncio
    async def test_get_instruments_without_auth(self):
        """Test instruments endpoint without authentication"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments")

            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_instruments_invalid_token(self):
        """Test instruments endpoint with invalid token"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": "Bearer invalid_token"})

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_instruments_data_structure(self):
        """Test that instruments have the expected data structure"""
        token = await self.get_auth_token()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()

            # Get first instrument to check structure
            instruments = data["symbols"]
            assert len(instruments) > 0

            first_instrument = instruments[0]

            # Core required fields
            assert "symbol" in first_instrument
            assert "security_id" in first_instrument
            assert "currency" in first_instrument
            assert "settle_currency" in first_instrument
            assert "trade_enabled" in first_instrument
            assert isinstance(first_instrument["trade_enabled"], bool)

            # Trading parameters should be present (may be null for some symbols)
            trading_fields = [
                "contract_multiplier",
                "round_lot",
                "min_trade_vol",
                "max_trade_volume",
                "trade_vol_step",
                "px_precision",
            ]
            for field in trading_fields:
                assert field in first_instrument

            # Currency information
            currency_fields = [
                "currency_precision",
                "currency_sort_order",
                "settl_currency_precision",
                "settl_currency_sort_order",
            ]
            for field in currency_fields:
                assert field in currency_fields

    @pytest.mark.asyncio
    async def test_eurusd_symbol_availability(self):
        """Test that EUR/USD symbol is available and has complete data"""
        token = await self.get_auth_token()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()

            # Find EUR/USD in the instruments list
            eurusd = None
            for instrument in data["symbols"]:
                if instrument["symbol"] == "EUR/USD":
                    eurusd = instrument
                    break

            assert eurusd is not None, "EUR/USD symbol not found in instruments list"

            # Verify EUR/USD has expected fields populated
            assert eurusd["symbol"] == "EUR/USD"
            assert eurusd["security_id"] is not None
            assert eurusd["currency"] == "EUR"
            assert eurusd["settle_currency"] == "USD"
            assert isinstance(eurusd["trade_enabled"], bool)

            # Check trading parameters are present
            expected_non_null_fields = [
                "contract_multiplier",
                "round_lot",
                "min_trade_vol",
                "max_trade_volume",
                "trade_vol_step",
                "px_precision",
                "currency_precision",
                "settl_currency_precision",
            ]

            for field in expected_non_null_fields:
                assert eurusd[field] is not None, f"EUR/USD missing {field}"

            print(f"EUR/USD instrument data: {eurusd}")

    @pytest.mark.asyncio
    async def test_symbol_leverage_calculation(self):
        """Test that symbol_leverage field is calculated correctly"""
        token = await self.get_auth_token()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()

            instruments = data["symbols"]
            assert len(instruments) > 0

            # Check that symbol_leverage field exists and is calculated properly
            for instrument in instruments:
                assert "symbol_leverage" in instrument, f"Missing symbol_leverage field in {instrument['symbol']}"

                margin_calc_mode = instrument.get("margin_calc_mode", "").lower()
                margin_factor_fractional = instrument.get("margin_factor_fractional")
                symbol_leverage = instrument["symbol_leverage"]

                if margin_calc_mode == "c":
                    # CFD: leverage should be 1 / margin_factor_fractional
                    if margin_factor_fractional and symbol_leverage:
                        try:
                            expected_leverage = 1.0 / float(margin_factor_fractional)
                            assert (
                                abs(symbol_leverage - expected_leverage) < 0.001
                            ), f"CFD leverage mismatch for {instrument['symbol']}: expected {expected_leverage}, got {symbol_leverage}"
                        except (ValueError, ZeroDivisionError):
                            pass  # Skip invalid values
                elif margin_calc_mode == "f" or margin_calc_mode == "l":
                    # FOREX/Leverage: leverage should be account leverage (if available)
                    if symbol_leverage:
                        assert isinstance(
                            symbol_leverage, (int, float)
                        ), f"FOREX/Leverage leverage should be numeric for {instrument['symbol']}"
                        assert (
                            symbol_leverage > 0
                        ), f"FOREX/Leverage leverage should be positive for {instrument['symbol']}"
                else:
                    # Other: leverage should be None
                    assert (
                        symbol_leverage is None
                    ), f"Leverage should be None for unsupported margin_calc_mode {margin_calc_mode} in {instrument['symbol']}"

            print(f"Verified symbol_leverage calculation for {len(instruments)} instruments")

    @pytest.mark.asyncio
    async def test_instruments_field_completeness(self):
        """Test that most instruments have the majority of fields populated"""
        token = await self.get_auth_token()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()

            instruments = data["symbols"]
            assert len(instruments) > 0

            # Check field completeness across all instruments
            all_fields = [
                "symbol",
                "security_id",
                "currency",
                "settle_currency",
                "trade_enabled",
                "contract_multiplier",
                "round_lot",
                "min_trade_vol",
                "max_trade_volume",
                "trade_vol_step",
                "px_precision",
                "currency_precision",
                "currency_sort_order",
                "settl_currency_precision",
                "settl_currency_sort_order",
                "commission",
                "comm_type",
                "swap_type",
                "default_slippage",
                "sort_order",
                "group_sort_order",
                "status_group_id",
                "margin_factor_fractional",
            ]

            # Count how many instruments have each field populated
            field_population = {}
            for field in all_fields:
                populated_count = sum(1 for inst in instruments if inst.get(field) is not None)
                field_population[field] = populated_count

            total_instruments = len(instruments)

            # Core fields should be populated for most instruments
            core_fields = ["symbol", "security_id", "currency", "settle_currency", "trade_enabled"]
            for field in core_fields:
                population_rate = field_population[field] / total_instruments
                assert (
                    population_rate > 0.9
                ), f"Core field {field} only populated in {population_rate:.1%} of instruments"

            # Trading fields should be populated for majority of instruments
            trading_fields = ["contract_multiplier", "round_lot", "px_precision"]
            for field in trading_fields:
                population_rate = field_population[field] / total_instruments
                assert (
                    population_rate > 0.8
                ), f"Trading field {field} only populated in {population_rate:.1%} of instruments"

            print(f"Field population rates across {total_instruments} instruments:")
            for field, count in field_population.items():
                rate = count / total_instruments
                print(f"  {field}: {count}/{total_instruments} ({rate:.1%})")

    @pytest.mark.asyncio
    async def test_instruments_data_types(self):
        """Test that instruments have correct data types"""
        token = await self.get_auth_token()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 200
            data = response.json()

            instruments = data["symbols"]
            first_instrument = instruments[0]

            # Check data types
            assert isinstance(first_instrument["symbol"], str)
            assert isinstance(first_instrument["trade_enabled"], bool)

            # Numeric fields should be strings (as they come from FIX)
            numeric_fields = ["contract_multiplier", "round_lot", "px_precision"]
            for field in numeric_fields:
                if first_instrument[field] is not None:
                    assert isinstance(first_instrument[field], str)

    @pytest.mark.asyncio
    async def test_instruments_response_time(self):
        """Test that instruments endpoint responds within reasonable time"""
        import time

        token = await self.get_auth_token()

        start_time = time.time()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/market/instruments", headers={"Authorization": f"Bearer {token}"})

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 30.0, f"Response took {response_time:.2f}s, expected < 30s"

        print(f"Instruments endpoint response time: {response_time:.2f}s")
