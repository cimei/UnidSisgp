# __init__.py dentro da pasta project

import sys
import os
import locale
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail

import pyodbc

pyodbc.setDecimalSeparator('.')

TOP_LEVEL_DIR = os.path.abspath(os.curdir)

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

app.register_blueprint(core)
app.register_blueprint(usuarios)
app.register_blueprint(error_pages)

app.register_blueprint(demandas,url_prefix='/demandas')
app.register_blueprint(objetos,url_prefix='/objetos')
app.register_blueprint(pgs,url_prefix='/pgs')
