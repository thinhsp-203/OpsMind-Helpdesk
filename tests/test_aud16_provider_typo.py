"""
AUD-16 Regression Tests — Provider typo silently falls back to mock.

These tests MUST fail before the fix and pass after.
They call production code directly (no re-implementation of logic).
"""
from __future__ import annotations

import pytest

from app import config, email_sender


VALID_PROVIDERS = {"smtp", "resend", "brevo", "webhook", "console", "mock"}


# ---------------------------------------------------------------------------
# AUD-16-T1: resolve_email_provider must reject unknown provider names
# ---------------------------------------------------------------------------

def test_aud16_resolve_email_provider_typo_raises_or_returns_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AUD-16: A typo'd EMAIL_PROVIDER must NOT be silently accepted.

    resolve_email_provider() should either raise ValueError or return a value
    that is clearly NOT in the valid provider set, signalling misconfiguration.
    After the fix it must raise ValueError.
    """
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "smpt")  # intentional typo
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    monkeypatch.setattr(config, "SMTP_ENABLED", False)

    with pytest.raises(ValueError, match="smpt"):
        email_sender.resolve_email_provider()


# ---------------------------------------------------------------------------
# AUD-16-T2: dispatch_email must NOT return True for unknown provider
# ---------------------------------------------------------------------------

def test_aud16_dispatch_email_typo_provider_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AUD-16: dispatch_email with a typo'd provider must return False, not True.

    Before fix: returns True (email silently stored in RAM outbox).
    After fix: returns False (clear failure for unknown provider).
    """
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "smpt")  # intentional typo
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    monkeypatch.setattr(config, "SMTP_ENABLED", False)

    email_sender.clear_outbox()
    result = email_sender.dispatch_email(
        "victim@example.invalid",
        "Test Subject",
        "Test Body",
    )

    assert result is False, (
        "dispatch_email must return False for unknown/typo'd EMAIL_PROVIDER, "
        f"but returned {result!r}"
    )
    # Outbox must NOT contain a silently-queued message
    assert len(email_sender.get_outbox()) == 0, (
        "Outbox should be empty when provider is invalid, but received a record"
    )


# ---------------------------------------------------------------------------
# AUD-16-T3: get_email_status must indicate misconfiguration for typo provider
# ---------------------------------------------------------------------------

def test_aud16_get_email_status_typo_provider_not_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AUD-16: get_email_status must NOT report enabled=True for a typo'd provider.

    Before fix: returns {'enabled': True, 'is_mock': False, 'provider': 'smpt'} — misleading.
    After fix: should either raise ValueError or return enabled=False.
    """
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "smpt")  # intentional typo
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    monkeypatch.setattr(config, "SMTP_ENABLED", False)

    # Option A: fix raises ValueError (preferred — fail fast at startup)
    try:
        status = email_sender.get_email_status()
        # Option B: fix returns an error/disabled status (still acceptable)
        assert status.get("enabled") is False, (
            f"get_email_status must not report enabled=True for typo provider, got: {status}"
        )
    except ValueError:
        pass  # preferred outcome: fast-fail with clear error


# ---------------------------------------------------------------------------
# AUD-16-T4: valid providers must still work correctly (non-regression)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider", sorted(VALID_PROVIDERS))
def test_aud16_valid_providers_accepted(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    """Non-regression: resolve_email_provider must accept all valid provider names."""
    monkeypatch.setattr(config, "EMAIL_PROVIDER", provider)
    monkeypatch.setattr(config, "RESEND_API_KEY", "test_key")
    monkeypatch.setattr(config, "BREVO_API_KEY", "test_key")
    monkeypatch.setattr(config, "SMTP_ENABLED", True)

    # Must not raise
    resolved = email_sender.resolve_email_provider()
    assert resolved == provider, f"Expected {provider!r}, got {resolved!r}"


# ---------------------------------------------------------------------------
# AUD-16-T5: empty EMAIL_PROVIDER still auto-detects correctly (non-regression)
# ---------------------------------------------------------------------------

def test_aud16_empty_provider_auto_detects_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-regression: empty EMAIL_PROVIDER with no keys falls back to 'console'."""
    monkeypatch.setattr(config, "EMAIL_PROVIDER", "")
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    monkeypatch.setattr(config, "SMTP_ENABLED", False)

    resolved = email_sender.resolve_email_provider()
    assert resolved == "console"
