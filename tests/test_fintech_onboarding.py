from src.fintech_onboarding import PaymentEvent, should_release_payment


def test_payment_release_requires_verified_domain_and_caps_amount():
    event = PaymentEvent("pay_123", 500_000, "USD")
    assert should_release_payment(event, domain_verified=True)
    assert not should_release_payment(event, domain_verified=False)
    assert not should_release_payment(PaymentEvent("pay_124", 500_001, "USD"), True)
