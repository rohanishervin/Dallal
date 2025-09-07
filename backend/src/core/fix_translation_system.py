"""
Centralized FIX Protocol Translation System

This module provides the single source of truth for translating FIX protocol codes
and messages into modern, user-friendly API responses. All FIX-related translations
should go through this system to ensure consistency across the application.

Usage:
    from src.core.fix_translation_system import FIXTranslationSystem
    
    # Translate order status
    modern_status = FIXTranslationSystem.translate_order_status("8")  # Returns "rejected"
    
    # Get human readable message
    message = FIXTranslationSystem.get_status_message("rejected", order_data)
    
    # Convert complete FIX response
    modern_response = FIXTranslationSystem.convert_order_response(fix_data)
"""

import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ModernOrderStatus(str, Enum):
    """Modern order status - completely abstracted from FIX codes"""

    PENDING = "pending"  # Order accepted, waiting for execution
    PARTIALLY_FILLED = "partial"  # Order partially executed
    FILLED = "filled"  # Order completely executed
    CANCELLED = "cancelled"  # Order cancelled by user or system
    REJECTED = "rejected"  # Order rejected by broker/market
    EXPIRED = "expired"  # Order expired (GTD orders)
    CANCELLING = "cancelling"  # Cancel request in progress
    MODIFYING = "modifying"  # Modification request in progress


class ModernRejectionReason(str, Enum):
    """Modern rejection reasons"""

    MARKET_CLOSED = "market_closed"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_SYMBOL = "invalid_symbol"
    INVALID_PRICE = "invalid_price"
    INVALID_QUANTITY = "invalid_quantity"
    ORDER_LIMITS_EXCEEDED = "order_limits_exceeded"
    DUPLICATE_ORDER = "duplicate_order"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    TIMEOUT = "timeout"
    UNSUPPORTED_ORDER = "unsupported_order"
    SYSTEM_ERROR = "system_error"
    OTHER = "other"


class ModernOrderType(str, Enum):
    """Modern order types"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class ModernOrderSide(str, Enum):
    """Modern order sides"""

    BUY = "buy"
    SELL = "sell"


class ModernTimeInForce(str, Enum):
    """Modern time in force options"""

    GTC = "gtc"  # Good Till Cancel
    IOC = "ioc"  # Immediate or Cancel
    GTD = "gtd"  # Good Till Date


class FIXTranslationSystem:
    """
    Centralized system for translating FIX protocol codes to modern API responses.

    This class serves as the single source of truth for all FIX translations.
    All modules that need to translate FIX codes should use this system.
    """

    # FIX to Modern Status Mapping
    FIX_STATUS_MAP = {
        "0": ModernOrderStatus.PENDING,  # New
        "1": ModernOrderStatus.PARTIALLY_FILLED,  # Partially filled
        "2": ModernOrderStatus.FILLED,  # Filled
        "3": ModernOrderStatus.FILLED,  # Done (treat as filled)
        "4": ModernOrderStatus.CANCELLED,  # Cancelled
        "6": ModernOrderStatus.CANCELLING,  # Pending cancel
        "8": ModernOrderStatus.REJECTED,  # Rejected
        "B": ModernOrderStatus.PENDING,  # Calculated (treat as pending)
        "C": ModernOrderStatus.EXPIRED,  # Expired
        "E": ModernOrderStatus.MODIFYING,  # Pending replacement
        "F": ModernOrderStatus.CANCELLING,  # Pending close
    }

    # FIX to Modern Rejection Reason Mapping
    FIX_REJECTION_MAP = {
        "0": ModernRejectionReason.MARKET_CLOSED,
        "1": ModernRejectionReason.INVALID_SYMBOL,
        "3": ModernRejectionReason.ORDER_LIMITS_EXCEEDED,
        "4": ModernRejectionReason.INVALID_PRICE,
        "5": ModernRejectionReason.SYSTEM_ERROR,
        "6": ModernRejectionReason.DUPLICATE_ORDER,
        "11": ModernRejectionReason.UNSUPPORTED_ORDER,
        "13": ModernRejectionReason.INVALID_QUANTITY,
        "16": ModernRejectionReason.RATE_LIMIT_EXCEEDED,
        "17": ModernRejectionReason.TIMEOUT,
        "18": ModernRejectionReason.MARKET_CLOSED,
        "99": ModernRejectionReason.OTHER,
    }

    # FIX to Modern Order Type Mapping
    FIX_ORDER_TYPE_MAP = {
        "1": ModernOrderType.MARKET,
        "2": ModernOrderType.LIMIT,
        "3": ModernOrderType.STOP,
        "4": ModernOrderType.STOP_LIMIT,
    }

    # FIX to Modern Side Mapping
    FIX_SIDE_MAP = {
        "1": ModernOrderSide.BUY,
        "2": ModernOrderSide.SELL,
    }

    # FIX to Modern Time in Force Mapping
    FIX_TIF_MAP = {
        "1": ModernTimeInForce.GTC,
        "3": ModernTimeInForce.IOC,
        "6": ModernTimeInForce.GTD,
    }

    # Human-readable rejection reason descriptions
    REJECTION_DESCRIPTIONS = {
        ModernRejectionReason.MARKET_CLOSED: "Market is currently closed for trading",
        ModernRejectionReason.INSUFFICIENT_FUNDS: "Not enough balance or margin available",
        ModernRejectionReason.INVALID_SYMBOL: "Invalid or unknown trading symbol",
        ModernRejectionReason.INVALID_PRICE: "Price is outside acceptable range",
        ModernRejectionReason.INVALID_QUANTITY: "Order quantity is invalid",
        ModernRejectionReason.ORDER_LIMITS_EXCEEDED: "Order exceeds position or risk limits",
        ModernRejectionReason.DUPLICATE_ORDER: "Duplicate order detected",
        ModernRejectionReason.RATE_LIMIT_EXCEEDED: "Too many requests, please slow down",
        ModernRejectionReason.TIMEOUT: "Order processing timed out",
        ModernRejectionReason.UNSUPPORTED_ORDER: "This order type is not supported",
        ModernRejectionReason.SYSTEM_ERROR: "Internal system error occurred",
        ModernRejectionReason.OTHER: "Order was rejected by the broker",
    }

    @classmethod
    def translate_order_status(cls, fix_status: str) -> ModernOrderStatus:
        """Translate FIX order status code to modern status"""
        return cls.FIX_STATUS_MAP.get(fix_status, ModernOrderStatus.REJECTED)

    @classmethod
    def translate_rejection_reason(cls, fix_reason: str) -> ModernRejectionReason:
        """Translate FIX rejection reason code to modern reason"""
        return cls.FIX_REJECTION_MAP.get(fix_reason, ModernRejectionReason.OTHER)

    @classmethod
    def translate_order_type(cls, fix_type: str) -> ModernOrderType:
        """Translate FIX order type code to modern type"""
        return cls.FIX_ORDER_TYPE_MAP.get(fix_type, ModernOrderType.MARKET)

    @classmethod
    def translate_order_side(cls, fix_side: str) -> ModernOrderSide:
        """Translate FIX order side code to modern side"""
        return cls.FIX_SIDE_MAP.get(fix_side, ModernOrderSide.BUY)

    @classmethod
    def translate_time_in_force(cls, fix_tif: str) -> ModernTimeInForce:
        """Translate FIX time in force code to modern TIF"""
        return cls.FIX_TIF_MAP.get(fix_tif, ModernTimeInForce.GTC)

    @classmethod
    def parse_fix_timestamp(cls, time_str: Optional[str]) -> Optional[datetime]:
        """Parse FIX timestamp format to Python datetime"""
        if not time_str:
            return None
        try:
            return datetime.strptime(time_str, "%Y%m%d-%H:%M:%S.%f")
        except (ValueError, TypeError):
            try:
                return datetime.strptime(time_str, "%Y%m%d-%H:%M:%S")
            except (ValueError, TypeError):
                return None

    @classmethod
    def generate_status_message(cls, status: ModernOrderStatus, order_data: Dict[str, Any]) -> str:
        """Generate human-readable status message"""
        symbol = order_data.get("symbol", "")
        side = cls.translate_order_side(order_data.get("side", "1"))
        order_type = cls.translate_order_type(order_data.get("order_type", "1"))
        quantity = order_data.get("order_qty", 0)

        if status == ModernOrderStatus.REJECTED:
            reject_reason = cls.translate_rejection_reason(order_data.get("reject_reason"))
            server_text = order_data.get("text", "")
            base_message = cls.REJECTION_DESCRIPTIONS.get(reject_reason, "Order was rejected")
            if server_text:
                return f"{base_message}. Server details: {server_text}"
            return base_message

        elif status == ModernOrderStatus.FILLED:
            avg_price = order_data.get("avg_price")
            if avg_price:
                return (
                    f"{order_type.title()} {side} order for {quantity} {symbol} executed at average price {avg_price}"
                )
            return f"{order_type.title()} {side} order for {quantity} {symbol} executed successfully"

        elif status == ModernOrderStatus.PARTIALLY_FILLED:
            executed = order_data.get("cum_qty", 0)
            remaining = order_data.get("leaves_qty", 0)
            return f"{order_type.title()} {side} order for {symbol} partially filled: {executed} executed, {remaining} remaining"

        elif status == ModernOrderStatus.PENDING:
            return f"{order_type.title()} {side} order for {quantity} {symbol} accepted and pending execution"

        elif status == ModernOrderStatus.CANCELLED:
            return f"{order_type.title()} {side} order for {quantity} {symbol} has been cancelled"

        elif status == ModernOrderStatus.CANCELLING:
            return f"{order_type.title()} {side} order for {quantity} {symbol} cancellation in progress"

        elif status == ModernOrderStatus.EXPIRED:
            return f"{order_type.title()} {side} order for {quantity} {symbol} has expired"

        elif status == ModernOrderStatus.MODIFYING:
            return f"{order_type.title()} {side} order for {quantity} {symbol} modification in progress"

        else:
            return f"{order_type.title()} {side} order for {quantity} {symbol} status: {status}"

    @classmethod
    def convert_fix_order_data(cls, fix_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert complete FIX order data to modern format.
        This is the main method that should be used for all FIX order conversions.
        """
        modern_data = fix_data.copy()

        # Translate all FIX codes to modern equivalents
        if "order_status" in fix_data:
            modern_data["modern_status"] = cls.translate_order_status(fix_data["order_status"])

        if "reject_reason" in fix_data:
            modern_data["modern_rejection"] = cls.translate_rejection_reason(fix_data["reject_reason"])

        if "order_type" in fix_data:
            modern_data["modern_order_type"] = cls.translate_order_type(fix_data["order_type"])

        if "side" in fix_data:
            modern_data["modern_side"] = cls.translate_order_side(fix_data["side"])

        if "time_in_force" in fix_data:
            modern_data["modern_tif"] = cls.translate_time_in_force(fix_data["time_in_force"])

        # Parse timestamps
        for time_field in ["transact_time", "order_created", "order_modified", "expire_time"]:
            if time_field in fix_data:
                modern_data[f"parsed_{time_field}"] = cls.parse_fix_timestamp(fix_data[time_field])

        return modern_data

    @classmethod
    def get_all_possible_statuses(cls) -> Dict[str, str]:
        """Get all possible modern order statuses with descriptions"""
        return {
            ModernOrderStatus.PENDING: "Order accepted, waiting for execution",
            ModernOrderStatus.PARTIALLY_FILLED: "Order partially executed",
            ModernOrderStatus.FILLED: "Order completely executed",
            ModernOrderStatus.CANCELLED: "Order cancelled by user or system",
            ModernOrderStatus.REJECTED: "Order rejected by broker/market",
            ModernOrderStatus.EXPIRED: "Order expired (GTD orders)",
            ModernOrderStatus.CANCELLING: "Cancel request in progress",
            ModernOrderStatus.MODIFYING: "Modification request in progress",
        }

    @classmethod
    def get_all_rejection_reasons(cls) -> Dict[str, str]:
        """Get all possible rejection reasons with descriptions"""
        return {reason.value: description for reason, description in cls.REJECTION_DESCRIPTIONS.items()}

    @classmethod
    def validate_translation_integrity(cls) -> bool:
        """
        Validate that all translation mappings are complete and consistent.
        This should be called during application startup to ensure system integrity.
        """
        try:
            # Check that all enum values are covered in status descriptions
            all_statuses = cls.get_all_possible_statuses()
            for status in ModernOrderStatus:
                assert status.value in all_statuses, f"Status {status.value} not in descriptions"

            # Check that all rejection reasons have descriptions
            for reason in ModernRejectionReason:
                assert reason in cls.REJECTION_DESCRIPTIONS, f"Rejection reason {reason} not in descriptions"

            # Check mapping consistency - ensure all mappings exist and are not empty
            assert len(cls.FIX_STATUS_MAP) > 0, "FIX_STATUS_MAP is empty"
            assert len(cls.FIX_REJECTION_MAP) > 0, "FIX_REJECTION_MAP is empty"
            assert len(cls.FIX_ORDER_TYPE_MAP) > 0, "FIX_ORDER_TYPE_MAP is empty"
            assert len(cls.FIX_SIDE_MAP) > 0, "FIX_SIDE_MAP is empty"
            assert len(cls.FIX_TIF_MAP) > 0, "FIX_TIF_MAP is empty"

            # Validate that all mapped values are valid enum values
            for fix_code, modern_status in cls.FIX_STATUS_MAP.items():
                assert isinstance(
                    modern_status, ModernOrderStatus
                ), f"Invalid status mapping for {fix_code}: {modern_status}"

            for fix_code, modern_reason in cls.FIX_REJECTION_MAP.items():
                assert isinstance(
                    modern_reason, ModernRejectionReason
                ), f"Invalid rejection mapping for {fix_code}: {modern_reason}"

            return True
        except (AssertionError, KeyError) as e:
            import logging

            logging.error(f"FIX Translation System integrity check failed: {e}")
            return False
