"""Create local configuration without printing generated passwords."""
from pathlib import Path
import secrets
root = Path(__file__).resolve().parents[1]
env = root / '.env'
if env.exists():
    print('.env already exists; existing settings preserved.')
else:
    password = secrets.token_urlsafe(24)
    example = (root / 'env.example').read_text(encoding='utf-8-sig')
    env.write_text(example.replace('replace-with-a-local-password', password), encoding='utf-8')
    print('Created local .env. Configure your LLM provider and model when ready.')
