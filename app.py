from project import app
from datetime import datetime
import os

from threading import Timer

# filtros cusomizado para o jinja
#
@app.template_filter('retorna_var_amb')
def retorna_var_amb(chave):
    return os.getenv(chave)

@app.template_filter('str_to_date')
def str_to_date(valor):
    if valor == None or valor == '':
        return 0
    else:
        return datetime.strptime(valor,'%Y-%m-%dT%H:%M:%S')        

if __name__ == '__main__':
    app.run(port = 5002)