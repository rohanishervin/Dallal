import logging
import time
from datetime import datetime
from typing import Dict, List

from ..adapters.process_fix_adapter import ProcessFIXAdapter
from ..core.fix_translation_system import FIXTranslationSystem
from ..schemas.positions_schemas import OpenPosition, OpenPositionsResponse

logger = logging.getLogger(__name__)


class PositionsService:
    def __init__(self, fix_adapter: ProcessFIXAdapter):
        self.fix_adapter = fix_adapter

    def _generate_request_id(self) -> str:
        """Generate unique request ID for positions requests"""
        return f"POS_{int(time.time() * 1000000)}"

    async def get_open_positions(self, user_id: str, account_id: str) -> OpenPositionsResponse:
        """Get all currently open positions using Order Mass Status Request (same as orders, but filtering for positions)"""
        request_id = self._generate_request_id()
        start_time = time.time()

        try:
            # Send Order Mass Status Request (AF) via FIX - same as orders endpoint
            # We'll filter for positions (OrdType='N') from the Execution Reports
            success, raw_data, error = await self.fix_adapter.send_order_mass_status_request(
                user_id=user_id, request_id=request_id
            )

            processing_time = int((time.time() - start_time) * 1000)

            if not success:
                logger.error(f"Order mass status request failed: {error}")
                return OpenPositionsResponse(
                    success=False,
                    positions=[],
                    total_positions=0,
                    positions_by_type={},
                    positions_by_symbol={},
                    message=f"Failed to retrieve positions: {error}",
                    request_id=request_id,
                    request_result="unknown",
                    request_status="rejected",
                    processing_time_ms=processing_time,
                )

            # Extract orders from Order Mass Status Request - we'll filter for positions
            fix_orders = raw_data.get("orders", [])

            # Filter for positions (OrdType='N') and convert to position format
            positions = self._convert_fix_orders_to_positions(fix_orders)

            # Generate summary statistics
            positions_by_type = self._group_positions_by_type(positions)
            positions_by_symbol = self._group_positions_by_symbol(positions)

            # Calculate financial summaries
            financial_summary = self._calculate_financial_summary(positions)

            message = f"Retrieved {len(positions)} open positions"
            if len(positions) == 0:
                message = "No open positions found"

            return OpenPositionsResponse(
                success=True,
                positions=positions,
                total_positions=len(positions),
                positions_by_type=positions_by_type,
                positions_by_symbol=positions_by_symbol,
                total_unrealized_pnl=financial_summary["total_unrealized_pnl"],
                total_realized_pnl=financial_summary["total_realized_pnl"],
                total_commission=financial_summary["total_commission"],
                total_swap=financial_summary["total_swap"],
                message=message,
                request_id=request_id,
                request_result="valid_request",
                request_status="completed",
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Positions service error: {e}")
            return OpenPositionsResponse(
                success=False,
                positions=[],
                total_positions=0,
                positions_by_type={},
                positions_by_symbol={},
                message=f"Internal error retrieving positions: {str(e)}",
                request_id=request_id,
                request_result="unknown",
                request_status="rejected",
                processing_time_ms=processing_time,
            )

    def _convert_fix_orders_to_positions(self, fix_orders: List[Dict]) -> List[OpenPosition]:
        """Convert FIX order data to positions, filtering for OrdType='N' (Position type)"""
        modern_positions = []

        for fix_order in fix_orders:
            try:
                # Only process orders that are actually positions (OrdType='N')
                order_type = fix_order.get("order_type", "")
                if order_type != "N":
                    continue

                # Use centralized FIX translation system
                converted_data = FIXTranslationSystem.convert_fix_order_data(fix_order)

                # For positions, we need to interpret the order fields as position data
                # Quantities for positions come from the order quantity fields
                original_qty = float(fix_order.get("order_qty", 0))
                executed_qty = float(fix_order.get("cum_qty", 0))
                remaining_qty = float(fix_order.get("leaves_qty", 0))

                # For positions, the "remaining quantity" is the current open position
                net_qty = remaining_qty

                # Skip positions with zero quantity
                if abs(net_qty) <= 0.0000001:
                    logger.debug(f"Skipping position {fix_order.get('order_id', 'unknown')} with zero net quantity")
                    continue

                # Determine position type from side and quantity
                side = fix_order.get("side", "1")
                if side == "1":  # Buy side = Long position
                    long_qty = abs(net_qty)
                    short_qty = 0.0
                    position_type = "long"
                else:  # Sell side = Short position
                    long_qty = 0.0
                    short_qty = abs(net_qty)
                    position_type = "short"

                # Create OpenPosition object with modern fields
                position = OpenPosition(
                    position_id=fix_order.get("order_id", ""),  # Use OrderID as position ID
                    symbol=fix_order.get("symbol", ""),
                    currency=fix_order.get("symbol", "").split("/")[0] if "/" in fix_order.get("symbol", "") else "",
                    # Position type and status
                    position_type=position_type,
                    status="open",  # Positions from Order Mass Status are open
                    # Position quantities
                    net_quantity=net_qty,
                    long_quantity=long_qty,
                    short_quantity=short_qty,
                    # Position prices
                    average_price=self._safe_float(fix_order.get("avg_price"))
                    or self._safe_float(fix_order.get("price")),
                    long_average_price=self._safe_float(fix_order.get("avg_price")) if side == "1" else None,
                    short_average_price=self._safe_float(fix_order.get("avg_price")) if side == "2" else None,
                    # Financial information
                    commission=self._safe_float(fix_order.get("commission")),
                    commission_currency=fix_order.get("acc_tr_curry"),
                    agent_commission=self._safe_float(fix_order.get("agent_commission")),
                    agent_commission_currency=fix_order.get("acc_tr_curry"),
                    swap=self._safe_float(fix_order.get("swap")),
                    # Account information
                    account_balance=self._safe_float(fix_order.get("account_balance")),
                    transaction_amount=self._safe_float(fix_order.get("acc_tr_amount")),
                    transaction_currency=fix_order.get("acc_tr_curry"),
                    # Metadata
                    report_type="response",
                    # Timestamps
                    created_at=converted_data.get("parsed_order_created") or datetime.utcnow(),
                    clearing_date=None,
                )

                modern_positions.append(position)

            except Exception as e:
                logger.warning(f"Failed to convert position from order {fix_order.get('order_id', 'unknown')}: {e}")
                continue

        return modern_positions

    def _group_positions_by_type(self, positions: List[OpenPosition]) -> Dict[str, int]:
        """Group positions by type for summary statistics"""
        type_counts = {}
        for position in positions:
            pos_type = (
                position.position_type.value
                if hasattr(position.position_type, "value")
                else str(position.position_type)
            )
            type_counts[pos_type] = type_counts.get(pos_type, 0) + 1
        return type_counts

    def _group_positions_by_symbol(self, positions: List[OpenPosition]) -> Dict[str, int]:
        """Group positions by symbol for summary statistics"""
        symbol_counts = {}
        for position in positions:
            symbol = position.symbol
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        return symbol_counts

    def _calculate_financial_summary(self, positions: List[OpenPosition]) -> Dict[str, float]:
        """Calculate financial summary across all positions"""
        summary = {"total_unrealized_pnl": 0.0, "total_realized_pnl": 0.0, "total_commission": 0.0, "total_swap": 0.0}

        for position in positions:
            if position.unrealized_pnl:
                summary["total_unrealized_pnl"] += position.unrealized_pnl
            if position.realized_pnl:
                summary["total_realized_pnl"] += position.realized_pnl
            if position.commission:
                summary["total_commission"] += position.commission
            if position.swap:
                summary["total_swap"] += position.swap

        return summary

    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
