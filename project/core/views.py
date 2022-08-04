"""
.. topic:: Core (views)

    Este é o módulo inicial do sistema.

    Apresenta as telas de início, informação e procedimentos de carda de dados em lote.

.. topic:: Ações relacionadas aos bolsistas

    * Tela inicial: index
    * Tela de informações: info

"""

# core/views.py

from flask import render_template, Blueprint


core = Blueprint("core",__name__)

@core.route('/')
def index():
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta a tela inicial do aplicativo.                                                |
    +---------------------------------------------------------------------------------------+
    """

    return render_template ('index.html',sistema='Unidade SISGP')

@core.route('/info')
def info():
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta a tela de informações do aplicativo.                                         |
    +---------------------------------------------------------------------------------------+
    """

    return render_template('info.html')




