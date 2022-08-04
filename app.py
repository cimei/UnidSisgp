from project import app
from flask import render_template
import locale
from datetime import datetime

# filtro cusomizado para o jinja
#
@app.template_filter('converte_para_real')
def converte_para_real(valor):
    if valor == None or valor == '':
        return 0
    else:
        return locale.currency(valor, symbol=False, grouping = True )

@app.template_filter('decimal_com_virgula')
def decimal_com_virgula(valor):
    if valor == None or valor == '':
        return 0
    else:
        return locale.format_string('%.1f',valor,grouping=True)

@app.template_filter('str_to_date')
def str_to_date(valor):
    if valor == None or valor == '':
        return 0
    else:
        return datetime.strptime(valor,'%Y-%m-%dT%H:%M:%S')        

@app.route('/')
def index():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(port = 5002, host='0.0.0.0')
