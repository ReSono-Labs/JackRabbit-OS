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
    )
