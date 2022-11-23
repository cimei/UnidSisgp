# __init__.py dentro da pasta project

import locale
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail

import pyodbc

import sys
import os
import time
from shutil import rmtree
import glob

def deleteOldPyinstallerFolders(time_threshold = 3600): # Por deefault remove depois de 1 hora, time_threshold em segundos
    try:
        base_path = sys._MEIPASS
    except Exception:
        return  # Não está rodando como OneFile Folder -> Return

    temp_path = os.path.abspath(os.path.join(base_path, '..')) # Vai para o parent folder de MEIPASS

    # Deleta os MEIPASS folders antigos...
    mei_folders = glob.glob(os.path.join(temp_path, '_MEI*'))
    for item in mei_folders:
        if (time.time()-os.path.getctime(item)) > time_threshold:
            rmtree(item)

pyodbc.setDecimalSeparator('.')

#TOP_LEVEL_DIR = os.path.abspath(os.curdir)

frozen = ' não '

if getattr(sys, 'frozen', False):
    frozen = ' sim '
    deleteOldPyinstallerFolders()

print( 'rodando no modo frozen:',frozen)    

app = Flask (__name__, static_url_path=None, instance_relative_config=True)

app.config.from_pyfile('flask.cfg')

app.static_url_path=app.config.get('STATIC_PATH')

db = SQLAlchemy(app)
Migrate(app,db)

mail = Mail(app)

locale.setlocale( locale.LC_ALL, '' )

#################################
## log in - cofigurações

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'users.login'

############################################
## blueprints - registros

from project.core.views import core
from project.error_pages.handlers import error_pages
from project.usuarios.views import usuarios

from project.demandas.views import demandas
from project.objetos.views import objetos
from project.pgs.views import pgs
from project.pessoas.views import pessoas


app.register_blueprint(core)
app.register_blueprint(usuarios)
app.register_blueprint(error_pages)

app.register_blueprint(demandas,url_prefix='/demandas')
app.register_blueprint(objetos,url_prefix='/objetos')
app.register_blueprint(pgs,url_prefix='/pgs')
app.register_blueprint(pessoas,url_prefix='/pessoas')

