from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol


class TelephonyEventType(str, Enum):
    CALL_STARTED = "call_started"
    MEDIA_STARTED = "media_started"
    MEDIA_RECEIVED = "media_received"
    CALL_ENDED = "call_ended"
    CALL_FAILED = "call_failed"


@dataclass
class TelephonyCall:
    provider_call_id: str
    from_number: str
    to_number: str
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TelephonyEvent:
    type: TelephonyEventType
    provider_call_id: str | None
    metadata: dict = field(default_factory=dict)


class TelephonyProvider(Protocol):
    async def create_call(
        self,
        from_number: str,
        to_number: str,
        webhook_url: str | None = None,
    ) -> str:
        """Place an outbound call, returning the provider call id."""
        ...

    async def end_call(self, provider_call_id: str) -> None:
        """Hang up an active call."""
        ...

    async def transfer_call(
        self,
        provider_call_id: str,
        to_number: str,
    ) -> None:
        """Transfer an active call to a human number."""
        ...

    async def get_call(self, provider_call_id: str) -> TelephonyCall:
        """Retrieve the current state of a call from the provider."""
        ...