import json

from app.domain.common import Loader
from app.domain.requirements.models import RequirementProfile
from app.domain.requirements.understanding import ConfidenceLevel, RequirementAnalysis, RequirementExplanation
from app.services.requirements import category_quotas, parse_requirements


def test_structured_analysis_serializes_missing_information():
    profile = RequirementProfile('horror pack', '1.20.1', Loader.FABRIC)
    analysis = RequirementAnalysis(profile, ConfidenceLevel.MISSING_INFORMATION, theme='horror', qol_level='high', missing_information=('minecraft version',), explanation=RequirementExplanation())
    payload = json.loads(json.dumps(analysis.to_dict()))
    assert payload['confidence'] == 'missing_information'
    assert payload['missing_information'] == ['minecraft version']
    assert payload['explanation']['follow_up_questions'] == ['minecraft version']


def test_category_quotas_respect_requested_minimum():
    requirements = parse_requirements('horror with lots of QoL', minimum_mods=100)
    quotas = category_quotas(requirements)
    assert sum(quotas.values()) >= 100
    assert {'horror', 'qol'} <= quotas.keys()
