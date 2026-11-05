import base64
import httpx
from cvpilot.github import import_repositories

def test_github_api_import_and_fork_filtering():
    def github(request):
        path = request.url.path
        if path == '/users/example':
            return httpx.Response(200, json={'login': 'example'})
        if path == '/users/example/repos':
            return httpx.Response(200, json=[{'id': 1, 'owner': {'login': 'example'}, 'name': 'pipeline', 'html_url': 'https://github.com/example/pipeline', 'language': 'Python', 'description': 'ETL', 'fork': False}, {'id': 2, 'owner': {'login': 'example'}, 'name': 'fork', 'fork': True}])
        if path == '/repos/example/pipeline/readme':
            return httpx.Response(200, json={'encoding': 'base64', 'content': base64.b64encode(b'Python PostgreSQL pipeline').decode()})
        raise AssertionError(path)
    with httpx.Client(base_url='https://api.github.com', transport=httpx.MockTransport(github)) as client:
        result = import_repositories('example', client=client)
    assert len(result['repositories']) == 1
    assert 'PostgreSQL' in result['repositories'][0]['readme']
