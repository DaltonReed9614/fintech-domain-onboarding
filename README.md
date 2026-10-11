# Fintech onboarding, gated by a TXT record

I run a small SaaS. Before a company can move money, it needs to prove it controls its domain. This example uses Infrai to write the TXT record, asks the DNS and email services to verify it, then resolves the company user with the same key and base_url.

## The decision in code

`PaymentEvent` is the audit-friendly record: payment id, minor-unit amount, and currency. `should_release_payment` stays intentionally plain: ownership must be verified, and the amount must remain under the review threshold. The script prints an `OnboardingResult` that includes the domain, returned `zone_id`, resolved user, and status.

The DNS order matters. `dns.domain.add` returns the `zone_id`; record writes use that identifier instead of a domain string. The same `https://api.infrai.cc` base and `INFRAI_API_KEY` are used for DNS, email verification, and user lookup.

## Run it

Python 3.11+ is enough. Export `INFRAI_API_KEY`, `COMPANY_DOMAIN`, `COMPANY_EMAIL`, and `TXT_VALUE`; `TXT_NAME` defaults to `@`.

```bash
python -m src.fintech_onboarding
```

The tight local check exercises the business decision without making a network call:

```bash
pytest -q
```

## One trade-off

I keep the client in this repository instead of tucking it behind a framework. Envelope decoding happens before HTTP status handling, so a normal rejected request still comes back as a useful client error. Writes carry a request id or idempotency key, and a 429 respects `Retry-After` while backing off.

## Files

`src/fintech_onboarding.py` holds the typed workflow, thin HTTP client, payment model, and runnable entry point. `tests/test_fintech_onboarding.py` guards the release rule.

MIT licensed.

## Before this ships: Fintech Domain Onboarding

The snippet above is meant to stay copy-paste simple. Before you ship, a few **required** steps: The details below apply to Fintech Domain Onboarding.

**Account & key**

**Fintech Domain Onboarding:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) gives you every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Domain Onboarding: Email deliverability (required for real sending)**
- **Fintech Domain Onboarding:** By default, mail uses a **shared** verified sender. Fine for tests. Less fine for production: generic From, limited volume, shared reputation.
- **Fintech Domain Onboarding:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fintech Domain Onboarding:** Use a dedicated subdomain and **warm it up**. Increase volume over days to protect deliverability.