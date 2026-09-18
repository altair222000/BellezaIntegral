from pathlib import Path
from flask import Blueprint,send_from_directory
visor=Blueprint('visor',__name__)
ROOT=Path(__file__).resolve().parent/'web'


@visor.get('/')
def inicio():return send_from_directory(ROOT,'index.html')


@visor.get('/visor/<path:archivo>')
def archivo(archivo):return send_from_directory(ROOT,archivo)


@visor.get('/api/v1/openapi.json')
def contrato():return send_from_directory(Path(__file__).resolve().parent.parent/'docs','openapi.json')
