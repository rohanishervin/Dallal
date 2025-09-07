import logging
from datetime import datetime
from typing import Optional, Tuple

from src.schemas.market_schemas import (
    HistoricalBar,
    HistoricalBarsRequest,
    HistoricalBarsResponse,
    PeriodID,
    PriceType,
    SecurityInfo,
    SecurityListResponse,
)
from src.services.account_service import account_service
from src.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class MarketService:
    def __init__(self):
        pass

    def _calculate_symbol_leverage(self, symbol_data: dict, account_leverage: Optional[float]) -> Optional[float]:
        """
        Calculate symbol leverage based on margin_calc_mode and account leverage.

        Business Logic:
        - If margin_calc_mode = "c": leverage = 1 / margin_factor_fractional
        - If margin_calc_mode = "f": leverage = account_leverage
        - If margin_calc_mode = "l": leverage = account_leverage
        - Otherwise: return None
        """
        try:
            margin_calc_mode = symbol_data.get("margin_calc_mode", "").lower()
            margin_factor_fractional_str = symbol_data.get("margin_factor_fractional")

            if not margin_calc_mode:
                logger.debug("No margin_calc_mode found for symbol")
                return None

            # CFD case: leverage = 1 / margin_factor_fractional
            if margin_calc_mode == "c":
                if margin_factor_fractional_str:
                    try:
                        margin_factor_fractional = float(margin_factor_fractional_str)
                        if margin_factor_fractional > 0:
                            leverage = 1.0 / margin_factor_fractional
                            logger.debug(f"CFD leverage calculated: {leverage} (1/{margin_factor_fractional})")
                            return leverage
                        else:
                            logger.warning(f"Invalid margin_factor_fractional for CFD: {margin_factor_fractional}")
                            return None
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Could not parse margin_factor_fractional for CFD: {margin_factor_fractional_str}"
                        )
                        return None
                else:
                    logger.debug("No margin_factor_fractional found for CFD symbol")
                    return None

            # FOREX case: leverage = account_leverage
            elif margin_calc_mode == "f":
                if account_leverage is not None:
                    logger.debug(f"FOREX leverage from account: {account_leverage}")
                    return account_leverage
                else:
                    logger.debug("No account leverage available for FOREX symbol")
                    return None

            # Leverage case: leverage = account_leverage (same as FOREX)
            elif margin_calc_mode == "l":
                if account_leverage is not None:
                    logger.debug(f"Leverage mode leverage from account: {account_leverage}")
                    return account_leverage
                else:
                    logger.debug("No account leverage available for leverage mode symbol")
                    return None

            # Other cases: return None
            else:
                logger.debug(f"Unsupported margin_calc_mode for leverage calculation: {margin_calc_mode}")
                return None

        except Exception as e:
            logger.error(f"Error calculating symbol leverage: {str(e)}")
            return None

    async def get_security_list(self, user_id: str, request_id: Optional[str] = None) -> SecurityListResponse:
        try:
            # Get existing FEED session (should already exist from login)
            session = session_manager.get_feed_session(user_id)

            if not session:
                return SecurityListResponse(
                    success=False,
                    message="No active FIX feed session found. Please login first.",
                    error="Feed session not available",
                    symbols=[],
                )

            # Get account leverage for leverage calculations
            account_info = await account_service.get_account_info(user_id)
            logger.debug(f"Account info type: {type(account_info)}, value: {account_info}")

            account_leverage = None
            if account_info:
                if isinstance(account_info, dict):
                    leverage_str = account_info.get("leverage")
                    if leverage_str:
                        try:
                            account_leverage = float(leverage_str)
                        except (ValueError, TypeError):
                            logger.warning(f"Could not convert leverage to float: {leverage_str}")
                            account_leverage = None
                elif isinstance(account_info, tuple) and len(account_info) >= 2:
                    # Handle case where account_info is a tuple (success, data, error)
                    success, data, error = account_info
                    if success and isinstance(data, dict):
                        leverage_str = data.get("leverage")
                        if leverage_str:
                            try:
                                account_leverage = float(leverage_str)
                            except (ValueError, TypeError):
                                logger.warning(f"Could not convert leverage to float: {leverage_str}")
                                account_leverage = None
                    logger.warning(
                        f"Account service returned tuple instead of dict, extracted leverage: {account_leverage}"
                    )
                else:
                    logger.error(f"Expected dict for account_info, got {type(account_info)}: {account_info}")

            logger.debug(f"Account leverage for user {user_id}: {account_leverage}")

            success, response_data, error_message = await session.send_security_list_request(request_id)

            if success and response_data:
                symbols = []

                for symbol_data in response_data.get("symbols", []):
                    symbols.append(
                        SecurityInfo(
                            symbol=symbol_data.get("symbol", ""),
                            security_id=symbol_data.get("security_id"),
                            security_id_source=symbol_data.get("security_id_source"),
                            security_desc=symbol_data.get("security_desc"),
                            currency=symbol_data.get("currency"),
                            settle_currency=symbol_data.get("settle_currency"),
                            trade_enabled=symbol_data.get("trade_enabled"),
                            description=symbol_data.get("description"),
                            # Trading parameters
                            contract_multiplier=symbol_data.get("contract_multiplier"),
                            round_lot=symbol_data.get("round_lot"),
                            min_trade_vol=symbol_data.get("min_trade_vol"),
                            max_trade_volume=symbol_data.get("max_trade_volume"),
                            trade_vol_step=symbol_data.get("trade_vol_step"),
                            px_precision=symbol_data.get("px_precision"),
                            # Currency information
                            currency_precision=symbol_data.get("currency_precision"),
                            currency_sort_order=symbol_data.get("currency_sort_order"),
                            settl_currency_precision=symbol_data.get("settl_currency_precision"),
                            settl_currency_sort_order=symbol_data.get("settl_currency_sort_order"),
                            # Commission and fees
                            commission=symbol_data.get("commission"),
                            limits_commission=symbol_data.get("limits_commission"),
                            comm_type=symbol_data.get("comm_type"),
                            comm_charge_type=symbol_data.get("comm_charge_type"),
                            comm_charge_method=symbol_data.get("comm_charge_method"),
                            min_commission=symbol_data.get("min_commission"),
                            min_commission_currency=symbol_data.get("min_commission_currency"),
                            # Swap information
                            swap_type=symbol_data.get("swap_type"),
                            swap_size_short=symbol_data.get("swap_size_short"),
                            swap_size_long=symbol_data.get("swap_size_long"),
                            triple_swap_day=symbol_data.get("triple_swap_day"),
                            # Margin and risk
                            profit_calc_mode=symbol_data.get("profit_calc_mode"),
                            margin_factor_fractional=symbol_data.get("margin_factor_fractional"),
                            margin_calc_mode=symbol_data.get("margin_calc_mode"),
                            margin_hedge=symbol_data.get("margin_hedge"),
                            margin_factor=symbol_data.get("margin_factor"),
                            stop_order_margin_reduction=symbol_data.get("stop_order_margin_reduction"),
                            hidden_limit_order_margin_reduction=symbol_data.get("hidden_limit_order_margin_reduction"),
                            # Display and grouping
                            description_len=symbol_data.get("description_len"),
                            encoded_security_desc_len=symbol_data.get("encoded_security_desc_len"),
                            encoded_security_desc=symbol_data.get("encoded_security_desc"),
                            color_ref=symbol_data.get("color_ref"),
                            default_slippage=symbol_data.get("default_slippage"),
                            sort_order=symbol_data.get("sort_order"),
                            group_sort_order=symbol_data.get("group_sort_order"),
                            status_group_id=symbol_data.get("status_group_id"),
                            close_only=symbol_data.get("close_only"),
                            # Calculated fields
                            symbol_leverage=self._calculate_symbol_leverage(symbol_data, account_leverage),
                        )
                    )

                return SecurityListResponse(
                    success=True,
                    request_id=response_data.get("request_id"),
                    response_id=response_data.get("response_id"),
                    symbols=symbols,
                    message=f"Retrieved {len(symbols)} trading instruments",
                )
            else:
                return SecurityListResponse(
                    success=False,
                    message="Failed to retrieve security list",
                    error=error_message or "Unknown error",
                    symbols=[],
                )

        except Exception as e:
            logger.error(f"Error in get_security_list for user {user_id}: {str(e)}")
            return SecurityListResponse(
                success=False, message="Internal error occurred", error="Service error", symbols=[]
            )

    async def get_historical_bars(self, user_id: str, request: HistoricalBarsRequest) -> HistoricalBarsResponse:
        try:
            # Get existing FEED session (should already exist from login)
            session = session_manager.get_feed_session(user_id)

            if not session:
                return HistoricalBarsResponse(
                    success=False,
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    price_type=request.price_type,
                    message="No active FIX feed session found. Please login first.",
                    error="Feed session not available",
                    bars=[],
                )

            success, response_data, error_message = await session.send_market_history_request(
                symbol=request.symbol,
                period_id=request.timeframe.value,
                max_bars=request.count,
                end_time=request.to_time,
                price_type=request.price_type.value,
                graph_type="B",  # Always bars for now
            )

            if success and response_data:
                bars = []

                for bar_data in response_data.get("bars", []):
                    try:
                        # Parse the bar timestamp from the FIX format
                        bar_time_str = bar_data.get("bar_time", "")
                        if bar_time_str:
                            # Expected format: YYYYMMDD-HH:MM:SS.sss
                            bar_timestamp = datetime.strptime(bar_time_str, "%Y%m%d-%H:%M:%S.%f")
                        else:
                            logger.warning(f"Missing bar_time for bar: {bar_data}")
                            continue

                        bars.append(
                            HistoricalBar(
                                timestamp=bar_timestamp,
                                open_price=bar_data.get("bar_open", 0.0),
                                high_price=bar_data.get("bar_hi", 0.0),
                                low_price=bar_data.get("bar_low", 0.0),
                                close_price=bar_data.get("bar_close", 0.0),
                                volume=bar_data.get("bar_volume"),
                                volume_ex=bar_data.get("bar_volume_ex"),
                            )
                        )
                    except (ValueError, KeyError) as bar_error:
                        logger.warning(f"Error parsing bar data {bar_data}: {str(bar_error)}")
                        continue

                # Parse datetime fields if present
                from_time = None
                to_time = None

                try:
                    if response_data.get("data_from"):
                        from_time = datetime.strptime(response_data["data_from"], "%Y%m%d-%H:%M:%S.%f")
                except (ValueError, TypeError):
                    pass

                try:
                    if response_data.get("data_to"):
                        to_time = datetime.strptime(response_data["data_to"], "%Y%m%d-%H:%M:%S.%f")
                except (ValueError, TypeError):
                    pass

                return HistoricalBarsResponse(
                    success=True,
                    request_id=response_data.get("request_id"),
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    price_type=request.price_type,
                    from_time=from_time,
                    to_time=to_time,
                    bars=bars,
                    message=f"Retrieved {len(bars)} historical bars for {request.symbol}",
                )
            else:
                return HistoricalBarsResponse(
                    success=False,
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    price_type=request.price_type,
                    message="Failed to retrieve historical bars",
                    error=error_message or "Unknown error",
                    bars=[],
                )

        except Exception as e:
            logger.error(f"Error in get_historical_bars for user {user_id}: {str(e)}")
            return HistoricalBarsResponse(
                success=False,
                symbol=request.symbol,
                timeframe=request.timeframe,
                price_type=request.price_type,
                message="Internal error occurred",
                error="Service error",
                bars=[],
            )
