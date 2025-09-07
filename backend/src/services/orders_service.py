import logging
import time
from datetime import datetime
from typing import Dict, List

from ..adapters.process_fix_adapter import ProcessFIXAdapter
from ..core.fix_translation_system import FIXTranslationSystem
from ..schemas.orders_schemas import OpenOrder, OpenOrdersResponse

logger = logging.getLogger(__name__)


class OrdersService:
    def __init__(self, fix_adapter: ProcessFIXAdapter):
        self.fix_adapter = fix_adapter

    def _generate_request_id(self) -> str:
        """Generate unique request ID for mass status requests"""
        return f"MSR_{int(time.time() * 1000000)}"

    async def get_open_orders(self, user_id: str) -> OpenOrdersResponse:
        """Get all currently open orders using Order Mass Status Request"""
        request_id = self._generate_request_id()
        start_time = time.time()

        try:
            # Send Order Mass Status Request (AF) via FIX
            success, raw_data, error = await self.fix_adapter.send_order_mass_status_request(
                user_id=user_id, request_id=request_id
            )

            processing_time = int((time.time() - start_time) * 1000)

            if not success:
                logger.error(f"Order mass status request failed: {error}")
                return OpenOrdersResponse(
                    success=False,
                    orders=[],
                    total_orders=0,
                    orders_by_status={},
                    orders_by_symbol={},
                    message=f"Failed to retrieve open orders: {error}",
                    request_id=request_id,
                    processing_time_ms=processing_time,
                )

            # Process the raw FIX data using centralized translation system
            orders = self._convert_fix_orders_to_modern(raw_data.get("orders", []))

            # Generate summary statistics
            orders_by_status = self._group_orders_by_status(orders)
            orders_by_symbol = self._group_orders_by_symbol(orders)

            message = f"Retrieved {len(orders)} open orders"
            if len(orders) == 0:
                message = "No open orders found"

            return OpenOrdersResponse(
                success=True,
                orders=orders,
                total_orders=len(orders),
                orders_by_status=orders_by_status,
                orders_by_symbol=orders_by_symbol,
                message=message,
                request_id=request_id,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Orders service error: {e}")
            return OpenOrdersResponse(
                success=False,
                orders=[],
                total_orders=0,
                orders_by_status={},
                orders_by_symbol={},
                message=f"Internal error retrieving orders: {str(e)}",
                request_id=request_id,
                processing_time_ms=processing_time,
            )

    def _convert_fix_orders_to_modern(self, fix_orders: List[Dict]) -> List[OpenOrder]:
        """Convert FIX order data to modern format using centralized translation system"""
        modern_orders = []

        for fix_order in fix_orders:
            try:
                # Use centralized FIX translation system
                converted_data = FIXTranslationSystem.convert_fix_order_data(fix_order)

                # Get the modern status
                modern_status = converted_data.get("modern_status", "pending")

                # Filter out non-order types (positions have OrdType='N')
                order_type_raw = fix_order.get("order_type", "")
                if order_type_raw == "N":
                    logger.debug(f"Skipping position {fix_order.get('client_order_id', 'unknown')} (OrdType='N')")
                    continue

                # Determine the actual status based on multiple factors
                # According to FIX documentation, we need to consider both status and quantities
                remaining_qty = float(fix_order.get("leaves_qty", 0))
                executed_qty = float(fix_order.get("cum_qty", 0))
                original_qty = float(fix_order.get("order_qty", 0))

                # Override status based on execution state
                actual_status = self._determine_actual_order_status(
                    modern_status, remaining_qty, executed_qty, original_qty, fix_order
                )

                # Only include orders that are actually "open" (not filled, cancelled, or rejected)
                if actual_status in ["filled", "cancelled", "rejected", "expired"]:
                    logger.debug(
                        f"Skipping order {fix_order.get('client_order_id', 'unknown')} with status {actual_status}"
                    )
                    continue

                # Create OpenOrder object with modern fields
                order = OpenOrder(
                    order_id=fix_order.get("order_id", ""),
                    client_order_id=fix_order.get("client_order_id", ""),
                    symbol=fix_order.get("symbol", ""),
                    # Use translated modern values
                    order_type=converted_data.get("modern_order_type", "market"),
                    side=converted_data.get("modern_side", "buy"),
                    status=actual_status,
                    # Quantities
                    original_quantity=float(fix_order.get("order_qty", 0)),
                    remaining_quantity=remaining_qty,
                    executed_quantity=float(fix_order.get("cum_qty", 0)),
                    # Prices
                    price=self._safe_float(fix_order.get("price")),
                    stop_price=self._safe_float(fix_order.get("stop_price")),
                    average_price=self._safe_float(fix_order.get("avg_price")),
                    # Order management
                    time_in_force=converted_data.get("modern_tif", "gtc"),
                    expire_time=converted_data.get("parsed_expire_time"),
                    # Risk management
                    stop_loss=self._safe_float(fix_order.get("stop_loss")),
                    take_profit=self._safe_float(fix_order.get("take_profit")),
                    # Order flags and features
                    max_visible_quantity=self._safe_float(fix_order.get("max_visible_qty")),
                    immediate_or_cancel=self._safe_bool(fix_order.get("immediate_or_cancel_flag")),
                    market_with_slippage=self._safe_bool(fix_order.get("market_with_slippage_flag")),
                    # Financial details
                    commission=self._safe_float(fix_order.get("commission")),
                    swap=self._safe_float(fix_order.get("swap")),
                    slippage=self._safe_float(fix_order.get("slippage")),
                    # Rejection information
                    rejection_reason=converted_data.get("modern_rejection") if actual_status == "rejected" else None,
                    # Metadata
                    comment=fix_order.get("comment"),
                    tag=fix_order.get("tag"),
                    magic=self._safe_int(fix_order.get("magic")),
                    parent_order_id=fix_order.get("parent_order_id"),
                    # Timestamps
                    created_at=converted_data.get("parsed_order_created") or datetime.utcnow(),
                    updated_at=converted_data.get("parsed_order_modified"),
                )

                modern_orders.append(order)

            except Exception as e:
                logger.warning(f"Failed to convert order {fix_order.get('client_order_id', 'unknown')}: {e}")
                continue

        return modern_orders

    def _determine_actual_order_status(
        self, fix_status: str, remaining_qty: float, executed_qty: float, original_qty: float, fix_order: Dict
    ) -> str:
        """
        Determine the actual order status based on FIX status and execution quantities.
        This handles cases where FIX status might not reflect the true execution state.
        """
        # Check for completely filled orders
        if executed_qty >= original_qty and remaining_qty <= 0.0000001:
            return "filled"

        # Check for partially filled orders
        if executed_qty > 0 and remaining_qty > 0.0000001:
            return "partial"

        # Check for orders with average price but showing as pending (execution happened)
        avg_price = fix_order.get("avg_price")
        if avg_price and float(avg_price) > 0 and executed_qty <= 0:
            # This suggests the order was executed but quantities not updated properly
            # This can happen with certain FIX implementations
            return "filled"

        # For market orders with price but no execution quantity, likely filled
        order_type = fix_order.get("order_type", "")
        if order_type == "1" and avg_price and float(avg_price) > 0:  # Market order with avg price
            return "filled"

        # Use the original FIX status translation
        return fix_status

    def _group_orders_by_status(self, orders: List[OpenOrder]) -> Dict[str, int]:
        """Group orders by status for summary statistics"""
        status_counts = {}
        for order in orders:
            status = order.status.value if hasattr(order.status, "value") else str(order.status)
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    def _group_orders_by_symbol(self, orders: List[OpenOrder]) -> Dict[str, int]:
        """Group orders by symbol for summary statistics"""
        symbol_counts = {}
        for order in orders:
            symbol = order.symbol
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        return symbol_counts

    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value) -> int:
        """Safely convert value to int"""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _safe_bool(self, value) -> bool:
        """Safely convert value to bool"""
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.upper() in ["Y", "YES", "1", "TRUE"]
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            return None
