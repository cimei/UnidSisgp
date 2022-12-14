"""
.. topic:: Core (views)

    Este é o módulo inicial do sistema.

    Apresenta as telas de início, informação e procedimentos de carda de dados em lote.

.. topic:: Ações relacionadas aos bolsistas

    * Tela inicial: index
    * Tela de informações: info

"""

# core/views.py

from flask import render_template,url_for,flash, redirect, request, Blueprint, send_from_directory

import os
from datetime import datetime as dt
import tempfile
from flask_login import current_user
from werkzeug.utils import secure_filename

from project.core.forms import ArquivoForm

from project.usuarios.views import registra_log_unid

core = Blueprint("core",__name__)

## função para pegar arquivo

def PegaArquivo(form):

    '''
        DOCSTRING: solicita arquivo do usuário e salva em diretório temporário para ser utilizado
        INPUT: formulário de entrada
        OUTPUT: arquivo de trabalho
    '''

    tempdirectory = tempfile.gettempdir()

    f = form.arquivo.data
    fname = secure_filename(f.filename)
    arquivo = os.path.join(tempdirectory, fname)
    f.save(arquivo)

    print ('***  ARQUIVO ***',arquivo)

    pasta = os.path.normpath(tempdirectory)

    if not os.path.exists(pasta):
        os.makedirs(os.path.normpath(pasta))

    arq = fname
    arq = os.path.normpath(pasta+'/'+arq)

    return arq

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

@core.route('/carregaTA', methods=['GET', 'POST'])
def CarregaTA():
    """
    +---------------------------------------------------------------------------------------+
    |Executa o procedimento de carga do arquivo com um termo de aceite.                     |
    +---------------------------------------------------------------------------------------+

    """

    form = ArquivoForm()

    if form.validate_on_submit():

        if current_user.userAtivo and current_user.avaliadorId == 99999:

            arq = PegaArquivo(form)

            print ('*****************************************************************')
            print ('<<',dt.now().strftime("%x %X"),'>> ','Carregando Termo de Aceite...')
            print ('*****************************************************************')

            os.popen('cp '+ arq +' /app/project/static/termo.txt')

            registra_log_unid(current_user.id,'Upload de arquivo com Termo de Aceite.')

            flash('Arquivo com Termo de Aceite salvo!','sucesso')

            return redirect(url_for('core.index'))

        else:

            flash('O seu usuário precisa ser ativado para esta operação!','erro')

            return redirect(url_for('core.index'))

    return render_template('grab_file.html',form=form)





