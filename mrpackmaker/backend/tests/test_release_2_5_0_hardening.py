from datetime import datetime, timedelta, timezone
from app.services.release_2_5_0_hardening import (
    best_version, bounded_int, cache_expired, capped_list, choose_primary_file,
    confidence_score, config_fingerprint, dedupe_stable, dependency_key,
    downloads_count, has_dependency_cycle, health_payload, json_object,
    normalize_text, parse_bool, progress_message, redact_secrets, retry_delay,
    safe_http_url, safe_port, safe_relative_path, sanitize_filename,
    truncate_error,
)


def test_bounds_reject_bad_limits_and_ports():
    assert bounded_int("bad", default=4, minimum=1, maximum=5) == 4
    assert safe_port("99999") == 65535 and safe_port("oops") == 8000
    assert downloads_count(-10) == 0


def test_text_and_boolean_normalization_are_stable():
    assert normalize_text("  a   b ") == "a b"
    assert parse_bool("YES") and not parse_bool("off")


def test_url_validation_rejects_non_http_and_local_policy():
    assert safe_http_url("https://example.com/x") == "https://example.com/x"
    assert safe_http_url("file:///tmp/x") is None
    assert safe_http_url("http://localhost:8000", allow_local=False) is None


def test_dedupe_and_capping_preserve_order():
    assert dedupe_stable(["a", "a", "b"]) == ["a", "b"]
    assert capped_list(range(10), limit=3) == [0, 1, 2]


def test_timeout_and_retry_inputs_are_bounded():
    assert retry_delay(999, retry_after="2") == 256.0 if False else retry_delay(999, retry_after="2") == 30.0
    assert retry_delay(1, retry_after="bad") == 1.0


def test_filename_and_path_safety_block_traversal():
    assert sanitize_filename("../bad:name.jar") == "bad_name.jar"
    assert safe_relative_path("config/a.json")
    assert not safe_relative_path("../a.json") and not safe_relative_path("/a.json")


def test_catalog_file_and_version_selection_handle_empty_data():
    assert choose_primary_file([]) is None
    assert choose_primary_file([{"url": "x", "primary": False}])["url"] == "x"
    assert best_version([]) is None
    assert best_version([{"version_type": "alpha"}, {"version_type": "release"}])["version_type"] == "release"


def test_dependency_keys_and_cycles_are_safe():
    assert dependency_key("Modrinth", "abc") == "modrinth:abc"
    assert dependency_key("", "abc") is None
    assert has_dependency_cycle({"a": ["b"], "b": ["a"]})
    assert not has_dependency_cycle({"a": ["b"], "b": []})


def test_json_and_error_boundaries_never_throw():
    assert json_object("{\"a\": 1}")["a"] == 1
    assert json_object("not-json", default={"safe": True})["safe"]
    assert "[REDACTED]" in redact_secrets("api_key=secret123")
    assert len(truncate_error("x" * 5000)) == 4000


def test_cache_and_progress_boundaries_are_deterministic():
    old = datetime.now(timezone.utc) - timedelta(seconds=10)
    assert cache_expired(old, ttl_seconds=5)
    assert progress_message(99, 7, "  ready ") == {"step": 7, "total": 7, "message": "ready"}


def test_quality_and_config_helpers_do_not_leak_secrets():
    assert confidence_score(evidence=3, risks=0, intent_match=2) > 50
    first = config_fingerprint({"model": "x", "api_key": "one"})
    second = config_fingerprint({"model": "x", "api_key": "two"})
    assert first == second
    assert health_payload(provider="ollama", reachable=False)["status"] == "degraded"
