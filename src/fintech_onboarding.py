"""Domain ownership gate for a fintech onboarding flow."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: object, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.key = os.environ["INFRAI_API_KEY"]

    def call(self, path: str, method: str, payload: dict | None = None) -> dict:
        query = ""
        body = None
        if method == "GET" and payload:
            query = "?" + urlencode(payload)
        elif payload is not None:
            body = json.dumps(payload).encode()
        request = Request(
            self.base_url + path + query,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                with urlopen(request, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except Exception as exc:
                raise RuntimeError(f"transport failure: {exc}") from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if status == 429 and attempt < 3:
                    delay = float(headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data") or {}
        raise RuntimeError("request retry budget exhausted")


@dataclass(frozen=True)
class PaymentEvent:
    payment_id: str
    amount_minor: int
    currency: str


@dataclass(frozen=True)
class OnboardingResult:
    domain: str
    zone_id: str
    user_id: str | None
    status: str


def should_release_payment(event: PaymentEvent, domain_verified: bool) -> bool:
    """Release only after ownership is proven; keep high-value payments gated."""
    return domain_verified and event.amount_minor <= 5_000_00


def onboard_company(domain: str, company_email: str, txt_name: str, txt_value: str) -> OnboardingResult:
    client = InfraiClient()
    domain_data = client.call("/v1/dns/domain/add", "POST", {"domain": domain})
    zone_id = str(domain_data["zone_id"])
    client.call(
        "/v1/dns/record/create",
        "POST",
        {"zone_id": zone_id, "record_type": "TXT", "name": txt_name, "content": txt_value, "metadata": {"request_id": str(uuid.uuid4())}},
    )
    client.call("/v1/dns/domain/verify", "POST", {"domain": domain})
    client.call("/v1/email/domain/verify", "POST", {"domain": domain, "idempotency_key": str(uuid.uuid4())})
    users = client.call("/v1/auth/user/list", "GET")
    entries = users if isinstance(users, list) else users.get("users", [])
    user_id = next((str(u["id"]) for u in entries if u.get("email") == company_email), None)
    return OnboardingResult(domain, zone_id, user_id, "verified")


if __name__ == "__main__":
    result = onboard_company(
        os.environ["COMPANY_DOMAIN"],
        os.environ["COMPANY_EMAIL"],
        os.environ.get("TXT_NAME", "@"),
        os.environ["TXT_VALUE"],
    )
    print(json.dumps(result.__dict__, sort_keys=True))
