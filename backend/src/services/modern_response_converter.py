import time
from datetime import datetime
from typing import Any, Dict, Optional

from ..core.fix_translation_system import (
    FIXTranslationSystem,
    ModernOrderSide,
    ModernOrderStatus,
    ModernOrderType,
    ModernRejectionReason,
    ModernTimeInForce,
)
from ..schemas.modern_trading_schemas import ExecutionDetails, ModernOrderResponse, OrderInfo, OrderManagementResponse


class ModernResponseConverter:
    """Converts FIX protocol responses to modern API responses"""

    # All methods now delegate to the centralized FIX translation system

    @classmethod
    def convert_order_response(
        cls,
        success: bool,
        client_order_id: str,
        exec_data: Optional[Dict[str, Any]],
        error: Optional[str] = None,
        start_time: Optional[float] = None,
    ) -> ModernOrderResponse:
        """Convert FIX execution report to modern order response using centralized translation"""

        processing_time = None
        if start_time:
            processing_time = int((time.time() - start_time) * 1000)

        if not success or not exec_data:
            error_message = error or "Unknown error occurred"
            return ModernOrderResponse(
                success=False,
                client_order_id=client_order_id,
                status=ModernOrderStatus.REJECTED,
                status_message="Order request failed",
                message="Order request failed",  # Backward compatibility
                error_message=error_message,
                processing_time_ms=processing_time,
            )

        # Use centralized translation system
        converted_data = FIXTranslationSystem.convert_fix_order_data(exec_data)
        modern_status = converted_data["modern_status"]
        status_message = FIXTranslationSystem.generate_status_message(modern_status, exec_data)

        # Build order info using centralized translations
        order_info = OrderInfo(
            order_id=exec_data.get("order_id", ""),
            client_order_id=client_order_id,
            symbol=exec_data.get("symbol", ""),
            order_type=converted_data.get("modern_order_type", ModernOrderType.MARKET),
            side=converted_data.get("modern_side", ModernOrderSide.BUY),
            original_quantity=exec_data.get("order_qty", 0.0),
            price=exec_data.get("price"),
            stop_price=exec_data.get("stop_price"),
            time_in_force=converted_data.get("modern_tif", ModernTimeInForce.GTC),
            expire_time=converted_data.get("parsed_expire_time"),
            stop_loss=exec_data.get("stop_loss"),
            take_profit=exec_data.get("take_profit"),
            comment=exec_data.get("comment"),
            tag=exec_data.get("tag"),
            magic=exec_data.get("magic"),
            created_at=converted_data.get("parsed_order_created") or datetime.utcnow(),
            updated_at=converted_data.get("parsed_order_modified"),
        )

        # Build execution details if applicable
        execution_details = None
        if modern_status in [ModernOrderStatus.FILLED, ModernOrderStatus.PARTIALLY_FILLED]:
            execution_details = ExecutionDetails(
                executed_quantity=exec_data.get("cum_qty", 0.0),
                remaining_quantity=exec_data.get("leaves_qty", 0.0),
                average_price=exec_data.get("avg_price"),
                last_execution_price=exec_data.get("last_price"),
                last_execution_quantity=exec_data.get("last_qty"),
                total_executions=1 if exec_data.get("cum_qty", 0) > 0 else 0,
            )

        # Handle rejection using centralized translation
        rejection_reason = None
        if modern_status == ModernOrderStatus.REJECTED:
            rejection_reason = converted_data.get("modern_rejection", ModernRejectionReason.OTHER)

        # Create backward-compatible execution report
        execution_report = None
        if success and exec_data:
            execution_report = {
                "order_id": exec_data.get("order_id", ""),
                "client_order_id": client_order_id,
                "exec_id": exec_data.get("exec_id", ""),
                "order_status": exec_data.get("order_status", ""),
                "exec_type": exec_data.get("exec_type", ""),
                "symbol": exec_data.get("symbol", ""),
                "side": exec_data.get("side", ""),
                "order_type": exec_data.get("order_type", ""),
                "order_qty": exec_data.get("order_qty", 0.0),
                "cum_qty": exec_data.get("cum_qty", 0.0),
                "leaves_qty": exec_data.get("leaves_qty", 0.0),
                "avg_price": exec_data.get("avg_price"),
                "price": exec_data.get("price"),
                "stop_price": exec_data.get("stop_price"),
                "last_qty": exec_data.get("last_qty"),
                "last_price": exec_data.get("last_price"),
                "transact_time": exec_data.get("transact_time"),
                "time_in_force": exec_data.get("time_in_force"),
                "expire_time": exec_data.get("expire_time"),
                "stop_loss": exec_data.get("stop_loss"),
                "take_profit": exec_data.get("take_profit"),
                "commission": exec_data.get("commission"),
                "swap": exec_data.get("swap"),
                "account_balance": exec_data.get("account_balance"),
                "comment": exec_data.get("comment"),
                "tag": exec_data.get("tag"),
                "magic": exec_data.get("magic"),
            }

        return ModernOrderResponse(
            success=True,  # Request was processed successfully
            order_id=exec_data.get("order_id"),
            client_order_id=client_order_id,
            status=modern_status,
            status_message=status_message,
            message=status_message,  # Backward compatibility
            execution_report=execution_report,  # Backward compatibility
            order_info=order_info,
            execution_details=execution_details,
            rejection_reason=rejection_reason,
            account_balance=exec_data.get("account_balance"),
            commission=exec_data.get("commission"),
            swap=exec_data.get("swap"),
            processing_time_ms=processing_time,
        )

    @classmethod
    def convert_management_response(
        cls,
        success: bool,
        operation: str,
        order_id: str,
        client_order_id: str,
        exec_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> OrderManagementResponse:
        """Convert order management response to modern format using centralized translation"""

        if not success:
            return OrderManagementResponse(
                success=False,
                order_id=order_id,
                client_order_id=client_order_id,
                operation=operation,
                status=ModernOrderStatus.REJECTED,
                status_message=f"Failed to {operation} order",
                error_message=error or "Unknown error occurred",
            )

        # If we have execution data, use centralized translation
        if exec_data:
            converted_data = FIXTranslationSystem.convert_fix_order_data(exec_data)
            modern_status = converted_data["modern_status"]
            status_message = FIXTranslationSystem.generate_status_message(modern_status, exec_data)
        else:
            # Default status based on operation
            if operation == "cancel":
                modern_status = ModernOrderStatus.CANCELLING
                status_message = f"Order {order_id} cancellation request sent"
            elif operation == "modify":
                modern_status = ModernOrderStatus.MODIFYING
                status_message = f"Order {order_id} modification request sent"
            else:
                modern_status = ModernOrderStatus.PENDING
                status_message = f"Order {operation} request processed"

        return OrderManagementResponse(
            success=True,
            order_id=order_id,
            client_order_id=client_order_id,
            operation=operation,
            status=modern_status,
            status_message=status_message,
        )
