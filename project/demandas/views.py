"""
.. topic:: Demandas (views)

    Compõe o trabalho diário da coordenação. Consistem da atividades da coordenação, cadastratas no PGD.

.. topic:: Ações relacionadas às demandas

    * Ver uma demanda (pacto de trabalho): demanda
    * Listar demandas da unidade (pactos de trabalho): list_demandas
    * Procurar demandas: pesquisa_demanda
    * Lista resultado da procura: list_pesquisa


"""

# views.py dentro da pasta demandas

from flask import render_template, url_for, flash, request, redirect, Blueprint, abort
from flask_login import current_user, login_required
from flask_mail import Message
from threading import Thread
from sqlalchemy import or_, and_, func, literal
from sqlalchemy.sql import label
from sqlalchemy.orm import aliased
from project import db, mail, app
from project.models import Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs_Items, Unidades, Pessoas, Planos_de_Trabalho, \
                           Atividades, VW_Unidades, cat_item_cat, catdom, Pactos_de_Trabalho, Planos_de_Trabalho_Reuniao,\
                           Pactos_de_Trabalho_Solic, Pactos_de_Trabalho_Atividades, Planos_de_Trabalho_Metas,\
                           Pactos_de_Trabalho_Hist, Objetos, Objeto_Atividade_Pacto, Objeto_PG, Feriados, UFs

from project.demandas.forms import SolicitacaoForm601, SolicitacaoForm602, SolicitacaoForm603, SolicitacaoAnaliseForm,\
                                   PreSolicitacaoForm, InciaConcluiAtivForm, AvaliaAtivForm                               

from project.usuarios.views import registra_log_unid                                   

from datetime import datetime, date, timedelta
# from fpdf import FPDF

import pickle
import os.path
import sys

import uuid
import ast
import numpy as np
import ast

demandas = Blueprint("demandas",__name__,template_folder='templates')


#lendo uma demanda

@demandas.route('/demanda/<pacto_id>',methods=['GET','POST'])
def demanda(pacto_id):
    """+---------------------------------------------------------------------------------+
       |Resgata, para leitura, uma demanda (pacto de trabalho) e registros associados.   |
       |                                                                                 |
       |Recebe o ID do pacto como parâmetro.                                             |
       +---------------------------------------------------------------------------------+
    """

    #pega e-mail do usuário logado
    email = current_user.userEmail

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first()

    # subquery das situações de pacto de trabalho
    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

    # subquery das situações de atividades de pactos de trabalho
    catdom_2 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoAtividadePactoTrabalho')\
                         .subquery()                     

    # pega o pacto selecionado
    demanda = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
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
                               label('forma',catdom.descricao),
                               Planos_de_Trabalho.planoTrabalhoId,
                               UFs.ufId)\
                         .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                         .join(UFs, UFs.ufId == Unidades.ufId)\
                         .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                         .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Pactos_de_Trabalho.planoTrabalhoId)\
                         .first()

    #pega hierarquia superior da unidade da demanda
    unid = db.session.query(Unidades.unidadeId, Unidades.undSigla, VW_Unidades.undSiglaCompleta)\
                           .filter(Unidades.undSigla == demanda.undSigla)\
                           .join(VW_Unidades, VW_Unidades.id_unidade == Unidades.unidadeId)\
                           .first()
    tree_sup = unid.undSiglaCompleta.split('/')
    tree_sup_ids = [u.unidadeId for u in Unidades.query.filter(Unidades.undSigla.in_(tree_sup))]
    
    # calcula a quantidade de dias úteis entre as datas de início e fim do pacto
    feriados = db.session.query(Feriados.ferData).filter(or_(Feriados.ufId==demanda.ufId,Feriados.ufId==None)).all()
    feriados = [f.ferData for f in feriados]

    qtd_dias_uteis = 1 + np.busday_count(demanda.dataInicio,demanda.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados)
    qtd_dias_uteis_sf = 1 + np.busday_count(demanda.dataInicio,demanda.dataFim,weekmask=[1,1,1,1,1,0,0])


    # pega as atividades do PG no a partir do qual o pacto selecionado foi criado
    items_cat = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId,
                                 Atividades.titulo,
                                 Atividades.tempoPresencial,
                                 Atividades.tempoRemoto,
                                 Atividades.permiteRemoto)\
                          .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId == demanda.planoTrabalhoId)\
                          .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                          .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
                          .order_by(Atividades.titulo)\
                          .all()

    # conta quantas atividades foram vincualdas ao pacto
    qtd_items_cat = len(items_cat)

    # conta o número de objetos do PG ao qual o pacto está vinculado
    obj_pg_count = db.session.query(Objeto_PG)\
                        .filter(Objeto_PG.planoTrabalhoId == demanda.planoTrabalhoId)\
                        .count()

    
    # histórico, reuniões, solicitações e atividades são agrupadas para uma visualização conjunta, para tal, 
    # todos tem que ter a mesma quandidade de campos

    historico = db.session.query(label('id',Pactos_de_Trabalho_Hist.pactoTrabalhoHistoricoId),
                                label("situa",catdom.descricao),
                                literal('Histórico').label("tipo"),
                                label('data',Pactos_de_Trabalho_Hist.dataOperacao),
                                literal(None).label('dataFim'),
                                label('tit',Pactos_de_Trabalho_Hist.observacoes),
                                literal(None).label('obs'),
                                literal(None).label('desc'),
                                literal(None).label("tempoRealizado"),
                                literal(None).label("nota"),
                                Pessoas.pesNome,
                                literal(None).label("titulo"),
                                literal(None).label("quantidade"),
                                literal(None).label("tempoPrevistoPorItem"),
                                literal(None).label("tempoPrevistoTotal"),
                                literal(None).label("tempoHomologado"),
                                literal(None).label("justificativa"),
                                literal(None).label("descricao"),
                                literal(None).label("obj"),
                                literal(None).label("chave"),
                                literal(None).label("analist"))\
                          .filter(Pactos_de_Trabalho_Hist.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                          .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Hist.situacaoId)\
                          .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho_Hist.responsavelOperacao)\
                          .order_by(Pactos_de_Trabalho_Hist.dataOperacao.desc())\
                          .all()

    qtd_hist = len(historico)                      

    reunioes = db.session.query(label('id',Planos_de_Trabalho_Reuniao.planoTrabalhoReuniaoId),
                                literal(None).label("situa"),
                                literal('Reunião').label("tipo"),
                                Planos_de_Trabalho_Reuniao.data,
                                literal(None).label("dataFim"),
                                label('tit',Planos_de_Trabalho_Reuniao.titulo),
                                literal(None).label('obs'),
                                label('desc',Planos_de_Trabalho_Reuniao.descricao),
                                literal(None).label("tempoRealizado"),
                                literal(None).label("nota"),
                                literal(None).label("pesNome"),
                                literal(None).label("titulo"),
                                literal(None).label("quantidade"),
                                literal(None).label("tempoPrevistoPorItem"),
                                literal(None).label("tempoPrevistoTotal"),
                                literal(None).label("tempoHomologado"),
                                literal(None).label("justificativa"),
                                literal(None).label("descricao"),
                                label('obj',Objetos.descricao),
                                Objetos.chave,
                                literal(None).label("analist"))\
                          .filter(Planos_de_Trabalho_Reuniao.planoTrabalhoId == demanda.planoTrabalhoId)\
                          .outerjoin(Objeto_PG, Objeto_PG.planoTrabalhoObjetoId == Planos_de_Trabalho_Reuniao.planoTrabalhoObjetoId)\
                          .outerjoin(Objetos, Objetos.objetoId == Objeto_PG.objetoId)\
                          .order_by(Planos_de_Trabalho_Reuniao.data.desc())\
                          .all()

    qtd_reun = len(reunioes)                      

    ativs    = db.session.query(label('id',Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId),
                                 label('situa',catdom_2.c.descricao),
                                 literal('Atividade').label("tipo"),
                                 label('data',Pactos_de_Trabalho_Atividades.dataInicio),
                                 Pactos_de_Trabalho_Atividades.dataFim,
                                 label('tit',Pactos_de_Trabalho_Atividades.descricao),
                                 literal(None).label('obs'),
                                 label('desc',Pactos_de_Trabalho_Atividades.consideracoesConclusao),
                                 Pactos_de_Trabalho_Atividades.tempoRealizado,
                                 Pactos_de_Trabalho_Atividades.nota,
                                 literal(None).label("pesNome"),
                                 Atividades.titulo,
                                 Pactos_de_Trabalho_Atividades.quantidade,
                                 Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                                 Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                 Pactos_de_Trabalho_Atividades.tempoHomologado,
                                 Pactos_de_Trabalho_Atividades.justificativa,
                                 catdom.descricao,
                                 label('obj',Objetos.descricao),
                                 Objetos.chave,
                                 literal(None).label("analist"))\
                         .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                         .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.modalidadeExecucaoId)\
                         .join(catdom_2, catdom_2.c.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                         .outerjoin(Objeto_Atividade_Pacto, Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                         .outerjoin(Objeto_PG, Objeto_PG.planoTrabalhoObjetoId == Objeto_Atividade_Pacto.planoTrabalhoObjetoId)\
                         .outerjoin(Objetos, Objetos.objetoId == Objeto_PG.objetoId)\
                         .order_by(Pactos_de_Trabalho_Atividades.dataInicio.desc(),Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                         .all()

    qtd_ativs_pacto = len(ativs)   

    # gera lista das atividades do pacto acrescentando número de sequência para facilitar sua identificação
    seq_ativs = list(enumerate([(a.id,a.titulo) for a in ativs],1))

    # calcula a soma dos tempos previstos das atividades no pacto por situação e totaliza tudo no final
    ativs_p_tempo_total = [float(t.tempoPrevistoTotal) for t in ativs if t.situa == 'Programada']
    sum_ativs_p_tempo_total = sum(ativs_p_tempo_total)
    ativs_e_tempo_total = [float(t.tempoPrevistoTotal) for t in ativs if t.situa == 'Em execução']
    sum_ativs_e_tempo_total = sum(ativs_e_tempo_total)
    ativs_c_tempo_total = [float(t.tempoPrevistoTotal) for t in ativs if t.situa == 'Concluída']
    sum_ativs_c_tempo_total = sum(ativs_c_tempo_total)
    sum_ativs_tempo_total = sum_ativs_p_tempo_total + sum_ativs_e_tempo_total + sum_ativs_c_tempo_total

    # identificando o analista
    analistas = db.session.query(Pessoas.pessoaId, Pessoas.pesNome).subquery()
    
    solicit  = db.session.query(label('id',Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId),
                                 literal(None).label("situa"),
                                 (literal('Solicitação tipo "') + catdom.descricao + literal('" ')).label("tipo"),
                                 label('data',Pactos_de_Trabalho_Solic.dataSolicitacao),
                                 label('dataFim',Pactos_de_Trabalho_Solic.dataAnalise),
                                 label('tit',Pactos_de_Trabalho_Solic.dadosSolicitacao),
                                 label('obs',Pactos_de_Trabalho_Solic.observacoesSolicitante),
                                 label('desc',Pactos_de_Trabalho_Solic.observacoesAnalista),
                                 literal(None).label("tempoRealizado"),
                                 label('nota',Pactos_de_Trabalho_Solic.aprovado),
                                 Pessoas.pesNome,
                                 literal(None).label("titulo"),
                                 literal(None).label("quantidade"),
                                 literal(None).label("tempoPrevistoPorItem"),
                                 literal(None).label("tempoPrevistoTotal"),
                                 literal(None).label("tempoHomologado"),
                                 literal(None).label("justificativa"),
                                 literal(None).label("descricao"),
                                 literal(None).label("obj"),
                                 literal(None).label("chave"),
                                 label('analist',analistas.c.pesNome))\
                         .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho_Solic.solicitante)\
                         .outerjoin(analistas, analistas.c.pessoaId == Pactos_de_Trabalho_Solic.analista)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Solic.tipoSolicitacaoId)\
                         .order_by(Pactos_de_Trabalho_Solic.dataSolicitacao.desc())\
                         .all()

    qtd_solic = len(solicit) 

    # monta dicionários com o campo dadosSolicitacao das solicitações do pacto que está sendo visto
    dados_solic = [[s.id,ast.literal_eval(str(s.tit).replace('null','None').replace('true','True').replace('false','False'))] for s in solicit]
               
    # agrupa reuniões, solicitações, atividades e historicos para a visão conjunta
    pro_des = reunioes + solicit + ativs + historico

    # o agrupamento é então classificado por data na ordem decrescente, visando contar a história do mais recente para o mais antigo
    pro_des.sort(key=lambda ordem: (ordem.data is not None,ordem.data),reverse=True)

    
    # permite a inserção de nova solicitação com verificação prévia do tipo
    form1 = PreSolicitacaoForm()

    if form1.validate_on_submit():

        # caso a solicitação seja de nova atividade, verifica se há tempo disponível no pacto
        if form1.tipo.data == '601':
            if sum_ativs_tempo_total < demanda.tempoTotalDisponivel:
                return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))
            else:
                flash('Não há como solicitar nova atividade, pois o tempo total disponível no pacto já está todo comprometido','erro')

        # caso a solicitação seja de alterar prazo...
        if form1.tipo.data == '602':
            return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))

        # caso a solicitação seja de prazo de atividade ultrapassaso...
        if form1.tipo.data == '603':
            return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))    

        # caso a solicitação seja de excluir atividade do pacto, só é aberta a tela de solicitação se
        # houver atividades no pacto, caso contrario, repete a tela do pacto, mostrando uma msg flash
        if form1.tipo.data == '604':
            if qtd_ativs_pacto == 0:
                flash('Não há atividades no pacto para excluir!','erro')
            else:
                return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))


    return render_template('ver_demanda.html',
                            id           = pacto_id,
                            post         = demanda,
                            items_cat    = items_cat,
                            pro_des      = pro_des,
                            dados_solic  = dados_solic,
                            form1        = form1,
                            usuario      = usuario,
                            obj_pg_count = obj_pg_count,
                            qtd_items_cat = qtd_items_cat,
                            qtd_dias_uteis = qtd_dias_uteis,
                            qtd_dias_uteis_sf = qtd_dias_uteis_sf,
                            sum_ativs_p_tempo_total = sum_ativs_p_tempo_total,
                            sum_ativs_e_tempo_total = sum_ativs_e_tempo_total,
                            sum_ativs_c_tempo_total = sum_ativs_c_tempo_total,
                            sum_ativs_tempo_total   = sum_ativs_tempo_total,
                            seq_ativs = seq_ativs,
                            qtd_hist = qtd_hist,
                            qtd_reun = qtd_reun,
                            qtd_solic = qtd_solic,
                            qtd_ativs_pacto = qtd_ativs_pacto,
                            tree_sup_ids = tree_sup_ids)

# vendo todas as demandas da unidade

@demandas.route('/<lista>/<coord>/demandas')
def list_demandas(lista,coord):

    """
        +----------------------------------------------------------------------+
        |Lista todas as demandas (pactos de trabalho), bem como registros      |
        |associados.                                                           |
        |                                                                      |
        |Recebe o id da unidade como parâmetro.                                |
        +----------------------------------------------------------------------+
    """

    #pega e-mail do usuário logado
    email = current_user.userEmail

    #pega unidadeId do usuário logado e unsSigla na tabela Unidades
    unid_id = db.session.query(Pessoas.unidadeId).filter(Pessoas.pesEmail == email).first()
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

    if lista == 'Todas':
        lista = '%'

    page = request.args.get('page', 1, type=int)

    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

    demandas = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
                               Pactos_de_Trabalho.planoTrabalhoId,
                               Pactos_de_Trabalho.dataInicio,
                               Pactos_de_Trabalho.dataFim,
                               Pactos_de_Trabalho.cargaHorariaDiaria,
                               Pactos_de_Trabalho.percentualExecucao,
                               Pactos_de_Trabalho.relacaoPrevistoRealizado,
                               Pactos_de_Trabalho.tempoTotalDisponivel,
                               Pessoas.pesNome,
                               Unidades.unidadeId,
                               Unidades.undSigla,
                               catdom_1.c.descricao,
                               label('forma',catdom.descricao))\
                         .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]), catdom_1.c.descricao.like(lista))\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                         .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                         .order_by(Unidades.unidadeId,catdom_1.c.descricao,Pactos_de_Trabalho.dataInicio.desc())\
                         .paginate(page=page,per_page=8)

    demandas_count = db.session.query(Pactos_de_Trabalho)\
                               .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                               .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]), catdom_1.c.descricao.like(lista))\
                               .count()

    demandas_count_pai = db.session.query(Pactos_de_Trabalho)\
                                   .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                   .filter(Pactos_de_Trabalho.unidadeId == unid, catdom_1.c.descricao.like(lista))\
                                   .count()                           

    # pega as atividades de cada demanda
    dem = db.session.query(Pactos_de_Trabalho.planoTrabalhoId)\
                    .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]))\
                    .all()
    
    pts = [item.planoTrabalhoId for item in dem]

    items_cat = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId, Atividades.titulo)\
                          .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId.in_(pts))\
                          .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                          .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
                          .order_by(Atividades.titulo)\
                          .all()
    #

    return render_template ('demandas.html', lista=lista, 
                                             coord=coord, 
                                             items_cat=items_cat, 
                                             demandas=demandas, 
                                             demandas_count=demandas_count,
                                             demandas_count_pai=demandas_count_pai,
                                             unid_dados = unid_dados)


#inserindo uma solicitação

@demandas.route('/solicitacao/<pacto_id>/<tipo>',methods=['GET','POST'])
@login_required
def solicitacao(pacto_id,tipo):
    """+---------------------------------------------------------------------------------+
       |Insere uma solicitação para um pacto existente.                                  |
       |                                                                                 |
       |Recebe o ID do pacto e ID da atividade como parâmetros.                          |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.userEmail

    #pega id sisgp e unidade do usuário logado
    solicitante_id = db.session.query(Pessoas.pessoaId, Pessoas.unidadeId).filter(Pessoas.pesEmail == email).first()

    #pega descrição do tipo de solicitação
    tipo_solic = db.session.query(catdom.catalogoDominioId, catdom.descricao)\
                      .filter(catdom.catalogoDominioId == tipo)\
                      .first()

    #pega dados do pacto
    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

    pacto = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
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
                             label('forma',catdom.descricao),
                             Unidades.ufId)\
                      .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                      .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                      .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                      .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                      .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                      .first()
    
    # pega as atividades do pacto selecionado
    items_cat = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId, 
                                 Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                 Atividades.titulo,
                                 Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                 Pactos_de_Trabalho_Atividades.dataInicio,
                                 Pactos_de_Trabalho_Atividades.situacaoId)\
                          .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                          .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                          .order_by(Pactos_de_Trabalho_Atividades.dataInicio.desc(),Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                          .all()

    # gera lista das atividades do pacto acrescentando número de sequência para facilitar sua identificação
    seq_ativs = list(enumerate([[a.pactoTrabalhoAtividadeId,a.titulo,a.situacaoId] for a in items_cat],1))

    # calcula a soma dos tempos previstos das atividades no pacto por situação e totaliza tudo no final
    ativs_tempo_total = [float(t.tempoPrevistoTotal) for t in items_cat]
    sum_ativs_tempo_total = sum(ativs_tempo_total)
                  

    items_cat_pg = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId,
                                    Atividades.itemCatalogoId,
                                    Atividades.titulo)\
                             .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId == pacto.planoTrabalhoId)\
                             .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                             .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
                             .order_by(Atividades.titulo)\
                             .all()                      

    # define qual formulario a ser utilizado, dependendo do tipo de solicitação
    if tipo_solic.descricao == 'Nova atividade':
        # o choices do campo atividade são definidos aqui e não no form
        lista_ativs = [(i.itemCatalogoId,i.titulo) for i in items_cat_pg]
        lista_ativs.insert(0,('',''))

        form = SolicitacaoForm601()

        form.atividade.choices = lista_ativs

    elif tipo_solic.descricao == 'Alteração prazo':
        form = SolicitacaoForm602()
        
    else:
        # o choices do campo atividade são definidos aqui e não no form
        lista_ativs = [(i[1][0],'('+str(i[0])+') '+i[1][1]) for i in seq_ativs]
        lista_ativs.insert(0,('',''))

        form = SolicitacaoForm603()

        form.atividade.choices = lista_ativs
       
    if form.validate_on_submit():

        if tipo_solic.descricao == 'Nova atividade':

            ativ = db.session.query(Atividades.titulo,
                                    Atividades.complexidade,
                                    Atividades.tempoPresencial,
                                    Atividades.tempoRemoto,
                                    Atividades.permiteRemoto)\
                             .filter(Atividades.itemCatalogoId == form.atividade.data)\
                             .first()

            ## verifica forma de execução e crítica sobre tempo na demanda nova
            if pacto.formaExecucaoId == 101:
                tempo_ativ = ativ.tempoPresencial
            else:
                tempo_ativ = ativ.tempoRemoto
            
            folga_tempo_pacto = float(pacto.tempoTotalDisponivel) - (sum_ativs_tempo_total + form.quantidade.data * float(tempo_ativ))

            if folga_tempo_pacto < 0:
                flash('Solicitação de nova atividade estoura tempo disponível no pacto!','erro')

                return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

            ## crítica sobre tipo de atividade frente à modadlidade do pacto  
            if pacto.formaExecucaoId == 101 and form.remoto.data:
                flash('O pacto não permite atividades remotas!','erro')

                return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

            # monta dadosSoliciacao conforme tipo da nova atividade escolhido
            if form.situacao.data == '501': # Programada

                dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                            "itemCatalogoId":form.atividade.data.lower(),\
                            "itemCatalogo":ativ.titulo + " - " + ativ.complexidade,\
                            "execucaoRemota":form.remoto.data,\
                            "situacaoId":"501",\
                            "situacao":"Programada",\
                            "tempoPrevistoPorItem":float(str(tempo_ativ).replace(',','.')),\
                            "tempoPrevistoPorItemStr":None,\
                            "dataInicio":None,\
                            "dataFim":None,\
                            "tempoRealizado":None,\
                            "descricao":form.desc.data}

            elif form.situacao.data == '502': # Em execução

                dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                            "itemCatalogoId":form.atividade.data.lower(),\
                            "itemCatalogo":ativ.titulo + " - " + ativ.complexidade,\
                            "execucaoRemota":form.remoto.data,\
                            "situacaoId":"502",\
                            "situacao":"Em execução",\
                            "tempoPrevistoPorItem":float(str(tempo_ativ).replace(',','.')),\
                            "tempoPrevistoPorItemStr":None,\
                            "dataInicio":(form.data_ini.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                            "dataFim":None,\
                            "tempoRealizado":None,\
                            "descricao":form.desc.data}

            elif form.situacao.data == '503': # Concluída

                dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                            "itemCatalogoId":form.atividade.data.lower(),\
                            "itemCatalogo":ativ.titulo + " - " + ativ.complexidade,\
                            "execucaoRemota":form.remoto.data,\
                            "situacaoId":"503",\
                            "situacao":"Concluída",\
                            "tempoPrevistoPorItem":float(str(tempo_ativ).replace(',','.')),\
                            "tempoPrevistoPorItemStr":None,\
                            "dataInicio":(form.data_ini.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                            "dataFim":(form.data_fim.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                            "tempoRealizado":float(str(form.tempo_real.data).replace(',','.')),\
                            "descricao":form.desc.data}

      
        elif tipo_solic.descricao == 'Alteração prazo':

            ## crítica tempo total disponível frente ao prazo solicitado  
            # calcula a quantidade de dias úteis entre as datas de início e fim do pacto
            feriados = db.session.query(Feriados.ferData).filter(or_(Feriados.ufId==pacto.ufId,Feriados.ufId==None)).all()
            feriados = [f.ferData for f in feriados]

            qtd_dias_uteis = 1 + np.busday_count(pacto.dataInicio,form.data_fim.data,weekmask=[1,1,1,1,1,0,0],holidays=feriados)

            # tempo total que o pacto teria frente à nova data de término
            tempo_total_pretendido = qtd_dias_uteis * pacto.cargaHorariaDiaria

            # calcula a soma dos tempos previstos das atividades no pacto
            ativs = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id).all()
            ativs_tempo_total = [float(t.tempoPrevistoTotal) for t in ativs]
            sum_ativs_tempo_total = sum(ativs_tempo_total)

            if tempo_total_pretendido < sum_ativs_tempo_total:
                flash('O novo prazo não compreende a quantidade de atividades que o pacto possui no momento\
                      ('+str(tempo_total_pretendido)+'h para o pacto < '+ str(sum_ativs_tempo_total).replace('.',',') +'h das atividades)!','erro')

                return redirect(url_for('demandas.demanda',pacto_id=pacto_id))
            
            dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                         "dataFim":(form.data_fim.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                         "descricao":form.desc.data}
        
        elif tipo_solic.descricao == 'Prazo de atividade ultrapassado':
            
            dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                         "pactoTrabalhoAtividadeId":form.atividade.data,\
                         "justificativa":form.desc.data}
        
        elif tipo_solic.descricao == 'Excluir atividade':

            ativ = db.session.query(Atividades.titulo,
                                    Atividades.complexidade,
                                    Atividades.tempoPresencial,
                                    Atividades.tempoRemoto)\
                             .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == form.atividade.data)\
                             .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.itemCatalogoId==Atividades.itemCatalogoId)\
                             .first()

            dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                         "pactoTrabalhoAtividadeId":form.atividade.data.lower(),\
                         "itemCatalogo":ativ.titulo + " - " + ativ.complexidade + " (pres.:" + str(ativ.tempoPresencial).replace('.',',') + \
                                       "h / rem.:" + str(ativ.tempoRemoto).replace('.',',') +"h)",\
                         "justificativa":form.desc.data}
 
        
        nova_solic = Pactos_de_Trabalho_Solic(pactoTrabalhoSolicitacaoId = uuid.uuid4(),
                                              pactoTrabalhoId            = pacto_id,  
                                              tipoSolicitacaoId          = tipo,
                                              dataSolicitacao            = hoje,
                                              solicitante                = solicitante_id.pessoaId,
                                              dadosSolicitacao           = (str(dados_dic).replace("'",'"')).replace('None','null'),
                                              observacoesSolicitante     = form.desc.data,
                                              analisado                  = False,
                                              dataAnalise                = None,
                                              analista                   = None,
                                              aprovado                   = None,
                                              observacoesAnalista        = None)

        db.session.add(nova_solic)
            
        db.session.commit()

        registra_log_unid(current_user.id,'Solicitação '+ nova_solic.pactoTrabalhoSolicitacaoId +' inserida no banco de dados.')

        flash('Solicitação registrada!','sucesso')

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))


    return render_template('add_solicitacao.html', form=form, 
                                                   tipo=tipo_solic.descricao, 
                                                   pacto=pacto, 
                                                   items_cat=items_cat,
                                                   sum_ativs_tempo_total = sum_ativs_tempo_total)

#avaliando uma solicitação

@demandas.route('/solicitacao_analise/<solic_id>/<pacto_id>',methods=['GET','POST'])
@login_required
def solicitacao_analise(solic_id,pacto_id):
    """+---------------------------------------------------------------------------------+
       |Realiza a analise de uma solicitação em um pacto existente.                      |
       |                                                                                 |
       |Recebe o ID da solicitação como parâmetro.                                       |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.userEmail

    #pega id sisgp do usuário logado
    analista = db.session.query(Pessoas.pessoaId, Pessoas.pesNome).filter(Pessoas.pesEmail == email).first_or_404()

    #resgata a solicitação
    solicitacao  = db.session.query (label('id',Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId),
                                    (literal('Solicitação tipo "') + catdom.descricao + literal('" ')).label("tipo"),
                                    label('data',Pactos_de_Trabalho_Solic.dataSolicitacao),
                                    label('dataFim',Pactos_de_Trabalho_Solic.dataAnalise),
                                    label('tit',Pactos_de_Trabalho_Solic.dadosSolicitacao),
                                    label('obs',Pactos_de_Trabalho_Solic.observacoesSolicitante),
                                    Pactos_de_Trabalho_Solic.observacoesAnalista,
                                    Pactos_de_Trabalho_Solic.analisado,
                                    Pessoas.pesNome,
                                    Unidades.ufId)\
                             .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == solic_id)\
                             .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho_Solic.solicitante)\
                             .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Solic.tipoSolicitacaoId)\
                             .join(Pactos_de_Trabalho, Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Solic.pactoTrabalhoId)\
                             .join(Unidades,Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                             .first()                        

    dados_solic = ast.literal_eval(str(solicitacao.tit).replace('null','None').replace('true','True').replace('false','False'))                 

    form = SolicitacaoAnaliseForm()

    if form.validate_on_submit():

        analisado = db.session.query(Pactos_de_Trabalho_Solic).filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == solic_id).first()

        analisado.analisado           = True
        analisado.dataAnalise         = hoje
        analisado.analista            = analista.pessoaId
        analisado.aprovado            = int(form.aprovado.data)
        analisado.observacoesAnalista = form.observacoes.data

        db.session.commit()

        # o que fazer quando da aprovação de diferentes tipos de solicitação

        if analisado.aprovado:

            if solicitacao.tipo[18:22] == 'Nova':

                if dados_solic['execucaoRemota']:
                    modalidade = 103
                else:
                    modalidade = 101

                nova_ativ = Pactos_de_Trabalho_Atividades(pactoTrabalhoAtividadeId = uuid.uuid4(),
                                                          pactoTrabalhoId          = pacto_id,
                                                          itemCatalogoId           = dados_solic['itemCatalogoId'],
                                                          situacaoId               = dados_solic['situacaoId'],
                                                          quantidade               = 1,
                                                          tempoPrevistoPorItem     = dados_solic['tempoPrevistoPorItem'],
                                                          tempoPrevistoTotal       = dados_solic['tempoPrevistoPorItem'],
                                                          dataInicio               = dados_solic['dataInicio'],
                                                          dataFim                  = dados_solic['dataFim'],
                                                          tempoRealizado           = dados_solic['tempoRealizado'],
                                                          descricao                = dados_solic['descricao'],
                                                          tempoHomologado          = 0,
                                                          nota                     = 0,
                                                          justificativa            = '',
                                                          consideracoesConclusao   = '',
                                                          modalidadeExecucaoId     = modalidade)                 

                db.session.add(nova_ativ)
                db.session.commit()                      

                registra_log_unid(current_user.id,'Atividade ' + nova_ativ.pactoTrabalhoAtividadeId + ' inserida no pacto ' + pacto_id + '.')

                flash('Nova atividade registrada!','sucesso')

            elif solicitacao.tipo[18:24] == 'Altera':    

                pacto = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

                # calcula a quantidade de dias úteis entre as datas de início e fim do pacto
                feriados = db.session.query(Feriados.ferData).filter(or_(Feriados.ufId==solicitacao.ufId,Feriados.ufId==None)).all()
                feriados = [f.ferData for f in feriados]

                qtd_dias_uteis = 1 + np.busday_count(pacto.dataInicio,pacto.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados)

                # altera a data fim do pacto e recalcula o tempo total disponível
                pacto.dataFim = dados_solic['dataFim']
                pacto.tempoTotalDisponivel = int(pacto.cargaHorariaDiaria * qtd_dias_uteis)

                db.session.commit()

                registra_log_unid(current_user.id,'Pacto ' + pacto_id + ' teve sua data final alterada.')

                flash('Data fim do pacto foi alterada!','sucesso')

            elif solicitacao.tipo[16:] == '"Prazo de atividade ultrapassado"':    

                print('*** ', solicitacao.tipo, ' - nada foi feito')
                # nada a fazer?

            elif solicitacao.tipo[18:25] == 'Excluir':    

                ativ_pacto_id = dados_solic["pactoTrabalhoAtividadeId"]

                # deleta eventual relação da atividade do pacto com objetos    
                obj = db.session.query(Objeto_Atividade_Pacto).filter(Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == ativ_pacto_id).delete()

                db.session.commit()

                # deleta atividade no pacto
                ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()

                if ativ == None:
                    abort(404)

                db.session.delete(ativ)
                db.session.commit()

                registra_log_unid(current_user.id,'Atividade  '+ ativ_pacto_id +' foi retirada do pacto de trabalho mediante aprovação.')
                
                flash('Atividade retirada do pacto de trabalho!','sucesso')    
    
        registra_log_unid(current_user.id,'Solicitação '+ solic_id +' foi analisada.')

        flash('Solicitação analisada!','sucesso')

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('analisa_solicitacao.html', form=form, 
                                                       pacto_id=pacto_id,
                                                       solicitacao=solicitacao,
                                                       dados_solic=dados_solic,
                                                       analista = analista)


# vendo todas as demandas de um usuário

@demandas.route('/<lista>/<int:pessoa_id>/list_demandas_usu')
def list_demandas_usu(lista,pessoa_id):

    """
        +----------------------------------------------------------------------+
        |Lista todas as demandas (pactos de trabalho), de uma determinada      |
        |pessoa.                                                               |
        |                                                                      |
        |Recebe o id da pessoa como parâmetro.                                 |
        +----------------------------------------------------------------------+
    """

    #pega e-mail do usuário logado
    email = current_user.userEmail

    # possibilidade de consultar outra pessoa
    if pessoa_id != 0:
        #pega dados da pessoa informada
        pes = db.session.query(Pessoas.unidadeId,Pessoas.pessoaId,Pessoas.pesNome)\
                                .filter(Pessoas.pessoaId == pessoa_id).first()
        if pes == None:
            abort(404)
    else:
        #pega dados da pessoa logada
        pes = db.session.query(Pessoas.unidadeId,Pessoas.pessoaId,Pessoas.pesNome)\
                            .filter(Pessoas.pesEmail == email).first()
    
    unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                        .filter(Unidades.unidadeId == pes.unidadeId)\
                        .join(VW_Unidades, VW_Unidades.id_unidade == Unidades.unidadeId)\
                        .first()

    # unid = pes.unidadeId    
      
    if lista == 'Todas':
        lista = '%'

    page = request.args.get('page', 1, type=int)

    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

    if lista != '%':

        lista = ast.literal_eval(lista)

        demandas = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
                                    Pactos_de_Trabalho.planoTrabalhoId,
                                    Pactos_de_Trabalho.dataInicio,
                                    Pactos_de_Trabalho.dataFim,
                                    Pactos_de_Trabalho.cargaHorariaDiaria,
                                    Pactos_de_Trabalho.percentualExecucao,
                                    Pactos_de_Trabalho.relacaoPrevistoRealizado,
                                    Pactos_de_Trabalho.tempoTotalDisponivel,
                                    Pactos_de_Trabalho.formaExecucaoId,
                                    Pactos_de_Trabalho.situacaoId,
                                    Pessoas.pesNome,
                                    Unidades.unidadeId,
                                    Unidades.undSigla,
                                    catdom_1.c.descricao,
                                    label('forma',catdom.descricao))\
                            .filter(Pactos_de_Trabalho.pessoaId == pes.pessoaId,
                                    Pactos_de_Trabalho.formaExecucaoId == lista[0],
                                    Pactos_de_Trabalho.situacaoId == lista[1])\
                            .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                            .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                            .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                            .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                            .order_by(Pactos_de_Trabalho.dataInicio.desc())\
                            .paginate(page=page,per_page=8)

        demandas_count = demandas.total

    else:    
    
        demandas = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
                                Pactos_de_Trabalho.planoTrabalhoId,
                                Pactos_de_Trabalho.dataInicio,
                                Pactos_de_Trabalho.dataFim,
                                Pactos_de_Trabalho.cargaHorariaDiaria,
                                Pactos_de_Trabalho.percentualExecucao,
                                Pactos_de_Trabalho.relacaoPrevistoRealizado,
                                Pactos_de_Trabalho.tempoTotalDisponivel,
                                Pessoas.pesNome,
                                Unidades.unidadeId,
                                Unidades.undSigla,
                                catdom_1.c.descricao,
                                label('forma',catdom.descricao))\
                            .filter(Pactos_de_Trabalho.pessoaId == pes.pessoaId)\
                            .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                            .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                            .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                            .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                            .order_by(Pactos_de_Trabalho.dataInicio.desc())\
                            .paginate(page=page,per_page=8)

        # demandas_count = db.session.query(Pactos_de_Trabalho)\
        #                         .filter(Pactos_de_Trabalho.pessoaId == pes.pessoaId)\
        #                         .count()

        demandas_count = demandas.total                        

                         

    # pega as atividades de cada demanda
    # dem = db.session.query(Pactos_de_Trabalho.planoTrabalhoId)\
    #                 .filter(Pactos_de_Trabalho.unidadeId == unid)\
    #                 .all()
    
    # pts = [item.planoTrabalhoId for item in dem]

    # items_cat = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId, Atividades.titulo)\
    #                       .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId.in_(pts))\
    #                       .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
    #                       .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
    #                       .order_by(Atividades.titulo)\
    #                       .all()
    #

    return render_template ('demandas_pessoa.html', lista=lista, 
                                                    # items_cat=items_cat, 
                                                    demandas=demandas, 
                                                    demandas_count=demandas_count,
                                                    unid_dados = unid_dados,
                                                    nome = pes.pesNome)


#iniciando ou finalizando uma atividade em pacto de trabalho

@demandas.route('/inicia_finaliza_atividade/<pacto_id>/<ativ_pacto_id>/<acao>',methods=['GET','POST'])
@login_required
def inicia_finaliza_atividade(pacto_id,ativ_pacto_id,acao):
    """+---------------------------------------------------------------------------------+
       |Inicia uma atividade planejada em um pacto de trabalho.                          |
       |                                                                                 |
       |Recebe o ID da atividade no pacto e ID da atividade como parâmetros.             |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.userEmail

    ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()

    form = InciaConcluiAtivForm()

    if ativ.consideracoesConclusao != None:
        consid = 'Considerações: ' + ativ.consideracoesConclusao
    else:
        consid = 'Considerações: N.I.'

    if form.validate_on_submit():

        if acao == 'i':
            ativ.situacaoId = 502
            ativ.dataInicio = form.data_ini.data
            ativ.consideracoesConclusao = form.consi_conclu.data
            
        elif acao == 'f':
            ativ.situacaoId     = 503
            if ativ.dataInicio == None or ativ.dataInicio == '':
                ativ.dataInicio = form.data_ini.data
            ativ.dataFim        = form.data_fim.data
            ativ.tempoRealizado = form.tempo_realizado.data.replace(',','.')
            ativ.consideracoesConclusao = consid + ' - Conclusão: ' + form.consi_conclu.data

        db.session.commit()

        if acao == 'i':
            registra_log_unid(current_user.id,'Atividade  '+ ativ_pacto_id +' foi colocada em execução.')
            flash('Atividade colocada em execução!','sucesso')
        elif acao == 'f':
            registra_log_unid(current_user.id,'Atividade  '+ ativ_pacto_id +' foi concluída.')
            flash('Atividade concluída!','sucesso')

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('inicia_conclui_atividade.html', form=form, acao=acao, sit = ativ.situacaoId)

#avaliando uma solicitação
@demandas.route('/avalia_atividade/<pacto_id>/<ativ_pacto_id>',methods=['GET','POST'])
@login_required
def avalia_atividade(pacto_id,ativ_pacto_id):
    """+---------------------------------------------------------------------------------+
       |Avalia uma atividade concluida em um pacto de trabalho.                          |
       |                                                                                 |
       |Recebe o ID da atividade no pacto e ID da atividade como parâmetros.             |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.userEmail

    #pega id sisgp do usuário logado
    avaliador = db.session.query(Pessoas.pessoaId, Pessoas.pesNome).filter(Pessoas.pesEmail == email).first_or_404()

    ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()

    form = AvaliaAtivForm()

    if form.validate_on_submit():

        ativ.nota = form.nota.data
        if form.tempo_homologado.data == None or form.tempo_homologado.data == '':
            ativ.tempoHomologado = ativ.tempoRealizado
        else:
            ativ.tempoHomologado = str(form.tempo_homologado.data).replace(',','.')
        ativ.justificativa = form.justificativa.data
            
        db.session.commit()

        registra_log_unid(current_user.id,'Atividade  '+ ativ_pacto_id +' foi avaliada.')
        
        flash('Atividade avaliada!','sucesso')

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('avalia_atividade.html', form=form, avaliador = avaliador)

# # procurando uma demanda

# @demandas.route('/pesquisa', methods=['GET','POST'])
# def pesquisa_demanda():
#     """+--------------------------------------------------------------------------------------+
#        |Permite a procura por demandas conforme os campos informados no respectivo formulário.|
#        |                                                                                      |
#        |Envia a string pesq para a função list_pesquisa, que executa a busca.                 |
#        +--------------------------------------------------------------------------------------+
#     """

#     pesquisa = True

#     form = PesquisaForm()

#     if form.validate_on_submit():
#         # a / do campo sei precisou ser trocada por _ para poder ser passado no URL da pesquisa
#         if str(form.sei.data).find('/') != -1:

#             pesq = str(form.sei.data).split('/')[0]+'_'+str(form.sei.data).split('/')[1]+';'+\
#                    str(form.titulo.data)+';'+\
#                    str(form.tipo.data)+';'+\
#                    str(form.necessita_despacho.data)+';'+\
#                    str(form.conclu.data)+';'+\
#                    str(form.convênio.data)+';'+\
#                    str(form.autor.data)+';'+\
#                    str(form.demanda_id.data)+';'+\
#                    str(form.atividade.data)+';'+\
#                    str(form.coord.data)+';'+\
#                    str(form.necessita_despacho_cg.data)

#         else:

#             pesq = str(form.sei.data)+';'+\
#                    str(form.titulo.data)+';'+\
#                    str(form.tipo.data)+';'+\
#                    str(form.necessita_despacho.data)+';'+\
#                    str(form.conclu.data)+';'+\
#                    str(form.convênio.data)+';'+\
#                    str(form.autor.data)+';'+\
#                    str(form.demanda_id.data)+';'+\
#                    str(form.atividade.data)+';'+\
#                    str(form.coord.data)+';'+\
#                    str(form.necessita_despacho_cg.data)

#         return redirect(url_for('demandas.list_pesquisa',pesq = pesq))

#     return render_template('pesquisa_demanda.html', form = form)

# # lista as demandas com base em uma procura

# @demandas.route('/<pesq>/list_pesquisa')
# def list_pesquisa(pesq):
#     """+--------------------------------------------------------------------------------------+
#        |Com os dados recebidos da formulário de pesquisa, traz as demandas, bem como          |
#        |providências e despachos, encontrados no banco de dados.                              |
#        |                                                                                      |
#        |Recebe a string pesq (dados para pesquisa) como parâmetro.                            |
#        +--------------------------------------------------------------------------------------+
#     """

#     pesquisa = True

#     page = request.args.get('page', 1, type=int)

#     pesq_l = pesq.split(';')

#     sei = pesq_l[0]
#     if sei.find('_') != -1:
#         sei = str(pesq_l[0]).split('_')[0]+'/'+str(pesq_l[0]).split('_')[1]

#     if pesq_l[2] == 'Todos':
#         p_tipo_pattern = ''
#     else:
#         p_tipo_pattern = pesq_l[2]

#     p_n_d = 'Todos'
#     if pesq_l[3] == 'Sim':
#         p_n_d = True
#     if pesq_l[3] == 'Não':
#         p_n_d = False

#     p_n_dcg = 'Todos'
#     if pesq_l[10] == 'Sim':
#         p_n_dcg = True
#     if pesq_l[10] == 'Não':
#         p_n_dcg = False

#     # p_conclu = 'Todos'
#     if pesq_l[4] == 'Todos':
#         p_conclu = ''
#     else:
#         p_conclu = pesq_l[4]

#     if pesq_l[6] != '':
#         autor_id = pesq_l[6]
#     else:
#         autor_id = '%'

#     if pesq_l[7] == '':
#         pesq_l[7] = '%'+str(pesq_l[7])+'%'
#     else:
#         pesq_l[7] = str(pesq_l[7])
#     #atividade
#     if pesq_l[8] == '':
#         pesq_l[8] = '%'+str(pesq_l[8])+'%'
#     else:
#         pesq_l[8] = str(pesq_l[8])

#     if pesq_l[9] == '':
#         pesq_l[9] = '%'
#     else:
#         pesq_l[9] = str(pesq_l[9])



#     demandas = db.session.query(Demanda.id,
#                                 Demanda.programa,
#                                 Demanda.sei,
#                                 Demanda.convênio,
#                                 Demanda.ano_convênio,
#                                 Demanda.tipo,
#                                 Demanda.data,
#                                 Demanda.user_id,
#                                 Demanda.titulo,
#                                 Demanda.desc,
#                                 Demanda.necessita_despacho,
#                                 Demanda.conclu,
#                                 Demanda.data_conclu,
#                                 Demanda.necessita_despacho_cg,
#                                 Demanda.urgencia,
#                                 Demanda.data_env_despacho,
#                                 Demanda.nota,
#                                 Plano_Trabalho.atividade_sigla,
#                                 User.coord,
#                                 User.username)\
#                          .join(User, User.id == Demanda.user_id)\
#                          .outerjoin(Plano_Trabalho, Plano_Trabalho.id == Demanda.programa)\
#                          .filter(Demanda.sei.like('%'+sei+'%'),
#                                  Demanda.convênio.like('%'+pesq_l[5]+'%'),
#                                  Demanda.titulo.like('%'+pesq_l[1]+'%'),
#                                  Demanda.tipo.like('%'+p_tipo_pattern+'%'),
#                                  Demanda.necessita_despacho != p_n_d,
#                                  Demanda.necessita_despacho_cg != p_n_dcg,
#                                  Demanda.conclu.like('%'+p_conclu+'%'),
#                                  Demanda.user_id.like (autor_id),
#                                  Demanda.id.like (pesq_l[7]),
#                                  Demanda.programa.like (pesq_l[8]),
#                                  User.coord.like (pesq_l[9]))\
#                          .order_by(Demanda.data.desc())\
#                          .paginate(page=page,per_page=8)

#     demandas_count  = demandas.total

#     providencias = db.session.query(Providencia.demanda_id,
#                                     Providencia.texto,
#                                     Providencia.data,
#                                     Providencia.user_id,
#                                     label('username',User.username),
#                                     Providencia.programada,
#                                     Providencia.passo)\
#                                     .outerjoin(User, Providencia.user_id == User.id)\
#                                     .order_by(Providencia.data.desc()).all()

#     despachos = db.session.query(Despacho.demanda_id,
#                                  Despacho.texto,
#                                  Despacho.data,
#                                  Despacho.user_id,
#                                  label('username',User.username +' - DESPACHO'),
#                                  User.despacha,
#                                  User.despacha2,
#                                  User.despacha0,
#                                  Despacho.passo)\
#                                 .outerjoin(User, Despacho.user_id == User.id)\
#                                 .order_by(Despacho.data.desc()).all()

#     pro_des = providencias + despachos
#     pro_des.sort(key=lambda ordem: ordem.data,reverse=True)

#     return render_template ('pesquisa.html', demandas_count = demandas_count, demandas = demandas,
#                              pro_des = pro_des, pesq = pesq, pesq_l = pesq_l)

