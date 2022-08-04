"""
.. topic:: PGs (views)

    Visualização de Programas de Gestão da Unidade e suas subordinadas.

.. topic:: Ações relacionadas aos programas de gestão.

    * Listar programas de gestão da unidade: plano_trabalho
    * Lista atividades de um PG: lista_atividades_pg
    * Lista metas de um pg: lista_metas_pg
    * Lista pactos de um pg: lista_pactos_pg


"""

# views.py dentro da pasta pgs

from flask import render_template, url_for, flash, request, redirect, Blueprint, abort
from flask_login import current_user, login_required
from flask_mail import Message
from threading import Thread
from sqlalchemy import or_, and_, func, literal
from sqlalchemy.sql import label
from sqlalchemy.orm import aliased
from project import db, mail, app
from project.models import Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs_Items, Unidades, Pessoas, Planos_de_Trabalho,\
                           Atividades, VW_Unidades, catdom, Pactos_de_Trabalho, Planos_de_Trabalho_Metas, Objeto_PG

from datetime import datetime, date, timedelta
# from fpdf import FPDF

import pickle
import os.path
import sys

import uuid
import ast

pgs = Blueprint("pgs",__name__,template_folder='templates')

## lista plano de trabalho

@pgs.route('/<lista>/<coord>/plano_trabalho')
def plano_trabalho(lista,coord):
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta o plano de trabalho (programas de gestão) da unidade.                        |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """
    #pega e-mail do usuário logado
    email = current_user.userEmail

    #pega unidade do usuário logado
    unid_id    = db.session.query(Pessoas.unidadeId).filter(Pessoas.pesEmail == email).first()
    unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                           .filter(Unidades.unidadeId == unid_id.unidadeId)\
                           .join(VW_Unidades, VW_Unidades.id_unidade == Unidades.unidadeId)\
                           .first()
    unid = unid_id.unidadeId

    #possibilidade de ver outra unidade
    if coord != '*':
        unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                               .join(VW_Unidades, VW_Unidades.id_unidade == Unidades.unidadeId)\
                               .filter(Unidades.undSigla == coord)\
                               .first()
        unid = unid_dados.unidadeId

    #monta árvore da unidade
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
         
    #

    ativs = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId,
                             label('qtd_ativs',func.count(Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId)))\
                       .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                       .group_by(Planos_de_Trabalho_Ativs.planoTrabalhoId)\
                       .subquery()

    metas = db.session.query(Planos_de_Trabalho_Metas.planoTrabalhoId,
                             label('qtd_metas',func.count(Planos_de_Trabalho_Metas.planoTrabalhoMetaId)))\
                       .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Planos_de_Trabalho_Metas.planoTrabalhoId)\
                       .group_by(Planos_de_Trabalho_Metas.planoTrabalhoId)\
                       .subquery()  

    pactos = db.session.query(Pactos_de_Trabalho.planoTrabalhoId,
                              label('qtd_pactos',func.count(Pactos_de_Trabalho.pactoTrabalhoId)))\
                       .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Pactos_de_Trabalho.planoTrabalhoId)\
                       .group_by(Pactos_de_Trabalho.planoTrabalhoId)\
                       .subquery()

    objetos = db.session.query(Objeto_PG.planoTrabalhoId,
                              label('qtd_objetos',func.count(Objeto_PG.planoTrabalhoObjetoId)))\
                       .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Objeto_PG.planoTrabalhoId)\
                       .group_by(Objeto_PG.planoTrabalhoId)\
                       .subquery()                                                        

    if lista == 'Todas':
        lista = '%'

    planos_trab_unid = db.session.query(Planos_de_Trabalho.planoTrabalhoId,
                                        Planos_de_Trabalho.situacaoId,
                                        Planos_de_Trabalho.dataInicio,
                                        Planos_de_Trabalho.dataFim,
                                        catdom.descricao,
                                        ativs.c.qtd_ativs,
                                        metas.c.qtd_metas,
                                        pactos.c.qtd_pactos,
                                        objetos.c.qtd_objetos,
                                        Unidades.undSigla,
                                        Unidades.unidadeId)\
                                 .join(catdom, catdom.catalogoDominioId == Planos_de_Trabalho.situacaoId)\
                                 .join(ativs, ativs.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .join(Unidades, Unidades.unidadeId == Planos_de_Trabalho.unidadeId)\
                                 .outerjoin(metas, metas.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .outerjoin(pactos,pactos.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .outerjoin(objetos,objetos.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .filter(Planos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]), catdom.descricao.like(lista))\
                                 .order_by(Unidades.unidadeId,catdom.descricao, Planos_de_Trabalho.dataInicio.desc())\
                                 .all() 


    quantidade = len(planos_trab_unid)


    return render_template('plano_trabalho.html', lista=lista, unid_dados = unid_dados, planos_trab_unid=planos_trab_unid, quantidade=quantidade)



## lista atividades de um pg

@pgs.route('/<pg>/lista_atividades_pg')

def lista_atividades_pg(pg):
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta uma lista das atividades de um pg.                                           |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """   

    ativs_lista = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId,
                                   Atividades.titulo,
                                   Atividades.tempoPresencial,
                                   Atividades.tempoRemoto,
                                   Atividades.complexidade,
                                   Atividades.entregasEsperadas)\
                            .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                            .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
                            .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId == pg)\
                            .order_by(Atividades.titulo)\
                            .all() 

    quantidade = len(ativs_lista)

    return render_template('lista_atividades_pg.html', pg=pg, quantidade = quantidade,
                                                ativs_lista = ativs_lista)

## lista metas de um pg

@pgs.route('/<pg>/lista_metas_pg')

def lista_metas_pg(pg):
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta uma lista das metas de um pg.                                                |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """   

    metas_lista = db.session.query(Planos_de_Trabalho_Metas.planoTrabalhoId,
                                   Planos_de_Trabalho_Metas.meta,
                                   Planos_de_Trabalho_Metas.indicador,
                                   Planos_de_Trabalho_Metas.descricao)\
                            .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Planos_de_Trabalho_Metas.planoTrabalhoId)\
                            .filter(Planos_de_Trabalho_Metas.planoTrabalhoId == pg)\
                            .order_by(Planos_de_Trabalho_Metas.meta)\
                            .all() 

    quantidade = len(metas_lista)

    return render_template('lista_metas_pg.html', pg=pg, quantidade = quantidade,
                                                metas_lista = metas_lista)                                                


## lista pactos de um pg

@pgs.route('/<pg>/lista_pactos_pg')

def lista_pactos_pg(pg):
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta uma lista de pactos geraros a partir de um pg.                               |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """   

    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

    pactos_lista = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
                                    Pactos_de_Trabalho.planoTrabalhoId,
                                    Pactos_de_Trabalho.dataInicio,
                                    Pactos_de_Trabalho.dataFim,
                                    Pactos_de_Trabalho.cargaHorariaDiaria,
                                    Pactos_de_Trabalho.percentualExecucao,
                                    Pactos_de_Trabalho.relacaoPrevistoRealizado,
                                    Pactos_de_Trabalho.tempoTotalDisponivel,
                                    Pactos_de_Trabalho.formaExecucaoId,
                                    Pessoas.pesNome,
                                    Unidades.undSigla,
                                    catdom_1.c.descricao,
                                    label('forma',catdom.descricao))\
                         .filter(Pactos_de_Trabalho.planoTrabalhoId == pg)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                         .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                         .all()    

    quantidade = len(pactos_lista)

    return render_template('lista_pactos_pg.html', pg=pg, quantidade = quantidade,
                                                pactos_lista = pactos_lista)                                                

