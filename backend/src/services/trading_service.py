import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from ..adapters.process_fix_adapter import ProcessFIXAdapter
from ..core.fix_translation_system import FIXTranslationSystem
from ..schemas.modern_trading_schemas import ModernOrderResponse, OrderManagementResponse, PossibleOrderOutcomes
from ..schemas.trading_schemas import (
    LimitOrderRequest,
    MarketOrderRequest,
    NewOrderRequest,
    OrderCancelRequest,
    OrderModifyRequest,
)
from ..schemas.trading_schemas import OrderSide as FixOrderSide
from ..schemas.trading_schemas import OrderType as FixOrderType
from ..schemas.trading_schemas import StopLimitOrderRequest, StopOrderRequest
from ..schemas.trading_schemas import TimeInForce as FixTimeInForce
from ..services.modern_response_converter import ModernResponseConverter

logger = logging.getLogger(__name__)


class TradingService:
    def __init__(self, fix_adapter: ProcessFIXAdapter):
        self.fix_adapter = fix_adapter

    def _generate_client_order_id(self) -> str:
        return f"ORD_{int(time.time() * 1000000)}"

    def place_market_order(self, request: MarketOrderRequest, user_id: str) -> ModernOrderResponse:
        client_order_id = self._generate_client_order_id()
        start_time = time.time()

        try:
            success, exec_data, error = self.fix_adapter.send_new_order_single(
                user_id=user_id,
                client_order_id=client_order_id,
                symbol=request.symbol,
                order_type=FixOrderType.MARKET.value,
                side=request.side.value,
                quantity=request.quantity,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                comment=request.comment,
                tag=request.tag,
                magic=request.magic,
                slippage=request.slippage,
            )

            return ModernResponseConverter.convert_order_response(
                success=success,
                client_order_id=client_order_id,
                exec_data=exec_data,
                error=error,
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"Market order placement failed: {e}")
            return ModernResponseConverter.convert_order_response(
                success=False, client_order_id=client_order_id, exec_data=None, error=str(e), start_time=start_time
            )

    def place_limit_order(self, request: LimitOrderRequest, user_id: str) -> ModernOrderResponse:
        client_order_id = self._generate_client_order_id()
        start_time = time.time()

        try:
            success, exec_data, error = self.fix_adapter.send_new_order_single(
                user_id=user_id,
                client_order_id=client_order_id,
                symbol=request.symbol,
                order_type=FixOrderType.LIMIT.value,
                side=request.side.value,
                quantity=request.quantity,
                price=request.price,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                time_in_force=request.time_in_force.value,
                expire_time=request.expire_time,
                max_visible_qty=request.max_visible_qty,
                comment=request.comment,
                tag=request.tag,
                magic=request.magic,
                immediate_or_cancel=request.immediate_or_cancel,
                market_with_slippage=request.market_with_slippage,
            )

            return ModernResponseConverter.convert_order_response(
                success=success,
                client_order_id=client_order_id,
                exec_data=exec_data,
                error=error,
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"Limit order placement failed: {e}")
            return ModernResponseConverter.convert_order_response(
                success=False, client_order_id=client_order_id, exec_data=None, error=str(e), start_time=start_time
            )

    def place_stop_order(self, request: StopOrderRequest, user_id: str) -> ModernOrderResponse:
        client_order_id = self._generate_client_order_id()
        start_time = time.time()

        try:
            success, exec_data, error = self.fix_adapter.send_new_order_single(
                user_id=user_id,
                client_order_id=client_order_id,
                symbol=request.symbol,
                order_type=FixOrderType.STOP.value,
                side=request.side.value,
                quantity=request.quantity,
                stop_price=request.stop_price,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                time_in_force=request.time_in_force.value,
                expire_time=request.expire_time,
                comment=request.comment,
                tag=request.tag,
                magic=request.magic,
            )

            return ModernResponseConverter.convert_order_response(
                success=success,
                client_order_id=client_order_id,
                exec_data=exec_data,
                error=error,
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"Stop order placement failed: {e}")
            return ModernResponseConverter.convert_order_response(
                success=False, client_order_id=client_order_id, exec_data=None, error=str(e), start_time=start_time
            )

    def place_stop_limit_order(self, request: StopLimitOrderRequest, user_id: str) -> ModernOrderResponse:
        client_order_id = self._generate_client_order_id()
        start_time = time.time()

        try:
            success, exec_data, error = self.fix_adapter.send_new_order_single(
                user_id=user_id,
                client_order_id=client_order_id,
                symbol=request.symbol,
                order_type=FixOrderType.STOP_LIMIT.value,
                side=request.side.value,
                quantity=request.quantity,
                price=request.price,
                stop_price=request.stop_price,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                time_in_force=request.time_in_force.value,
                expire_time=request.expire_time,
                max_visible_qty=request.max_visible_qty,
                comment=request.comment,
                tag=request.tag,
                magic=request.magic,
                immediate_or_cancel=request.immediate_or_cancel,
            )

            return ModernResponseConverter.convert_order_response(
                success=success,
                client_order_id=client_order_id,
                exec_data=exec_data,
                error=error,
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"Stop-limit order placement failed: {e}")
            return ModernResponseConverter.convert_order_response(
                success=False, client_order_id=client_order_id, exec_data=None, error=str(e), start_time=start_time
            )

    def place_order(self, request: NewOrderRequest, user_id: str) -> ModernOrderResponse:
        client_order_id = self._generate_client_order_id()
        start_time = time.time()

        try:
            success, exec_data, error = self.fix_adapter.send_new_order_single(
                user_id=user_id,
                client_order_id=client_order_id,
                symbol=request.symbol,
                order_type=request.order_type.value,
                side=request.side.value,
                quantity=request.quantity,
                price=request.price,
                stop_price=request.stop_price,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                time_in_force=request.time_in_force.value,
                expire_time=request.expire_time,
                max_visible_qty=request.max_visible_qty,
                comment=request.comment,
                tag=request.tag,
                magic=request.magic,
                immediate_or_cancel=request.immediate_or_cancel,
                market_with_slippage=request.market_with_slippage,
                slippage=request.slippage,
            )

            return ModernResponseConverter.convert_order_response(
                success=success,
                client_order_id=client_order_id,
                exec_data=exec_data,
                error=error,
                start_time=start_time,
            )

        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return ModernResponseConverter.convert_order_response(
                success=False, client_order_id=client_order_id, exec_data=None, error=str(e), start_time=start_time
            )

    def cancel_order(self, request: OrderCancelRequest, user_id: str) -> OrderManagementResponse:
        client_order_id = self._generate_client_order_id()

        try:
            success, exec_data, error = self.fix_adapter.send_order_cancel_request(
                user_id=user_id,
                client_order_id=client_order_id,
                original_client_order_id=request.original_client_order_id or request.order_id,
                symbol=request.symbol,
                side=request.side.value,
                order_id=request.order_id,
            )

            return ModernResponseConverter.convert_management_response(
                success=success,
                operation="cancel",
                order_id=request.order_id,
                client_order_id=client_order_id,
                exec_data=exec_data,
                error=error,
            )

        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return ModernResponseConverter.convert_management_response(
                success=False,
                operation="cancel",
                order_id=request.order_id,
                client_order_id=client_order_id,
                error=str(e),
            )

    def modify_order(self, request: OrderModifyRequest, user_id: str) -> OrderManagementResponse:
        client_order_id = self._generate_client_order_id()

        try:
            if not any(
                [
                    request.new_quantity,
                    request.new_price,
                    request.new_stop_price,
                    request.new_stop_loss,
                    request.new_take_profit,
                    request.new_time_in_force,
                    request.new_expire_time,
                    request.new_comment,
                    request.new_tag,
                ]
            ):
                return ModernResponseConverter.convert_management_response(
                    success=False,
                    operation="modify",
                    order_id=request.order_id,
                    client_order_id=client_order_id,
                    error="At least one field must be modified",
                )

            success, exec_data, error = self.fix_adapter.send_order_cancel_replace_request(
                user_id=user_id,
                client_order_id=client_order_id,
                original_client_order_id=request.original_client_order_id or request.order_id,
                symbol=request.symbol,
                side=request.side.value,
                order_type="2",
                quantity=request.new_quantity or 0.0,
                price=request.new_price,
                stop_price=request.new_stop_price,
                stop_loss=request.new_stop_loss,
                take_profit=request.new_take_profit,
                time_in_force=request.new_time_in_force.value if request.new_time_in_force else "1",
                expire_time=request.new_expire_time,
                comment=request.new_comment,
                tag=request.new_tag,
                leaves_qty=request.leaves_qty,
                order_id=request.order_id,
            )

            return ModernResponseConverter.convert_management_response(
                success=success,
                operation="modify",
                order_id=request.order_id,
                client_order_id=client_order_id,
                exec_data=exec_data,
                error=error,
            )

        except Exception as e:
            logger.error(f"Order modification failed: {e}")
            return ModernResponseConverter.convert_management_response(
                success=False,
                operation="modify",
                order_id=request.order_id,
                client_order_id=client_order_id,
                error=str(e),
            )

    @staticmethod
    def get_possible_order_outcomes() -> PossibleOrderOutcomes:
        """Get documentation of possible order outcomes for API users"""
        return PossibleOrderOutcomes(
            immediate_outcomes=[
                f"{status} - {desc}"
                for status, desc in FIXTranslationSystem.get_all_possible_statuses().items()
                if status in ["pending", "filled", "partial", "rejected"]
            ],
            eventual_outcomes=[
                f"{status} - {desc}" for status, desc in FIXTranslationSystem.get_all_possible_statuses().items()
            ],
            rejection_reasons=[
                f"{reason} - {desc}" for reason, desc in FIXTranslationSystem.get_all_rejection_reasons().items()
            ],
        )
