from project import app
from flask import render_template
from datetime import datetime
import os

import webbrowser
from threading import Timer

# filtros cusomizado para o jinja
#
@app.template_filter('verifica_serv_bd')
def verifica_serv_bd(chave):
    return os.getenv(chave)

@app.template_filter('str_to_date')
def str_to_date(valor):
    if valor == None or valor == '':
        return 0
    else:
        return datetime.strptime(valor,'%Y-%m-%dT%H:%M:%S')        

@app.route('/')
def index():
    return render_template('home.html')

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5002/')

if __name__ == '__main__':
    Timer(1, open_browser).start();
    app.run(port = 5002)