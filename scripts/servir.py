"""Servidor WSGI. Respeta PORT/HOST del entorno y permite overrides por CLI."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app
from waitress import serve

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--lan', action='store_true')
    p.add_argument('--host')
    p.add_argument('--puerto', type=int)
    a = p.parse_args()
    host = a.host or ('0.0.0.0' if a.lan else os.getenv('HOST', '127.0.0.1'))
    port = a.puerto or int(os.getenv('PORT', '5000'))
    print(f'Belleza Integral: http://{host}:{port}', flush=True)
    serve(create_app(), host=host, port=port, threads=int(os.getenv('WEB_THREADS','20')), max_request_body_size=1024*1024)
