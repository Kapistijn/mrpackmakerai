from pathlib import Path

from app.config import AIConfig
from app.schemas.editor import AIChangePlan

ROOT = Path(__file__).resolve().parents[2]


def test_ai_change_plan_is_typed_and_user_facing():
    plan = AIChangePlan(summary='Improve survival', benefits=['deeper progression'])
    assert plan.requires_approval is True
    assert plan.summary == 'Improve survival'


def test_provider_settings_validate_top_p_and_retry_bounds():
    assert AIConfig(top_p=0.4, retry_attempts=4).top_p == 0.4
    assert AIConfig(top_p=0.4, retry_attempts=4).retry_attempts == 4


def test_ai_editor_hides_raw_json_by_default():
    text = (ROOT / 'frontend' / 'src' / 'pages' / 'AIEditor.tsx').read_text(encoding='utf-8')
    assert 'Developer Details' in text
    assert 'JSON.stringify(result,null,2)' in text
    assert '<pre className="text-sm whitespace-pre-wrap mt-2">{JSON.stringify(plan' not in text


def test_settings_expose_real_ai_controls():
    text = (ROOT / 'frontend' / 'src' / 'pages' / 'Settings.tsx').read_text(encoding='utf-8')
    for field in ('top_p', 'retry_attempts', 'Save AI settings', 'Test connection'):
        assert field in text


def test_editor_marks_deterministic_fallbacks_honestly():
    text = (ROOT / 'frontend' / 'src' / 'pages' / 'AIEditor.tsx').read_text(encoding='utf-8')
    assert 'Deterministic fallback plan' in text
    assert 'AI unavailable' in text
