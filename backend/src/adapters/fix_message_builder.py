import datetime
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class FIXMessageBuilder:
    def __init__(self, sender_comp_id: str, target_comp_id: str, protocol_spec: str):
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.protocol_spec = protocol_spec
        self.SOH = "\x01"
        self.next_seq_num = 1

    def create_fix_message(self, msg_type: str, fields: List[Tuple[str, str]]) -> str:
        msg_fields = [
            ("35", msg_type),
            ("49", self.sender_comp_id),
            ("56", self.target_comp_id),
            ("34", str(self.next_seq_num)),
            ("52", datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]),
        ]

        msg_fields.extend(fields)
        body = self.SOH.join(f"{tag}={value}" for tag, value in msg_fields) + self.SOH
        body_length = len(body.encode("ascii"))
        header = f"8={self.protocol_spec}{self.SOH}9={body_length}{self.SOH}"
        message_without_checksum = header + body
        checksum = sum(message_without_checksum.encode("ascii")) % 256
        checksum_str = str(checksum).zfill(3)

        self.next_seq_num += 1
        return message_without_checksum + f"10={checksum_str}{self.SOH}"

    def parse_fix_response(self, response: str) -> Dict[str, str]:
        fields = {}
        for field in response.split(self.SOH):
            if "=" in field:
                tag, value = field.split("=", 1)
                fields[tag] = value
        return fields
