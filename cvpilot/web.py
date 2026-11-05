import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from . import ROOT
from .storage import Store

@asynccontextmanager
async def lifespan(app):
    store = Store()
    store.initialize()
    app.state.store = store
    yield

app = FastAPI(title='CV Pilot landing', lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

@app.get('/health')
def health():
    with app.state.store.connect() as conn:
        conn.execute('SELECT 1')
    return {'ok': True, 'database': 'PostgreSQL', 'workspace': 'Streamlit'}

@app.get('/api/state')
def state():
    # Loading-page health check exposes no personal profile contents.
    with app.state.store.connect() as conn:
        conn.execute('SELECT 1')
    return {'ready': True, 'workspace': 'Streamlit'}

@app.get('/app')
def workspace():
    return RedirectResponse('http://127.0.0.1:' + os.getenv('STREAMLIT_PORT', '8501'), status_code=302)

@app.get('/')
def landing():
    return FileResponse(ROOT / 'public' / 'landing.html')

@app.get('/{asset}')
def asset(asset: str):
    if asset not in ('landing.css', 'landing.js', 'transitions.css'):
        raise HTTPException(404)
    return FileResponse(ROOT / 'public' / asset)
