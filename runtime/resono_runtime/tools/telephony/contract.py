from __future__ import annotations

from dataclasses import dataclass


TELEPHONY_PACKAGE_VERSION = 1


@dataclass(frozen=True, slots=True)
class TelephonyContract:
    name: str
    description: str
    effect_class: str
    input_schema: dict[str, object]


def contracts() -> tuple[TelephonyContract, ...]:
    return (
        TelephonyContract(
            "get_phone_status",
            "Read current SIM, carrier, network, signal, and voice state from the R1 modem.",
            "read",
            {"type": "object", "properties": {}, "additionalProperties": False},
        ),
        TelephonyContract(
            "place_call",
            "Prepare a phone call to the given number for user confirmation.",
            "mutate",
            {
                "type": "object",
                "properties": {"number": {"type": "string"}},
                "required": ["number"],
                "additionalProperties": False,
            },
        ),
        TelephonyContract(
            "send_sms",
            "Prepare a text message to the given number for user confirmation.",
            "mutate",
            {
                "type": "object",
                "properties": {"to": {"type": "string"}, "text": {"type": "string"}},
                "required": ["to", "text"],
                "additionalProperties": False,
            },
        ),
        TelephonyContract(
            "confirm_action",
            "Confirm a previously prepared call or text so it executes.",
            "mutate",
            {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
                "additionalProperties": False,
            },
        ),
    )
