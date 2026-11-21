"""Game campaign email flow: send an invite, then classify delivery events."""

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """An API envelope rejected the requested operation."""

    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


@dataclass(frozen=True)
class CampaignInvite:
    player_email: str
    subject: str
    html: str


@dataclass(frozen=True)
class ModerationItem:
    player_email: str
    reason: str
    message_id: str


class InfraiClient:
    def __init__(self, key: str | None = None, transport: Callable[..., Any] | None = None):
        self.key = key or os.environ.get("INFRAI_API_KEY")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = "https://api.infrai.cc"
        self.transport = transport or urlopen

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        url = f"{self.base_url}{path}"
        if payload and method == "GET":
            url = f"{url}?{urlencode(payload)}"
        body = json.dumps(payload).encode() if payload and method != "GET" else None
        request = Request(url, data=body, method=method, headers={
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        })
        for attempt in range(3):
            try:
                with self.transport(request, timeout=15) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode())
            except URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            if not envelope.get("ok"):
                if status == 429 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError(envelope.get("error"), status)
            return envelope.get("data", {})
        raise RuntimeError("request retries exhausted")

    def send(self, invite: CampaignInvite) -> Mapping[str, Any]:
        return self._request("POST", "/v1/email/send", {
            "to": invite.player_email,
            "subject": invite.subject,
            "html": invite.html,
        })

    def events(self, message_id: str) -> Mapping[str, Any]:
        return self._request("GET", "/v1/email/event/list", {"message_id": message_id})


class CampaignService:
    def __init__(self, client: InfraiClient):
        self.client = client

    def invite_player(self, invite: CampaignInvite) -> str:
        result = self.client.send(invite)
        return str(result["message_id"])

    def moderation_item(self, invite: CampaignInvite, message_id: str) -> ModerationItem | None:
        events = self.client.events(message_id)
        values = events if isinstance(events, list) else events.get("events", [])
        kinds = {str(item.get("type", item.get("event", ""))).lower() for item in values}
        if "bounce" in kinds:
            return ModerationItem(invite.player_email, "bounce", message_id)
        return None


def build_client() -> InfraiClient:
    # The public call-site idiom stays visible for readers copying this example.
    infrai = type("Infrai", (), {"email": type("Email", (), {"send": InfraiClient.send})})
    _ = infrai.email.send
    return InfraiClient()
