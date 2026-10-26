"""Provider state classification and receipt secret hygiene."""

from __future__ import annotations

import importlib.util
import unittest

from compute_router.provider import (
    AUTHENTICATION_FAILED,
    CREDENTIALS_MISSING,
    EXECUTION_ERROR,
    NETWORK_FAILURE,
    PROVIDER_ACCESS_REQUIRED,
    PROVIDER_UNAVAILABLE,
    classify_provider_error,
    sanitize_provider_message,
)

HAS_DWAVE_CLOUD = importlib.util.find_spec("dwave.cloud") is not None


class SanitizationTests(unittest.TestCase):
    def test_dwave_style_token_is_redacted(self):
        token = "DEV-0123456789abcdef0123456789abcdef01234567"
        cleaned = sanitize_provider_message(f"auth failed for {token}")
        self.assertNotIn(token, cleaned)
        self.assertIn("[redacted]", cleaned)

    def test_key_value_secret_is_redacted(self):
        cleaned = sanitize_provider_message("request failed: token=hunter2secretvalue")
        self.assertNotIn("hunter2secretvalue", cleaned)

    def test_windows_path_is_redacted(self):
        cleaned = sanitize_provider_message(
            r"Failed to read 'C:\Users\someone\.config\dwave\dwave.conf'"
        )
        self.assertNotIn("someone", cleaned)
        self.assertIn("[redacted]", cleaned)

    def test_posix_home_path_is_redacted(self):
        cleaned = sanitize_provider_message("cannot open /home/someone/.dwave/conf")
        self.assertNotIn("someone", cleaned)

    def test_url_userinfo_is_redacted(self):
        cleaned = sanitize_provider_message("connecting to https://user:pass@sapi.example")
        self.assertNotIn("pass@", cleaned)

    def test_long_message_is_truncated(self):
        cleaned = sanitize_provider_message("x " * 500, limit=80)
        self.assertLessEqual(len(cleaned), 80)

    def test_newlines_are_collapsed(self):
        self.assertEqual(sanitize_provider_message("a\n\n  b\tc"), "a b c")

    def test_harmless_message_survives(self):
        self.assertEqual(
            sanitize_provider_message("solver is offline"), "solver is offline"
        )


class ClassificationTests(unittest.TestCase):
    def test_unknown_error_is_execution_error_not_success(self):
        self.assertEqual(classify_provider_error(RuntimeError("???")), EXECUTION_ERROR)

    def test_missing_token_value_error_is_credentials_missing(self):
        self.assertEqual(
            classify_provider_error(ValueError("API token not defined")),
            CREDENTIALS_MISSING,
        )

    def test_unrelated_value_error_is_not_credentials_missing(self):
        self.assertEqual(
            classify_provider_error(ValueError("duration must be positive")),
            EXECUTION_ERROR,
        )


@unittest.skipUnless(HAS_DWAVE_CLOUD, "D-Wave Ocean extra not installed")
class DwaveExceptionMappingTests(unittest.TestCase):
    """Pin the mapping against the real installed exception hierarchy."""

    def test_entitlement_and_auth_failures_are_distinguished(self):
        from dwave.cloud.exceptions import (
            SolverAuthenticationError,
            SolverNotFoundError,
        )

        self.assertEqual(
            classify_provider_error(SolverNotFoundError("no such solver")),
            PROVIDER_ACCESS_REQUIRED,
        )
        self.assertEqual(
            classify_provider_error(SolverAuthenticationError("bad token")),
            AUTHENTICATION_FAILED,
        )

    def test_config_error_is_credentials_missing(self):
        from dwave.cloud.exceptions import ConfigFileReadError

        self.assertEqual(
            classify_provider_error(ConfigFileReadError("missing")), CREDENTIALS_MISSING
        )

    def test_timeout_is_network_failure(self):
        from dwave.cloud.exceptions import RequestTimeout

        self.assertEqual(classify_provider_error(RequestTimeout("slow")), NETWORK_FAILURE)

    def test_offline_solver_is_provider_unavailable(self):
        from dwave.cloud.exceptions import SolverOfflineError

        self.assertEqual(
            classify_provider_error(SolverOfflineError("down")), PROVIDER_UNAVAILABLE
        )

    def test_entitlement_is_not_reported_as_authentication(self):
        """A Trial account without solver access is not a credential problem."""
        from dwave.cloud.exceptions import SolverNotFoundError

        state = classify_provider_error(SolverNotFoundError("not entitled"))
        self.assertNotEqual(state, AUTHENTICATION_FAILED)
        self.assertNotEqual(state, CREDENTIALS_MISSING)


if __name__ == "__main__":
    unittest.main()
