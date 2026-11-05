import copy
import re
from datetime import datetime, timezone

SKILLS = {
    'Python': ['python'], 'SQL': ['sql', 't-sql'], 'JavaScript': ['javascript', 'js'],
    'TypeScript': ['typescript'], 'Java': ['java'], 'C++': ['c++'],
    'PostgreSQL': ['postgresql', 'postgres'], 'MySQL': ['mysql'], 'SQL Server': ['sql server'],
    'JSONB': ['jsonb'], 'React': ['react', 'reactjs'], 'Node.js': ['node.js', 'nodejs'],
    'Express': ['express', 'express.js'], 'REST APIs': ['rest api', 'rest apis', 'restful'],
    'Docker': ['docker'], 'Git': ['git'], 'GitHub': ['github'], 'Node-RED': ['node-red'],
    'Capacitor': ['capacitor'], 'IndexedDB': ['indexeddb'], 'Snowflake': ['snowflake'],
    'Airflow': ['airflow'], 'dbt': ['dbt'], 'Kafka': ['kafka'], 'Spark': ['spark', 'pyspark'],
    'pandas': ['pandas'], 'NumPy': ['numpy'], 'scikit-learn': ['scikit-learn', 'sklearn'],
    'PyTorch': ['pytorch'], 'TensorFlow': ['tensorflow'], 'OpenCV': ['opencv'], 'YOLO': ['yolo'],
    'OCR': ['ocr'], 'AWS': ['aws', 'amazon web services'], 'Azure': ['azure'], 'GCP': ['gcp', 'google cloud'],
    'Kubernetes': ['kubernetes', 'k8s'], 'Streamlit': ['streamlit'], 'Tableau': ['tableau'],
    'Power BI': ['power bi'], 'Machine learning': ['machine learning'],
    'Data engineering': ['data engineering'], 'Data science': ['data science'],
    'HTML': ['html', 'html5'], 'CSS': ['css', 'css3'], 'Laravel': ['laravel'], 'PHP': ['php'],
    'Playwright': ['playwright'], 'LLM': ['llm', 'large language model'],
}

def extract_skills(text):
    return [skill for skill, aliases in SKILLS.items() if any(
        re.search(r'(?<![a-z0-9])' + re.escape(alias) + r'(?![a-z0-9])', text, re.I) for alias in aliases)]

def analyze(profile, repositories, job):
    required = extract_skills(job['title'] + ' ' + job['description'])
    sources = [{'skill': s, 'source': 'Master CV', 'kind': 'profile', 'note': 'Self-reported skill'} for s in profile['skills']]
    for exp in profile['experience']:
        for bullet in exp.get('bullets', []):
            sources.extend({'skill': s, 'source': exp['organization'], 'kind': 'experience', 'note': bullet} for s in extract_skills(bullet))
    projects = []
    for repo in repositories:
        if not repo.get('verified') or repo.get('fork'):
            continue
        repo_skills = extract_skills(' '.join([repo.get('description', ''), repo.get('readme', ''), *repo.get('languages', [])]))
        sources.extend({'skill': s, 'source': repo['name'], 'kind': 'repository', 'url': repo['url'],
                        'note': 'Mentioned in repository evidence; review implementation and authorship.'} for s in repo_skills)
        projects.append({**repo, 'matched': [s for s in repo_skills if s in required]})
    matched = [{'skill': s, 'evidence': [e for e in sources if e['skill'].casefold() == s.casefold()]} for s in required]
    matched = [m for m in matched if m['evidence']]
    missing = [s for s in required if not any(m['skill'] == s for m in matched)]
    return {'required': required, 'matched': matched, 'missing': missing,
            'score': round(len(matched) / len(required) * 100) if required else None,
            'projects': sorted((p for p in projects if p['matched']), key=lambda p: (-len(p['matched']), p['name']))[:3],
            'method': 'Recognized keyword coverage, not an ATS score or a hiring prediction.'}

def tailor(profile, repositories, job):
    profile = copy.deepcopy(profile)
    analysis = analyze(profile, repositories, job)
    relevant = {m['skill'] for m in analysis['matched']}
    profile['skills'].sort(key=lambda s: s not in relevant)
    for exp in profile['experience']:
        exp['bullets'] = sorted(exp.get('bullets', []), key=lambda b: -len(set(extract_skills(b)) & set(analysis['required'])))
    return {'profile': profile, 'job': job, 'analysis': analysis, 'generatedAt': datetime.now(timezone.utc).isoformat(),
            'strategy': 'Original facts, prioritized for this role. Planned projects keep their status.'}

def evidence_catalog(profile, repositories):
    facts = {'profile.skills': {'text': ', '.join(profile['skills']), 'source': 'Master CV'}, 'profile.summary': {'text': profile['summary'], 'source': 'Master CV'}}
    for i, exp in enumerate(profile['experience']):
        for j, bullet in enumerate(exp.get('bullets', [])):
            facts[f'experience.{i}.{j}'] = {'text': bullet, 'source': exp['organization']}
    for i, project in enumerate(profile.get('projects', [])):
        facts[f'project.{i}'] = {'text': project['description'], 'source': project['name'], 'status': project['status']}
    for repo in repositories:
        if repo.get('verified') and not repo.get('fork'):
            facts[f'repo.{repo["id"]}'] = {'text': (repo.get('description', '') + '\n' + repo.get('readme', ''))[:5000],
                                         'source': repo['url'], 'status': 'Repository evidence; verify authorship'}
    return facts
