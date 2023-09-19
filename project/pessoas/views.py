"""
.. topic:: Pessoas (views)

    As Pessoas são os servidores lotados na intituição.


.. topic:: Ações relacionadas às pessoas

    * lista_pessoas: Lista pessoas
    * lista_pessoas_unid: Pessoas de uma unidade

"""

# views.py na pasta pessoas

from flask import render_template,url_for,flash, redirect,Blueprint
from flask_login import current_user, login_required

from project import db
from project.models import Unidades, Pessoas, Situ_Pessoa, Tipo_Func_Pessoa, Tipo_Vinculo_Pessoa,\
                            VW_Unidades


pessoas = Blueprint('pessoas',__name__, template_folder='templates')

## lista pessoas de uma unidade

@pessoas.route('<coord>/lista_pessoas_unid')
@login_required
def lista_pessoas_unid(coord):
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta uma lista das pessoas de uma unidade.                                        |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first()

    #pega unidadeId do usuário logado e unsSigla na tabela Unidades
    unid_id = db.session.query(Pessoas.unidadeId).filter(Pessoas.pesEmail == email).first()
    unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                           .filter(Unidades.unidadeId == unid_id.unidadeId)\
                           .join(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
                           .first()
    unid = unid_id.unidadeId

    #possibilidade de ver outra unidade
    if coord != '*':
        unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                               .join(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
                               .filter(Unidades.undSigla == coord)\
                               .first()
        unid = unid_dados.unidadeId


    #monta subestrutura da unidade
    tree = {}
    pai = [unid]
    tree[unid_dados.undSigla] = [unid]

    while pai != []:

        prox_pai = []

        for p in pai:

            filhos = Unidades.query.filter(Unidades.unidadeIdPai==p).all()

            for u in filhos:

                prox_pai.append(u.unidadeId)

                tree[unid_dados.undSigla].append(u.unidadeId)    

        pai =  prox_pai

    pessoas = db.session.query(Pessoas.pessoaId,
                             Pessoas.pesNome,
                             Pessoas.pesCPF,
                             Pessoas.pesDataNascimento,
                             Pessoas.pesMatriculaSiape,
                             Pessoas.pesEmail,
                             Pessoas.unidadeId,
                             Unidades.undSigla,
                             Pessoas.tipoFuncaoId,
                             Tipo_Func_Pessoa.tfnDescricao,
                             Pessoas.cargaHoraria,
                             Pessoas.situacaoPessoaId,
                             Situ_Pessoa.spsDescricao,
                             Pessoas.tipoVinculoId,
                             Tipo_Vinculo_Pessoa.tvnDescricao)\
                            .outerjoin(Unidades,Unidades.unidadeId == Pessoas.unidadeId)\
                            .outerjoin(Situ_Pessoa, Situ_Pessoa.situacaoPessoaId == Pessoas.situacaoPessoaId)\
                            .outerjoin(Tipo_Func_Pessoa,Tipo_Func_Pessoa.tipoFuncaoId == Pessoas.tipoFuncaoId)\
                            .outerjoin(Tipo_Vinculo_Pessoa,Tipo_Vinculo_Pessoa.tipoVinculoId == Pessoas.tipoVinculoId)\
                            .filter(Unidades.unidadeId.in_(tree[unid_dados.undSigla]))\
                            .order_by(Pessoas.unidadeId,Pessoas.pesNome).all()

    quantidade = len(pessoas)

    return render_template('lista_pessoas.html', pessoas = pessoas, quantidade=quantidade,
                                                 unid=unid_dados.undSigla)

#