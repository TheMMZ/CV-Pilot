import base64
import os
import re
from datetime import datetime, timezone
import httpx

class GitHubError(RuntimeError):
    pass

def import_repositories(username, token=None, client=None):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{0,38}', username):
        raise ValueError('Enter a valid GitHub username.')
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'CV-Pilot', 'X-GitHub-Api-Version': '2026-03-10'}
    token = token or os.getenv('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    owned_client = client is None
    client = client or httpx.Client(base_url='https://api.github.com', headers=headers, timeout=20, follow_redirects=False)
    def get(path, optional=False):
        response = client.get(path, headers=headers)
        if response.status_code == 404 and optional:
            return None
        if response.status_code in (403, 429):
            raise GitHubError('GitHub denied access or the API rate limit was reached. Check token permissions or try later.')
        if response.status_code == 404:
            raise GitHubError('GitHub account not found.')
        if response.status_code >= 400:
            raise GitHubError(f'GitHub returned HTTP {response.status_code}.')
        return response.json()
    try:
        user = get('/users/' + username)
        repos = []
        for page in range(1, 6):
            # Only the explicitly entered account's repositories; a token never imports unrelated accounts.
            endpoint = f'/user/repos?affiliation=owner&per_page=100&sort=updated&page={page}' if token else f'/users/{username}/repos?per_page=100&sort=updated&page={page}'
            batch = get(endpoint)
            repos.extend(r for r in batch if r['owner']['login'].casefold() == username.casefold())
            if len(batch) < 100:
                break
        selected = [r for r in repos if not r.get('fork') and not r.get('archived')][:15]
        imported, warnings = [], []
        for repo in selected:
            readme = ''
            languages = [repo['language']] if repo.get('language') else []
            try:
                content = get(f'/repos/{username}/{repo["name"]}/readme', optional=True)
                if content and content.get('encoding') == 'base64':
                    readme = base64.b64decode(content.get('content', '')).decode('utf-8', errors='replace')[:16000]
            except GitHubError as exc:
                warnings.append(f'{repo["name"]}: {exc}')
            imported.append({'id': repo['id'], 'name': repo['name'], 'url': repo['html_url'],
                             'description': repo.get('description') or '', 'languages': languages, 'readme': readme,
                             'topics': repo.get('topics', []), 'fork': False, 'verified': True,
                             'private': repo.get('private', False), 'updatedAt': repo.get('pushed_at'),
                             'importedAt': datetime.now(timezone.utc).isoformat()})
        return {'username': user['login'], 'repositories': imported, 'warnings': warnings,
                'note': 'Up to 15 recent owned repositories. Metadata and READMEs are evidence to review, not proof of proficiency.'}
    finally:
        if owned_client:
            client.close()
