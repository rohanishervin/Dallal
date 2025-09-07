from typing import Any, Dict, Optional

from ..schemas.trading_schemas import ExecType, OrderStatus


class FIXResponseParser:
    ORDER_STATUS_DESCRIPTIONS = {
        "0": "New",
        "1": "Partially Filled",
        "2": "Filled",
        "3": "Done",
        "4": "Cancelled",
        "6": "Pending Cancel",
        "8": "Rejected",
        "B": "Calculated",
        "C": "Expired",
        "E": "Pending Replacement",
        "F": "Pending Close",
    }

    EXEC_TYPE_DESCRIPTIONS = {
        "0": "New",
        "4": "Cancelled",
        "5": "Replaced",
        "6": "Pending Cancel",
        "8": "Rejected",
        "B": "Calculated",
        "C": "Expired",
        "E": "Pending Replacement",
        "F": "Trade (Filled/Partially Filled)",
        "I": "Order Status",
        "J": "Pending Close",
    }

    REJECT_REASON_DESCRIPTIONS = {
        "0": "Dealer reject (Market closed or trading restrictions)",
        "1": "Unknown symbol",
        "3": "Order exceeds limits",
        "4": "Off quotes (Price too old)",
        "5": "Unknown order",
        "6": "Duplicate order",
        "11": "Unsupported order characteristics",
        "13": "Incorrect quantity",
        "16": "Throttling (Rate limit exceeded)",
        "17": "Timeout",
        "18": "Close only (Position closing only)",
        "99": "Other (See text field for details)",
    }

    ORDER_TYPE_DESCRIPTIONS = {
        "1": "Market Order",
        "2": "Limit Order",
        "3": "Stop Order",
        "4": "Stop-Limit Order",
        "N": "Position Order",
    }

    SIDE_DESCRIPTIONS = {"1": "Buy", "2": "Sell"}

    TIME_IN_FORCE_DESCRIPTIONS = {
        "1": "Good Till Cancel (GTC)",
        "3": "Immediate or Cancel (IOC)",
        "6": "Good Till Date (GTD)",
    }

    @classmethod
    def parse_execution_report(cls, exec_data: Dict[str, Any]) -> Dict[str, Any]:
        parsed = exec_data.copy()

        order_status = exec_data.get("order_status")
        exec_type = exec_data.get("exec_type")
        reject_reason = exec_data.get("reject_reason")
        order_type = exec_data.get("order_type")
        side = exec_data.get("side")
        time_in_force = exec_data.get("time_in_force")

        parsed["order_status_description"] = cls.ORDER_STATUS_DESCRIPTIONS.get(
            order_status, f"Unknown ({order_status})"
        )
        parsed["exec_type_description"] = cls.EXEC_TYPE_DESCRIPTIONS.get(exec_type, f"Unknown ({exec_type})")
        parsed["order_type_description"] = cls.ORDER_TYPE_DESCRIPTIONS.get(order_type, f"Unknown ({order_type})")
        parsed["side_description"] = cls.SIDE_DESCRIPTIONS.get(side, f"Unknown ({side})")

        if reject_reason:
            parsed["reject_reason_description"] = cls.REJECT_REASON_DESCRIPTIONS.get(
                reject_reason, f"Unknown ({reject_reason})"
            )

        if time_in_force:
            parsed["time_in_force_description"] = cls.TIME_IN_FORCE_DESCRIPTIONS.get(
                time_in_force, f"Unknown ({time_in_force})"
            )

        return parsed

    @classmethod
    def generate_human_readable_summary(cls, exec_data: Dict[str, Any]) -> str:
        order_status = exec_data.get("order_status")
        exec_type = exec_data.get("exec_type")
        reject_reason = exec_data.get("reject_reason")
        text = exec_data.get("text", "")
        symbol = exec_data.get("symbol", "")
        side = exec_data.get("side")
        order_type = exec_data.get("order_type")
        quantity = exec_data.get("order_qty", 0)

        side_desc = cls.SIDE_DESCRIPTIONS.get(side, "")
        order_type_desc = cls.ORDER_TYPE_DESCRIPTIONS.get(order_type, "")
        status_desc = cls.ORDER_STATUS_DESCRIPTIONS.get(order_status, "")
        exec_desc = cls.EXEC_TYPE_DESCRIPTIONS.get(exec_type, "")

        if order_status == "8" or exec_type == "8":
            reject_desc = cls.REJECT_REASON_DESCRIPTIONS.get(reject_reason, "Unknown reason")
            if text:
                return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} was rejected: {reject_desc}. Server message: {text}"
            else:
                return (
                    f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} was rejected: {reject_desc}"
                )

        elif order_status == "2" or exec_type == "F":
            avg_price = exec_data.get("avg_price")
            if avg_price:
                return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} was filled at average price {avg_price}"
            else:
                return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} was filled"

        elif order_status == "1":
            cum_qty = exec_data.get("cum_qty", 0)
            leaves_qty = exec_data.get("leaves_qty", 0)
            return f"{order_type_desc} {side_desc.lower()} order for {symbol} is partially filled: {cum_qty} executed, {leaves_qty} remaining"

        elif order_status == "0":
            return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} has been accepted and is pending execution"

        elif order_status == "4":
            return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} has been cancelled"

        elif order_status == "6":
            return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} is pending cancellation"

        elif order_status == "C":
            return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} has expired"

        else:
            return f"{order_type_desc} {side_desc.lower()} order for {quantity} {symbol} status: {status_desc} ({exec_desc})"

    @classmethod
    def enhance_response_message(cls, success: bool, exec_data: Dict[str, Any], original_message: str) -> str:
        if not success or not exec_data:
            return original_message

        order_status = exec_data.get("order_status")
        exec_type = exec_data.get("exec_type")

        if order_status == "8" or exec_type == "8":
            human_summary = cls.generate_human_readable_summary(exec_data)
            return f"Order rejected: {human_summary}"
        elif order_status == "2" or exec_type == "F":
            return f"Order executed successfully: {cls.generate_human_readable_summary(exec_data)}"
        elif order_status == "1":
            return f"Order partially filled: {cls.generate_human_readable_summary(exec_data)}"
        elif order_status == "0":
            return f"Order accepted: {cls.generate_human_readable_summary(exec_data)}"
        else:
            return original_message
