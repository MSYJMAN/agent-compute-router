from __future__ import annotations

import re

# Provider / backend execution states recorded on Compute Receipt stages.
# These are deliberately narrow: an unavailable provider, a missing credential,
# and a denied entitlement are different facts and must not collapse into one
# another, because each implies a different operator action.
REMOTE_NOT_AUTHORIZED = "REMOTE_NOT_AUTHORIZED"
BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
CREDENTIALS_MISSING = "CREDENTIALS_MISSING"
AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
PROVIDER_ACCESS_REQUIRED = "PROVIDER_ACCESS_REQUIRED"
PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
NETWORK_FAILURE = "NETWORK_FAILURE"
NO_FEASIBLE_SAMPLE = "NO_FEASIBLE_SAMPLE"
INVALID_SAMPLE = "INVALID_SAMPLE"
EXECUTION_ERROR = "EXECUTION_ERROR"
OPTIMAL = "OPTIMAL"
FEASIBLE = "FEASIBLE"

PROVIDER_STATES = frozenset(
    {
        REMOTE_NOT_AUTHORIZED,
        BACKEND_UNAVAILABLE,
        CREDENTIALS_MISSING,
        AUTHENTICATION_FAILED,
        PROVIDER_ACCESS_REQUIRED,
        PROVIDER_UNAVAILABLE,
        NETWORK_FAILURE,
        NO_FEASIBLE_SAMPLE,
        INVALID_SAMPLE,
        EXECUTION_ERROR,
        OPTIMAL,
        FEASIBLE,
    }
)

# States that mean "no usable allocation was produced".
UNSUCCESSFUL_STATES = frozenset(PROVIDER_STATES - {OPTIMAL, FEASIBLE})

_REDACTED = "[redacted]"

# Provider messages are operator-facing diagnostics, not trusted content. They
# can embed API tokens, signed URLs, and local filesystem paths. Receipts are
# meant to be shareable evidence, so these are stripped before they are stored.
_SANITIZERS: tuple[tuple[re.Pattern[str], str], ...] = (
    # D-Wave style tokens: short alpha prefix, dash, long hex body.
    (re.compile(r"\b[A-Za-z]{2,10}-[0-9a-fA-F]{16,}\b"), _REDACTED),
    # Bare long hex/base64-ish secrets.
    (re.compile(r"\b[0-9a-fA-F]{24,}\b"), _REDACTED),
    (re.compile(r"\b[A-Za-z0-9_\-]{40,}\b"), _REDACTED),
    # token=... / api_key: ... style key-value leaks.
    (
        re.compile(r"(?i)\b(token|api[_-]?key|secret|password|authorization)\b\s*[:=]\s*\S+"),
        r"\1=" + _REDACTED,
    ),
    # Absolute filesystem paths (Windows and POSIX).
    (re.compile(r"[A-Za-z]:[\\/][^\s'\"]*"), _REDACTED),
    (re.compile(r"(?<![\w.])/(?:home|Users|root|tmp|var|etc)/[^\s'\"]*"), _REDACTED),
    # Userinfo embedded in URLs.
    (re.compile(r"://[^/\s:@]+:[^/\s@]+@"), "://" + _REDACTED + "@"),
)


def sanitize_provider_message(message: str, *, limit: int = 300) -> str:
    """Strip credential- and path-shaped substrings from a provider message."""
    cleaned = " ".join(str(message).split())
    for pattern, replacement in _SANITIZERS:
        cleaned = pattern.sub(replacement, cleaned)
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1].rstrip() + "…"
    return cleaned


def _dwave_exception_states() -> tuple[tuple[type[BaseException], str], ...]:
    """Map installed D-Wave exception classes to provider states.

    Ordered most specific first. Built lazily so the Ocean SDK stays optional,
    and so a partially installed SDK degrades to EXECUTION_ERROR instead of
    raising during error handling.
    """
    mapping: list[tuple[type[BaseException], str]] = []

    def add(module: str, name: str, state: str) -> None:
        try:
            imported = __import__(module, fromlist=[name])
            candidate = getattr(imported, name, None)
        except Exception:
            return
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            mapping.append((candidate, state))

    # Entitlement: the account cannot use the requested solver at all.
    add("dwave.cloud.exceptions", "SolverNotFoundError", PROVIDER_ACCESS_REQUIRED)
    add("dwave.cloud.exceptions", "SolverPropertyMissingError", PROVIDER_ACCESS_REQUIRED)
    add("dwave.cloud.exceptions", "UnsupportedSolverError", PROVIDER_ACCESS_REQUIRED)
    # Authentication: credentials were presented and rejected.
    add("dwave.cloud.exceptions", "SolverAuthenticationError", AUTHENTICATION_FAILED)
    # Credentials absent or unreadable before any request is made.
    add("dwave.cloud.exceptions", "ConfigFileError", CREDENTIALS_MISSING)
    # Transport-level problems.
    add("dwave.cloud.exceptions", "RequestTimeout", NETWORK_FAILURE)
    add("dwave.cloud.exceptions", "PollingTimeout", NETWORK_FAILURE)
    add("dwave.cloud.exceptions", "Timeout", NETWORK_FAILURE)
    add("requests.exceptions", "ConnectionError", NETWORK_FAILURE)
    add("requests.exceptions", "Timeout", NETWORK_FAILURE)
    # Provider reachable but the solver itself failed or is offline.
    add("dwave.cloud.exceptions", "SolverOfflineError", PROVIDER_UNAVAILABLE)
    add("dwave.cloud.exceptions", "SolverFailureError", PROVIDER_UNAVAILABLE)
    add("dwave.cloud.exceptions", "InvalidAPIResponseError", PROVIDER_UNAVAILABLE)
    add("dwave.cloud.exceptions", "ProblemUploadError", PROVIDER_UNAVAILABLE)
    add("dwave.cloud.exceptions", "SAPIError", PROVIDER_UNAVAILABLE)
    add("dwave.cloud.exceptions", "SolverError", PROVIDER_UNAVAILABLE)
    add("dwave.cloud.exceptions", "RequestError", PROVIDER_UNAVAILABLE)
    return tuple(mapping)


_CREDENTIAL_TEXT = re.compile(
    r"(?i)\b(api token not defined|token not defined|no api token|missing token"
    r"|solver definition|no credentials)\b"
)


def classify_provider_error(exc: BaseException) -> str:
    """Classify a provider-side exception into a narrow provider state."""
    for candidate, state in _dwave_exception_states():
        if isinstance(exc, candidate):
            return state

    # dwave-cloud-client signals an absent API token with a plain ValueError.
    if isinstance(exc, ValueError) and _CREDENTIAL_TEXT.search(str(exc)):
        return CREDENTIALS_MISSING

    return EXECUTION_ERROR
