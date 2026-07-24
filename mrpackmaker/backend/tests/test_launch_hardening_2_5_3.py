from app.services.launch_hardening import bounded_upload_size, fallback_available, health_status, progress_key, redact_log_line, retry_budget

def test_logs_redact_keys_tokens_and_env_values():
    value=redact_log_line('api_key=sk-secret token=abc MRPACK_AI_API_KEY=xyz')
    assert 'sk-secret' not in value and 'abc' not in value and 'xyz' not in value and '[REDACTED]' in value

def test_upload_limit_and_retry_budget_are_bounded():
    assert bounded_upload_size(10**12)==512*1024*1024
    assert bounded_upload_size(-1)==0 and retry_budget(999)==5

def test_offline_health_keeps_fallback_available():
    assert health_status(False)=='degraded' and fallback_available(False)

def test_progress_dedupe_key_is_stable():
    event={'run_id':'r1','step':4,'message':'Processing prompt'}
    assert progress_key(event)==('r1',4,'Processing prompt')
