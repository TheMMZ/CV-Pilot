import json
import httpx
import pytest
from openai import OpenAI
from cvpilot.llm import Proposal, validate_proposal, propose, accept_proposal
from cvpilot.matching import evidence_catalog, tailor

def valid(profile):
    return {'summary': {'text': profile['summary'], 'source_ids': ['profile.summary']},
            'rewrites': [{'source_id': 'experience.0.0', 'text': profile['experience'][0]['bullets'][0]}],
            'cover_letter': {'text': profile['summary'], 'source_ids': ['profile.summary']}, 'rationale': 'Prioritize relevant demonstrated experience.'}

def test_llm_http_integration_and_acceptance(profile, job):
    requests = []
    def provider(request):
        data = json.loads(request.content)
        requests.append(data)
        assert request.url.path == '/v1/chat/completions'
        assert data['response_format'] == {'type': 'json_object'}
        return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 1, 'model': 'test-model',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(valid(profile))}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}})
    with OpenAI(base_url='http://provider.test/v1', api_key='test-only', http_client=httpx.Client(transport=httpx.MockTransport(provider))) as client:
        generated = propose(profile, [], job, client=client, model='test-model')
    assert len(requests) == 1
    accepted = accept_proposal(tailor(profile, [], job), generated)
    assert accepted['llm']['reviewed'] is True
    assert accepted['cover_letter'] == profile['summary']
    assert 'email' not in requests[0]['messages'][1]['content']

def test_llm_unknown_sources_and_skills_rejected(profile, job):
    catalog = evidence_catalog(profile, [])
    data = valid(profile)
    data['summary']['source_ids'] = ['nonexistent']
    with pytest.raises(ValueError):
        validate_proposal(Proposal(**data), catalog, job)
    data = valid(profile)
    data['summary']['text'] = 'Experienced in Kubernetes.'
    with pytest.raises(ValueError, match='unsupported skills'):
        validate_proposal(Proposal(**data), catalog, job)

def test_llm_invented_metrics_rejected(profile, job):
    data = valid(profile)
    data['rewrites'][0]['text'] += ' Increased performance by 900%.'
    with pytest.raises(ValueError, match='unsupported number'):
        validate_proposal(Proposal(**data), evidence_catalog(profile, []), job)

def test_llm_missing_config_is_explicit(profile, job, monkeypatch):
    monkeypatch.delenv('LLM_MODEL', raising=False)
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    with pytest.raises(RuntimeError, match='LLM_BASE_URL'):
        propose(profile, [], job)
