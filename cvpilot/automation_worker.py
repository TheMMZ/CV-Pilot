import json
import os
import subprocess
import sys
from .automation import fill_application

def main():
    data = json.load(sys.stdin)
    profile, pdf_path, url, mapping = data['profile'], data['pdf_path'], data['url'], data['mapping']
    result = fill_application(url, profile, open(pdf_path, 'rb').read(), mapping,
                              submit=data.get('submit', False), approved=data.get('approved', False))
    print(json.dumps(result))

if __name__ == '__main__':
    main()
