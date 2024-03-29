"""
.. topic:: Demandas (views)

    Compõe o trabalho diário da coordenação. Consistem das atividades da unidade, conforme cadastrado no PGD.
    Corresponde aos planos de atividades de cada um na unidade.

.. topic:: Ações relacionadas às demandas

    * Ver uma demanda (pacto de trabalho): demanda
    * Listar demandas da unidade (pactos de trabalho): list_demandas
    * Procurar demandas: pesquisa_demanda
    * Lista resultado da procura: list_pesquisa


"""

# views.py dentro da pasta demandas

from flask import render_template, url_for, flash, redirect, Blueprint, abort,send_from_directory
from flask_login import current_user, login_required
from sqlalchemy import or_, func, literal, case, distinct
from sqlalchemy.sql import label
from sqlalchemy.orm import aliased
from project import db
from project.models import Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs_Items, Unidades, Pessoas, Planos_de_Trabalho, \
                           Atividades, VW_Unidades, catdom, Pactos_de_Trabalho, Atividade_Candidato_Hist,\
                           Pactos_de_Trabalho_Solic, Pactos_de_Trabalho_Atividades, Atividade_Candidato,\
                           Pactos_de_Trabalho_Hist, Objetos, Objeto_Atividade_Pacto, Objeto_PG, Feriados, UFs,\
                           Assuntos, Atividade_Pacto_Assunto, Planos_de_Trabalho_Hist, Tipo_Func_Pessoa, Log_Unid

from project.demandas.forms import SolicitacaoForm601, SolicitacaoForm602, SolicitacaoForm603 , SolicitacaoForm604, SolicitacaoAnaliseForm,\
                                   PreSolicitacaoForm, InciaConcluiAtivForm, AvaliaAtivForm, AddAssuntoForm, CriaPlanoForm,\
                                   AnalisaPlano, SolicitacaoDesc

from project.usuarios.views import registra_log_unid                                   

from datetime import datetime, date

import uuid
import ast
import numpy as np
import math

import random
import string
from fpdf import FPDF
import os
import time

demandas = Blueprint("demandas",__name__,template_folder='templates')

def data_string(valor):
    if valor != None and valor != '':
        return valor.strftime('%d/%m/%Y')
    else:
        return 'N.I.'

def ponto_por_virgula(valor):
    if valor != None and valor != '':
        return str(valor).replace('.',',')
    else:
        return 'N.I.'            

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def pega_feriados(uf):
    # pega feriados do DBSISGP, acrescentando os fixos para o ano corrente
    feriados_db = db.session.query(Feriados.ferData,Feriados.ferFixo).filter(or_(Feriados.ufId==uf,Feriados.ufId==None)).all()
    feriados = []
    ano_corrente = int(date.today().year)
    for f in feriados_db:
        if f.ferFixo:
            intervalo = ano_corrente - int(f.ferData.strftime('%Y')) + 1
            for i in range(intervalo):
                feriados.append(date(ano_corrente-i,int(f.ferData.strftime('%m')),int(f.ferData.strftime('%d'))))
        else:
            feriados.append(f.ferData)
    return list(set(feriados))


class TimerError(Exception):
    """ Exceção customizada para relatar erros no uso da classe Timer """

class Timer:
    """ Mede intervalo de tempo entre dois eventos 
        Ex: t=Timer()                              
            tic = t.start()                        
              <alguma coisa rondando aqui>           
            toc = t.stop() 
        Em stop pode-se alterar a msg e o formato do resultado:
            toc = t.stop("** bla bla em {:0.2f} segundos")
        stop também retorna o valor do itervalo medido.
    """

    def __init__(self):
        self._start_time = None
    
    def start(self):
        """Iniciando um timer novo"""
        if self._start_time is not None:
            raise TimerError(f"Timer está rodando. Use .stop() para parar.")
        self._start_time = time.perf_counter()

    def stop(self,texto="Tempo decorrido: {:0.2f} segundos."):
        """Finaliza o timer e informa o tempo decorrido"""
        if self._start_time is None:
            raise TimerError(f"Timer não está rodando. Use .start() para iniciar.")
        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None
        print(texto.format(elapsed_time))

        return elapsed_time


#lendo uma demanda

@demandas.route('/demanda/<pacto_id>',methods=['GET','POST'])
@login_required
def demanda(pacto_id):

    """+---------------------------------------------------------------------------------+
       |Resgata, para leitura, uma demanda (plano no sisgp, pacto no banco) e registros  |
       |associados.                                                                      |
       |                                                                                 |
       |Recebe o ID do pacto como parâmetro.                                             |
       +---------------------------------------------------------------------------------+
    """

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first()

    # subquery das situações de pacto de trabalho
    catdom_1 = aliased(catdom)

    # pega o pacto (plano de trabalho) selecionado
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
                               catdom_1.descricao,
                               label('forma',catdom.descricao),
                               Planos_de_Trabalho.planoTrabalhoId,
                               UFs.ufId,
                               Pessoas.pesEmail,
                               Pactos_de_Trabalho.unidadeId,
                               Unidades.pessoaIdChefe,
                               Unidades.pessoaIdChefeSubstituto)\
                         .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                         .join(UFs, UFs.ufId == Unidades.ufId)\
                         .join(catdom_1, catdom_1.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                         .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Pactos_de_Trabalho.planoTrabalhoId)\
                         .first()
    

    #pega hierarquia superior da unidade da demanda
    unid = db.session.query(Unidades.unidadeId, Unidades.undSigla, VW_Unidades.undSiglaCompleta)\
                           .filter(Unidades.undSigla == demanda.undSigla)\
                           .outerjoin(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
                           .first()
    if unid.undSiglaCompleta != None:
        tree_sup = unid.undSiglaCompleta.split('/')
        tree_sup_ids = [u.unidadeId for u in Unidades.query.filter(Unidades.undSigla.in_(tree_sup))]
    else:
        tree_sup = None
        tree_sup_ids = []
   
    # pega feriados do DBSISGP, acrescentando os fixos para os anos de início de de fim da demanda (pacto)
    feriados = pega_feriados(demanda.ufId)

    # calcula a quantidade de dias úteis entre hoje e o fim do pacto - com feriados
    if np.is_busday(demanda.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados):
        n = 1
    else:
        n = 0
    qtd_dias_rest = n + np.busday_count(date.today(),demanda.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados)
    # calcula a quantidade de dias úteis entre as datas de início e fim do pacto - com feriados
    qtd_dias_uteis = n + np.busday_count(demanda.dataInicio,demanda.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados)

    # calcula a quantidade de dias úteis entre as datas de início e fim do pacto - sem feriados
    if np.is_busday(demanda.dataFim,weekmask=[1,1,1,1,1,0,0]):
        n = 1
    else:
        n = 0
    qtd_dias_uteis_sf = n + np.busday_count(demanda.dataInicio,demanda.dataFim,weekmask=[1,1,1,1,1,0,0])
    
    # pega as atividades, agrupadas por título, no plano do cidadão
    items_cat = db.session.query(Atividades.titulo,
                                 label('tam_grupo',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)),
                                 label('conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, 1)], else_=0))),
                                 label('exec',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 502, 1)], else_=0))),
                                 label('tempo_prev_total',func.sum(Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)),
                                 Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                 label('avaliada',func.sum(case([(Pactos_de_Trabalho_Atividades.nota != None, 1)], else_=0))))\
                          .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                          .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                          .group_by(Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                    Atividades.titulo)\
                          .order_by(Atividades.titulo)\
                          .all()

    # conta quantas atividades estão no plano
    qtd_items_cat = len(items_cat)
    
    # conta o número de objetos do PG ao qual o pacto está vinculado
    obj_pg_count = db.session.query(Objeto_PG)\
                        .filter(Objeto_PG.planoTrabalhoId == demanda.planoTrabalhoId)\
                        .count()

    # histórico, solicitações e atividades são agrupadas para uma visualização conjunta, para tal, 
    # todos tem que ter a mesma quandidade de campos

    historico_pg = db.session.query(label('id',Planos_de_Trabalho_Hist.planoTrabalhoHistoricoId),
                                label("situa",catdom.descricao),
                                literal('Histórico PG').label("tipo"),
                                label('data',Planos_de_Trabalho_Hist.DataOperacao),
                                literal(None).label('dataFim'),
                                label('tit',Planos_de_Trabalho_Hist.observacoes),
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
                          .filter(Planos_de_Trabalho_Hist.planoTrabalhoId == demanda.planoTrabalhoId)\
                          .join(catdom, catdom.catalogoDominioId == Planos_de_Trabalho_Hist.situacaoId)\
                          .join(Pessoas, Pessoas.pessoaId == Planos_de_Trabalho_Hist.responsavelOperacao)\
                          .order_by(Planos_de_Trabalho_Hist.DataOperacao.desc())\
                          .all()

    qtd_hist_pg = len(historico_pg)

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
    
    ## Atividades no plano (sisgp) ou pacto(banco)
    ativs    = db.session.query(label('id',Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId),
                                label('situa',catdom.descricao),
                                Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                Atividades.titulo,
                                Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)\
                         .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                         .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                         .all()

    qtd_ativs_pacto = len(ativs)   
    
    # gera lista das atividades do pacto acrescentando número de sequência para facilitar sua identificação
    ativs_simp    = db.session.query(label('id',Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId),
                                     Atividades.titulo,
                                     label('seq',func.row_number().over(order_by=(Pactos_de_Trabalho_Atividades.situacaoId))),
                                     Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                     label('situa',catdom.descricao),
                                     Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)\
                         .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                         .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                         .all()
    
    # calcula a soma dos tempos previstos das atividades no pacto por situação e totaliza tudo no final
    ativs_p_tempo_total = [float(t.tempoPrevistoPorItem) for t in ativs if t.situa == 'Programada']
    sum_ativs_p_tempo_total = round(sum(ativs_p_tempo_total),1)
    ativs_e_tempo_total = [float(t.tempoPrevistoPorItem) for t in ativs if t.situa == 'Em execução']
    sum_ativs_e_tempo_total = round(sum(ativs_e_tempo_total),1)
    ativs_c_tempo_total = [float(t.tempoPrevistoPorItem) for t in ativs if t.situa == 'Concluída']
    sum_ativs_c_tempo_total = round(sum(ativs_c_tempo_total),1)
    sum_ativs_tempo_total = sum_ativs_p_tempo_total + sum_ativs_e_tempo_total + sum_ativs_c_tempo_total
    
    # pegando solicitações
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
    
    #totalizar horas em pedidos de exclusão pendentes
    solic_exclu_pend = db.session.query(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId,
                                        Pactos_de_Trabalho_Solic.dadosSolicitacao)\
                                 .filter(Pactos_de_Trabalho_Solic.tipoSolicitacaoId == 604,
                                         Pactos_de_Trabalho_Solic.pactoTrabalhoId == pacto_id,
                                         Pactos_de_Trabalho_Solic.analisado == False)\
                                 .all()

    tempo_exclu = 0.0                             

    for solic in solic_exclu_pend:
        ativ_exclu_id = ast.literal_eval(str(solic.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False')) 

        tempo_ativ_exclu = db.session.query(Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)\
                                        .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_exclu_id['pactoTrabalhoAtividadeId'])\
                                        .first()

        tempo_exclu += float(tempo_ativ_exclu.tempoPrevistoPorItem)  
    
    # monta dicionários com o campo dadosSolicitacao das solicitações do pacto que está sendo visto
    dados_solic = [[s.id,ast.literal_eval(str(s.tit).replace('null','None').replace('true','True').replace('false','False'))] for s in solicit]

    # agrupa solicitações e historicos para a visão conjunta
    pro_des = solicit + historico + historico_pg

    # o agrupamento é então classificado por data na ordem decrescente, visando contar a história do mais recente para o mais antigo
    pro_des.sort(key=lambda ordem: (ordem.data is not None,ordem.data),reverse=True)

    # permite a inserção de nova solicitação com verificação prévia do tipo
    form1 = PreSolicitacaoForm()

    if form1.validate_on_submit():

        # caso a solicitação seja de nova atividade, verifica se há tempo disponível no pacto
        if form1.tipo.data == '601':
            if sum_ativs_tempo_total < demanda.tempoTotalDisponivel or tempo_exclu > 0:
                return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))
            else:
                flash('AVISO: O tempo total disponível no pacto já está todo comprometido','perigo')
                return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))

        # caso a solicitação seja de alterar prazo...
        if form1.tipo.data == '602':
            return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))

        # caso a solicitação seja de prazo de atividade ultrapassaso...
        if form1.tipo.data == '603':
            #flash('A opção de Justificar estouro de prazo está desabilitada','perigo')
            return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))    

        # caso a solicitação seja de excluir atividade do pacto, só é aberta a tela de solicitação se
        # houver atividades no pacto, caso contrario, repete a tela do pacto, mostrando uma msg flash
        if form1.tipo.data == '604':
            if qtd_ativs_pacto == 0:
                flash('Não há atividades no pacto para excluir!','erro')
            else:
                return redirect(url_for('demandas.solicitacao',pacto_id=pacto_id,tipo=form1.tipo.data))

    # calcular %execução e relação previsto/executado
    # pega as atividades no plano do cidadão
    itens_plano = db.session.query(label('tam_grupo',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)),
                                   label('tempo_prev_tot',func.sum((Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem))),
                                   label('tempo_realiz',func.sum((Pactos_de_Trabalho_Atividades.tempoRealizado))),
                                   label('tempo_prev_conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)], else_=0))),
                                   label('conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, 1)], else_=0))),
                                   label('exec',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 502, 1)], else_=0))))\
                            .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                            .first()                      

    if itens_plano.tempo_realiz == None:
        tempo_realiz = 0
    else:
        tempo_realiz = itens_plano.tempo_realiz 

    if itens_plano.tempo_prev_conclu == None:
        tempo_prev_conclu = 0
    else:
        tempo_prev_conclu = itens_plano.tempo_prev_conclu

    if itens_plano.conclu == None:
        itens_plano_conclu = 0
    else:
        itens_plano_conclu = itens_plano.conclu        

    # percentual de execução caculado pela relação quantidade de atividades concluidas / quantidade total de atividades no plano
    if itens_plano.tam_grupo == None or itens_plano.tam_grupo == '' or itens_plano.tam_grupo == 0:
        percentual_qtd_ativs_executado = 0 
    else:
        percentual_qtd_ativs_executado = round(100 * float(itens_plano_conclu) / float(itens_plano.tam_grupo),2)
    
    # percentual de execução calculado pela relação tempo realizado / tempo previsto no plano (todas as atividades)
    if itens_plano.tempo_prev_tot == None or itens_plano.tempo_prev_tot == '' or itens_plano.tempo_prev_tot == 0:
        percentual_tempo_realizado = 0
    else:
        percentual_tempo_realizado = round(100 * float(tempo_realiz) / float(itens_plano.tempo_prev_tot),2)
    
    # Verifica se tem assuntos e objetos relacionados às atividades 
    tem_assunto = {}
    tem_objeto = {}
    for a in ativs:
        assuntos = db.session.query(Atividade_Pacto_Assunto)\
                            .filter(Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId==a.id)\
                            .first()
        if assuntos:
            tem_assunto[a.titulo] = True

    for a in ativs:
        objetos = db.session.query(Objeto_Atividade_Pacto)\
                        .filter(Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == a.id)\
                        .first()
        if objetos:
            tem_objeto[a.titulo] = True
    

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
                            qtd_dias_rest = qtd_dias_rest,
                            sum_ativs_p_tempo_total = sum_ativs_p_tempo_total,
                            sum_ativs_e_tempo_total = sum_ativs_e_tempo_total,
                            sum_ativs_c_tempo_total = sum_ativs_c_tempo_total,
                            sum_ativs_tempo_total   = sum_ativs_tempo_total,
                            ativs_simp = ativs_simp,
                            qtd_ativs_pacto = qtd_ativs_pacto,
                            qtd_hist = qtd_hist + qtd_hist_pg,
                            qtd_solic = qtd_solic,
                            tree_sup_ids = tree_sup_ids,
                            percentual_qtd_ativs_executado = percentual_qtd_ativs_executado,
                            percentual_tempo_realizado = percentual_tempo_realizado,
                            tem_assunto = tem_assunto,
                            tem_objeto = tem_objeto)

# ocorrências de uma atividade
@demandas.route('/<pacto_id>/<item_cat_id>/ativ_ocor')
@login_required
def ativ_ocor(pacto_id,item_cat_id):

    """
        +------------------------------------------------------------------------+
        |Mostra as ocorrências de uma determinada atividade no plano de trabalho |
        |                                                                        |
        |Recebe o id da atividade como parâmetro.                                |
        +------------------------------------------------------------------------+
    """

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first()

    # pega o pacto selecionado
    demanda = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
                               Pessoas.pesNome,
                               Pactos_de_Trabalho.planoTrabalhoId,
                               Pactos_de_Trabalho.unidadeId,
                               Pactos_de_Trabalho.situacaoId)\
                         .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .first()

    #pega hierarquia superior da unidade da demanda
    unid = db.session.query(Unidades.unidadeId, Unidades.undSigla, VW_Unidades.undSiglaCompleta)\
                     .filter(Unidades.unidadeId == demanda.unidadeId)\
                     .outerjoin(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
                     .first()
    if unid.undSiglaCompleta:                 
        tree_sup = unid.undSiglaCompleta.split('/')
        tree_sup_ids = [u.unidadeId for u in Unidades.query.filter(Unidades.undSigla.in_(tree_sup))]
    else:
        tree_sup_ids = []                        

    # subquery das situações de atividades de pactos de trabalho
    catdom_2 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoAtividadePactoTrabalho')\
                         .subquery()                     
              
    ativs    = db.session.query(label('id',Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId),
                                label('situa',catdom_2.c.descricao),
                                Pactos_de_Trabalho_Atividades.nota,
                                Atividades.titulo,
                                Pactos_de_Trabalho_Atividades.quantidade,
                                Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                                Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                Pactos_de_Trabalho_Atividades.dataInicio,
                                Pactos_de_Trabalho_Atividades.dataFim,
                                label('tit',Pactos_de_Trabalho_Atividades.descricao),
                                label('desc',Pactos_de_Trabalho_Atividades.consideracoesConclusao),
                                catdom.descricao,
                                Pactos_de_Trabalho_Atividades.tempoRealizado,
                                Pactos_de_Trabalho_Atividades.tempoHomologado,
                                Pactos_de_Trabalho_Atividades.justificativa,
                                Pactos_de_Trabalho_Atividades.responsavelAvaliacao,
                                Pactos_de_Trabalho_Atividades.dataAvaliacao)\
                         .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id,
                                 Pactos_de_Trabalho_Atividades.itemCatalogoId == item_cat_id)\
                         .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.modalidadeExecucaoId)\
                         .join(catdom_2, catdom_2.c.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                         .order_by(Pactos_de_Trabalho_Atividades.dataInicio.desc(),Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                         .all()

    qtd_ativs = len(ativs)

    #calcula o tempo previsto total da atividade (soma das ocorrências)
    tempo_previsto_total = 0
    for a in ativs:
        tempo_previsto_total += a.tempoPrevistoPorItem

    # verificando se há solicitação de exclusão vinculada a cada uma das ocorrências da atividade consultada
    para_excluir = []
    solics = db.session.query(Pactos_de_Trabalho_Solic.dadosSolicitacao)\
                       .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId==pacto_id,
                               Pactos_de_Trabalho_Solic.tipoSolicitacaoId==604,
                               Pactos_de_Trabalho_Solic.analisado == False)\
                       .all()
    for s in solics:
        dados_s = ast.literal_eval(str(s.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False'))
        para_excluir.append(dados_s['pactoTrabalhoAtividadeId'].lower())
    cont=0    
    for a in ativs:
        if a.id.lower() in para_excluir:
            cont += 1
    if cont > 0:
        tem_exclu = True
    else:
        tem_exclu = False  

    # verificando se há solicitação de estouro de prazo vinculada a cada uma das ocorrências da atividade consultada
    para_justificar = []
    solics = db.session.query(Pactos_de_Trabalho_Solic.dadosSolicitacao)\
                       .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId==pacto_id,
                               Pactos_de_Trabalho_Solic.tipoSolicitacaoId==603,
                               Pactos_de_Trabalho_Solic.analisado == False)\
                       .all()
    for s in solics:
        dados_s = ast.literal_eval(str(s.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False'))
        para_justificar.append(dados_s['pactoTrabalhoAtividadeId'].lower())

    cont=0    
    for a in ativs:
        if a.id.lower() in para_justificar:
            cont += 1
    if cont > 0:
        tem_justificativa = True
    else:
        tem_justificativa = False      

    # resgata assuntos
    assuntos = db.session.query(Assuntos.chave,
                                Assuntos.valor,
                                Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                         .join(Atividade_Pacto_Assunto, Atividade_Pacto_Assunto.assuntoId == Assuntos.assuntoId)\
                         .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId)\
                         .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == item_cat_id,
                                 Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                         .order_by(Assuntos.chave.desc(),
                                   Assuntos.valor.desc())\
                         .all()
    qtd_assuntos = len(assuntos)  

    #resgata objetos
    objetos = db.session.query(Objetos.chave,
                               Objetos.descricao,
                               Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                        .join(Objeto_PG, Objeto_PG.objetoId==Objetos.objetoId)\
                        .join(Objeto_Atividade_Pacto,Objeto_Atividade_Pacto.planoTrabalhoObjetoId==Objeto_PG.planoTrabalhoObjetoId)\
                        .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId)\
                        .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == item_cat_id,
                                Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                        .all()  
    qtd_objetos = len(objetos)
    tem_objetos = []
    for obj in objetos:
        tem_objetos.append(obj.pactoTrabalhoAtividadeId)

    # retorna a parte decimal [posição 0] e a parte inteira [posição 1] da raiz quadrada em uma tupla
    qtd_ativs_sqr = math.modf(math.sqrt(qtd_ativs))

    # decidindo em quantas colunas e linhas as ocorrências serão mostradas (o máximo é 8)
    if qtd_ativs_sqr[1] >= 8.0:
        qtd_colunas = 8
        qtd_linhas = math.ceil(qtd_ativs/qtd_colunas)
    elif qtd_ativs_sqr[0] == 0:
        qtd_linhas = int(qtd_ativs_sqr[1]) 
        qtd_colunas = qtd_linhas
    else:
        qtd_linhas = int(qtd_ativs_sqr[1])
        qtd_colunas = math.ceil(qtd_ativs/qtd_linhas)

    return render_template('ativ_ocorrencias.html', ativs=ativs, qtd_ativs=qtd_ativs,
                                                    qtd_linhas=qtd_linhas, qtd_colunas=qtd_colunas,
                                                    usuario=usuario, demanda=demanda,
                                                    pacto_id=pacto_id,
                                                    tree_sup_ids=tree_sup_ids,
                                                    item_cat_id=item_cat_id,
                                                    assuntos=assuntos,
                                                    qtd_assuntos=qtd_assuntos,
                                                    objetos=objetos,
                                                    qtd_objetos=qtd_objetos,
                                                    tem_objetos=tem_objetos,
                                                    para_excluir=para_excluir,
                                                    tem_exclu=tem_exclu,
                                                    tem_justificativa=tem_justificativa,
                                                    para_justificar=para_justificar,
                                                    tempo_previsto_total=tempo_previsto_total)                   


# vendo todas as demandas da unidade
@demandas.route('/<lista>/<coord>/demandas')
@login_required
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
    email = current_user.pesEmail

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first()

    #pega unidadeId do usuário logado e undSigla na tabela Unidades
    unid_id = db.session.query(Pessoas.unidadeId).filter(Pessoas.pesEmail == email).first()
    unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                           .filter(Unidades.unidadeId == unid_id.unidadeId)\
                           .join(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
                           .first()
    unid = unid_id.unidadeId

    #possibilidade de ver outra unidade
    if coord != '*':
        unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                               .outerjoin(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
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
         
    #  
    if lista == 'Todas':
        lista = '%'

    #subquery para pegar situações dos planos de trabalho (pactos)
    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

    #subquery que conta atividades em cada plano de trabalho (pacto)
    ativs = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoId,
                             label('qtd_ativs',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)))\
                      .group_by(Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                      .subquery()
    
    #subquery que conta atividades com nota em cada plano de trabalho (pacto)
    ativs_com_nota = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoId,
                                      label('qtd_com_nota',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)))\
                               .filter(Pactos_de_Trabalho_Atividades.nota != None)\
                               .group_by(Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                               .subquery()                      

    com_nota = False
    icps = {}

    if lista == 'solic_pend':

        demandas = db.session.query(distinct(Pactos_de_Trabalho.pactoTrabalhoId),
                                    Pactos_de_Trabalho.pactoTrabalhoId,
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
                                    label('forma',catdom.descricao),
                                    Pessoas.pesEmail,
                                    Pactos_de_Trabalho.situacaoId)\
                            .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]),
                                    Pactos_de_Trabalho_Solic.analisado == False,
                                    catdom_1.c.descricao == 'Em execução')\
                            .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                            .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                            .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                            .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                            .join(Pactos_de_Trabalho_Solic, Pactos_de_Trabalho_Solic.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .order_by(Unidades.unidadeId,Pactos_de_Trabalho.situacaoId,Pactos_de_Trabalho.dataInicio.desc())\
                            .all()

        demandas_count = db.session.query(label('pactoTrabahoId',distinct(Pactos_de_Trabalho.pactoTrabalhoId)))\
                                   .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]),
                                           Pactos_de_Trabalho_Solic.analisado == False,
                                           catdom_1.c.descricao == 'Em execução')\
                                   .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                   .join(Pactos_de_Trabalho_Solic, Pactos_de_Trabalho_Solic.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                                   .count()

        demandas_count_pai = db.session.query(label('pactoTrabahoId',distinct(Pactos_de_Trabalho.pactoTrabalhoId)))\
                                       .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]),
                                               Pactos_de_Trabalho_Solic.analisado == False,
                                               catdom_1.c.descricao == 'Em execução')\
                                       .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                       .join(Pactos_de_Trabalho_Solic, Pactos_de_Trabalho_Solic.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                                       .count()                    

    elif lista == 'para_avaliar':    

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
                                    label('forma',catdom.descricao),
                                    Pessoas.pesEmail,
                                    Pactos_de_Trabalho.situacaoId,
                                    ativs.c.qtd_ativs,
                                    ativs_com_nota.c.qtd_com_nota)\
                            .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]),
                                    catdom_1.c.descricao == 'Executado',
                                    or_(ativs_com_nota.c.qtd_com_nota == None, ativs_com_nota.c.qtd_com_nota <  ativs.c.qtd_ativs))\
                            .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                            .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                            .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                            .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                            .order_by(Unidades.unidadeId,Pactos_de_Trabalho.situacaoId,Pactos_de_Trabalho.dataInicio.desc())\
                            .outerjoin(ativs_com_nota, ativs_com_nota.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .outerjoin(ativs, ativs.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .all()

        demandas_count = db.session.query(Pactos_de_Trabalho)\
                                .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                .outerjoin(ativs_com_nota, ativs_com_nota.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                                .outerjoin(ativs, ativs.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                                .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]),
                                        catdom_1.c.descricao == 'Executado',
                                        or_(ativs_com_nota.c.qtd_com_nota == None, ativs_com_nota.c.qtd_com_nota <  ativs.c.qtd_ativs))\
                                .count()

        demandas_count_pai = db.session.query(Pactos_de_Trabalho)\
                                    .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                    .outerjoin(ativs_com_nota, ativs_com_nota.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                                    .outerjoin(ativs, ativs.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                                    .filter(Pactos_de_Trabalho.unidadeId == unid,
                                            catdom_1.c.descricao == 'Executado',
                                            or_(ativs_com_nota.c.qtd_com_nota == None, ativs_com_nota.c.qtd_com_nota <  ativs.c.qtd_ativs))\
                                    .count()  

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
                                    label('forma',catdom.descricao),
                                    Pessoas.pesEmail,
                                    Pactos_de_Trabalho.situacaoId,
                                    ativs.c.qtd_ativs,
                                    ativs_com_nota.c.qtd_com_nota)\
                            .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]), catdom_1.c.descricao.like(lista))\
                            .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                            .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                            .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                            .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                            .order_by(Unidades.unidadeId,Pactos_de_Trabalho.situacaoId,Pactos_de_Trabalho.dataInicio.desc())\
                            .outerjoin(ativs_com_nota, ativs_com_nota.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .outerjoin(ativs, ativs.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .all()

        demandas_count = db.session.query(Pactos_de_Trabalho)\
                                .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                .filter(Pactos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]), catdom_1.c.descricao.like(lista))\
                                .count()

        demandas_count_pai = db.session.query(Pactos_de_Trabalho)\
                                    .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                    .filter(Pactos_de_Trabalho.unidadeId == unid, catdom_1.c.descricao.like(lista))\
                                    .count()  

        icps = {}
        for d in demandas:

            # verifica se há plano de trabalho (pacto) com nota atribuida em alguma atividade
            if d.qtd_com_nota != None:
                com_nota = True 

            # calcula icp para cada plano
            ativs_plano = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId,
                                            Pactos_de_Trabalho_Atividades.dataInicio)\
                                    .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == d.pactoTrabalhoId).all()

            log_plano = db.session.query(Log_Unid.msg, Log_Unid.data_hora)\
                                    .filter(Log_Unid.msg.like('Atividade%'),
                                            Log_Unid.msg.like('% colocada em execução.'),
                                            Log_Unid.data_hora > d.dataInicio).all()

            # iri é o índice de registro de íncio de atividade
            # iri próximo de 1: registro de início de atividade próximo do início do plano
            # iri próximo de 0: registro de início de atividade próxomo ao final do plano
            iris = []
            reg_log = 0
            if log_plano:
                for l in log_plano:
                    if l.msg[11:47] in [a.pactoTrabalhoAtividadeId for a in ativs_plano]:
                        reg_log += 1
                        dif_data_plano = (d.dataFim - d.dataInicio).days
                        if not(d.dataFim - l.data_hora.date()) or (d.dataFim - l.data_hora.date()) == 0:
                            dif_data_reg = 0
                        elif d.dataFim < l.data_hora.date():
                            dif_data_reg = -1    
                        else:    
                            dif_data_reg = (d.dataFim - l.data_hora.date()).days
                        if not dif_data_plano or dif_data_plano == 0:
                            iri = dif_data_reg
                        else:    
                            iri = dif_data_reg/dif_data_plano
                        iris.append(iri)
                # icp é o índice de comprometimento agregado para o plano 
                # corresponde à média dos iris vezes o peso correspondente à quantidade relativa de atividades iniciadas
                # icp próximo de 1: em média, atividades tiveram registros de início próximos ao início plano
                # icp próximo de 0: em média, atividades tiveram registros de início próximos ao final plano
                if len(iris) > 0: 
                    peso = reg_log/len(ativs_plano)       
                    icp = round(peso*(sum(iris)/len(iris)),2)
                    icps[d.pactoTrabalhoId] = icp
                else:
                    icp = 0
            else:
                icp = 0

    return render_template ('planos.html', lista=lista, 
                                             coord=coord, 
                                             demandas=demandas, 
                                             demandas_count=demandas_count,
                                             demandas_count_pai=demandas_count_pai,
                                             unid_dados = unid_dados,
                                             usuario = usuario,
                                             com_nota=com_nota,
                                             icps = icps)


#inserindo uma solicitação em um plano (pacto)
@demandas.route('/solicitacao/<pacto_id>/<tipo>',methods=['GET','POST'])
@login_required
def solicitacao(pacto_id,tipo):

    """+---------------------------------------------------------------------------------+
       |Insere uma solicitação para um pacto existente.                                  |
       |                                                                                 |
       |Recebe o ID do pacto e o tipo de solicitação como parâmetros.                    |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega id sisgp e unidade do usuário logado
    solicitante_id = db.session.query(Pessoas.pessoaId, Pessoas.unidadeId, Pessoas.tipoFuncaoId).filter(Pessoas.pesEmail == email).first()

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
                             Pessoas.pessoaId,
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
    
    # pega os grupos de ativivades no pacto 
    grupos_ativs_pacto = db.session.query(label('tam_grupo',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)),
                                          Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                          Atividades.titulo)\
                                   .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                                   .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                                   .group_by(Pactos_de_Trabalho_Atividades.itemCatalogoId, Atividades.titulo)\
                                   .all()

    # pega atividades em cada grupo
    if grupos_ativs_pacto:
        for a in grupos_ativs_pacto:
            ativs_grupo = db.session.query(label('seq',func.row_number().over(order_by=(Pactos_de_Trabalho_Atividades.dataInicio.desc(),Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId))),\
                                        label('tam_grupo',literal(a.tam_grupo)),
                                        Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId, 
                                        Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                        Atividades.titulo,
                                        Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                        Pactos_de_Trabalho_Atividades.dataInicio,
                                        Pactos_de_Trabalho_Atividades.situacaoId,
                                        Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                                        Pactos_de_Trabalho_Atividades.tempoRealizado)\
                                    .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == a.itemCatalogoId,
                                            Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                                    .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                                    .all()
            if grupos_ativs_pacto.index(a) == 0:
                items_cat = ativs_grupo
            else:
                items_cat += ativs_grupo  
    else:
        items_cat = []                                  
                        
    # calcula a soma dos tempos previstos das atividades no pacto por situação e totaliza tudo no final
    ativs_tempo_total = [float(t.tempoPrevistoPorItem) for t in items_cat]
    sum_ativs_tempo_total = sum(ativs_tempo_total)

    items_cat_pg = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId,
                                    Atividades.itemCatalogoId,
                                    Atividades.titulo,
                                    Atividades.complexidade,
                                    Atividades.tempoPresencial,
                                    Atividades.tempoRemoto)\
                             .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId == pacto.planoTrabalhoId)\
                             .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                             .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
                             .order_by(Atividades.titulo)\
                             .all()                      

    # define qual formulario a ser utilizado, dependendo do tipo de solicitação
    
    # para pedir nova atividade
    if tipo_solic.descricao == 'Nova atividade':
        # o choices do campo atividade são definidos aqui e não no form
        lista_ativs = [(i.itemCatalogoId,(i.titulo+' - '+i.complexidade+\
                       ' - Pre: '+str(i.tempoPresencial).replace('.',',')+'h Rem: '+str(i.tempoRemoto).replace('.',',')+'h')) for i in items_cat_pg]
        lista_ativs.insert(0,('',''))
        form = SolicitacaoForm601()
        form.atividade.choices = lista_ativs

    # para pedir alteração de prazo 
    elif tipo_solic.descricao == 'Alteração prazo':
        form = SolicitacaoForm602()

    # para pedir exclusão de atividade 
    elif tipo_solic.descricao == 'Excluir atividade':
        lista_ativs = [(i.itemCatalogoId,i.titulo) for i in grupos_ativs_pacto]
        lista_ativs.insert(0,('',''))
        form = SolicitacaoForm604()
        form.atividade.choices = lista_ativs
    
    # caso escolham a 603 (Prazo de atividade ultrapassado)
    else:
        # o choices do campo atividade são definidos aqui e não no form
        lista_ativs = [(i.pactoTrabalhoAtividadeId, '['+str(i.seq)+'/'+str(i.tam_grupo)+'] '+i.titulo) for i in items_cat if (i.tempoRealizado and i.tempoRealizado > i.tempoPrevistoPorItem)]
        if len(lista_ativs) > 0:
            lista_ativs.insert(0,('',''))
        else:
            lista_ativs.insert(0,('','Não há atividade com tempo estourado!'))    
        form = SolicitacaoForm603()
        form.atividade.choices = lista_ativs
       
    if form.validate_on_submit():

        quantidade = 1

        ## solicitando inclusão de nova atividade no plano

        if tipo_solic.descricao == 'Nova atividade':

            quantidade = form.quantidade.data 

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

            #totalizar horas em pedidos de exclusão pendentes
            solic_exclu_pend = db.session.query(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId,
                                                Pactos_de_Trabalho_Solic.dadosSolicitacao)\
                                         .filter(Pactos_de_Trabalho_Solic.tipoSolicitacaoId == 604,
                                                 Pactos_de_Trabalho_Solic.pactoTrabalhoId == pacto_id,
                                                 Pactos_de_Trabalho_Solic.analisado == False)\
                                         .all()

            tempo_exclu = 0.0                             

            for solic in solic_exclu_pend:
                ativ_exclu_id = ast.literal_eval(str(solic.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False')) 

                tempo_ativ_exclu = db.session.query(Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)\
                                             .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_exclu_id['pactoTrabalhoAtividadeId'])\
                                             .first()

                tempo_exclu += float(tempo_ativ_exclu.tempoPrevistoPorItem)  


            if folga_tempo_pacto < 0 and float(tempo_ativ) > tempo_exclu:
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
                            "situacaoId":501,\
                            "situacao":"Programada",\
                            "tempoPrevistoPorItem":float(str(tempo_ativ).replace(',','.')),\
                            "tempoPrevistoPorItemStr":None,\
                            "dataInicio":None,\
                            "dataFim":None,\
                            "tempoRealizado":None,\
                            "descricao":form.desc.data.replace('"','')}

            elif form.situacao.data == '502': # Em execução

                dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                            "itemCatalogoId":form.atividade.data.lower(),\
                            "itemCatalogo":ativ.titulo + " - " + ativ.complexidade,\
                            "execucaoRemota":form.remoto.data,\
                            "situacaoId":502,\
                            "situacao":"Em execução",\
                            "tempoPrevistoPorItem":float(str(tempo_ativ).replace(',','.')),\
                            "tempoPrevistoPorItemStr":None,\
                            "dataInicio":(form.data_ini.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                            "dataFim":None,\
                            "tempoRealizado":None,\
                            "descricao":form.desc.data.replace('"','')}

            elif form.situacao.data == '503': # Concluída

                dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                            "itemCatalogoId":form.atividade.data.lower(),\
                            "itemCatalogo":ativ.titulo + " - " + ativ.complexidade,\
                            "execucaoRemota":form.remoto.data,\
                            "situacaoId":503,\
                            "situacao":"Concluída",\
                            "tempoPrevistoPorItem":float(str(tempo_ativ).replace(',','.')),\
                            "tempoPrevistoPorItemStr":None,\
                            "dataInicio":(form.data_ini.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                            "dataFim":(form.data_fim.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                            "tempoRealizado":float(str(form.tempo_real.data).replace(',','.')),\
                            "descricao":form.desc.data.replace('"','')}

        ## solicitando alteração de prazo do plano 

        elif tipo_solic.descricao == 'Alteração prazo':

            ## crítica tempo total disponível frente ao prazo solicitado  
            # calcula a quantidade de dias úteis entre as datas de início e fim do pacto
            # pega feriados do DBSISGP, acrescentando os fixos para os anos de início de de fim da demanda (pacto)
            feriados = pega_feriados(pacto.ufId)

            if np.is_busday(form.data_fim.data,weekmask=[1,1,1,1,1,0,0],holidays=feriados):
                n = 1
            else:
                n = 0
            qtd_dias_uteis = n + np.busday_count(pacto.dataInicio,form.data_fim.data,weekmask=[1,1,1,1,1,0,0],holidays=feriados)

            # tempo total que o pacto teria frente à nova data de término
            tempo_total_pretendido = qtd_dias_uteis * pacto.cargaHorariaDiaria

            # calcula a soma dos tempos previstos das atividades no pacto
            ativs = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id).all()
            ativs_tempo_total = [float(t.tempoPrevistoPorItem) for t in ativs]
            sum_ativs_tempo_total = sum(ativs_tempo_total)

            # diferença entre tempo já comprometido com tempo total pretendido
            dif_tempos = sum_ativs_tempo_total - tempo_total_pretendido

            if dif_tempos > 0:
                flash('O novo prazo não compreende o tempo em atividades que o plano possui no momento, será necessário \
                       excluir '+str(dif_tempos).replace('.',',')+'h do rol de atividades do plano!','erro')

            dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                         "dataFim":(form.data_fim.data).strftime('%Y-%m-%dT%H:%M:%S'),\
                         "descricao":form.desc.data.replace('"','')}
        
        ## solicitando estouro de prazo
        
        elif tipo_solic.descricao == 'Prazo de atividade ultrapassado':
            
            ativ = db.session.query(Pactos_de_Trabalho_Atividades.tempoRealizado)\
                             .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==form.atividade.data)\
                             .first()

            if ativ.tempoRealizado:

                dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                         "pactoTrabalhoAtividadeId":form.atividade.data.lower(),\
                         "justificativa":form.desc.data.replace('"','')}
            else:                            
                flash('Esta atividade não foi finalizada (não consta tempo realizado)!','erro')
                return redirect(url_for('demandas.demanda',pacto_id=pacto_id))
            
        ## solicitando a exclusão de atividades
        
        elif tipo_solic.descricao == 'Excluir atividade':

            quantidade = form.qtd.data

            ativs_grupo = db.session.query(label('seq',func.row_number().over(order_by=(Pactos_de_Trabalho_Atividades.situacaoId))),\
                                           Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId, 
                                           Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                           Atividades.titulo,
                                           Atividades.complexidade,
                                           Atividades.tempoPresencial,
                                           Atividades.tempoRemoto,
                                           Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                           Pactos_de_Trabalho_Atividades.dataInicio,
                                           Pactos_de_Trabalho_Atividades.situacaoId,
                                           Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)\
                                   .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == form.atividade.data,
                                        Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                                   .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                                   .order_by(Pactos_de_Trabalho_Atividades.situacaoId)\
                                   .all()
            qtd_ativs_grupo = len(ativs_grupo)

            dados_dic_l = []
            programadas = 0
            execucao = 0
            concluidas = 0

            if quantidade > qtd_ativs_grupo:
                flash('Verifique a quantidade de ocorrências, está maior do que o registrado na atividade!','erro')
                return render_template('add_solicitacao.html', form=form, 
                                                   tipo=tipo_solic.descricao, 
                                                   pacto=pacto, 
                                                   items_cat=items_cat,
                                                   sum_ativs_tempo_total = sum_ativs_tempo_total)

            for a in range (quantidade): 

                ativ_a_excluir = ativs_grupo[a]                   

                # verifica que já existe solicitação não analisada de excluão de atividade no o pactoTrabalhoAtividadeId escolhido
                solics_existentes = db.session.query(Pactos_de_Trabalho_Solic)\
                                            .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == pacto_id,
                                                    Pactos_de_Trabalho_Solic.tipoSolicitacaoId == 604,
                                                    Pactos_de_Trabalho_Solic.analisado == False)\
                                            .all()
                solics_existentes_l = []
                for s in solics_existentes:
                    ativ_pacto =  (ast.literal_eval(s.dadosSolicitacao))['pactoTrabalhoAtividadeId'].upper()  
                    solics_existentes_l.append(ativ_pacto)
                   
                if ativ_a_excluir.pactoTrabalhoAtividadeId in solics_existentes_l:
                    flash('Já consta solicitação de exclusão para ativ. '+ ativ_a_excluir.pactoTrabalhoAtividadeId+' ('+str(ativ_a_excluir.seq)+'). Será retirada do grupo de exclusão.','erro')
                    quantidade -= 1 # diminui a quantidad para o loop de registro de solicitação
                else:    
                    # monta dados da solicitação de exclusão
                    dados_dic = {"pactoTrabalhoId":pacto_id.lower(),\
                                "pactoTrabalhoAtividadeId":ativ_a_excluir.pactoTrabalhoAtividadeId.lower(),\
                                "itemCatalogo":ativ_a_excluir.titulo + " - " + ativ_a_excluir.complexidade + \
                                            " (pres.:" + str(ativ_a_excluir.tempoPresencial).replace('.',',') + \
                                            "h / rem.:" + str(ativ_a_excluir.tempoRemoto).replace('.',',') +"h)",\
                                "justificativa":form.desc.data.replace('"','')}

                    dados_dic_l.append(dados_dic) 

                    if ativ_a_excluir.situacaoId == 501:
                        programadas += 1
                    elif ativ_a_excluir.situacaoId == 502:
                        execucao += 1
                    elif ativ_a_excluir.situacaoId == 503:
                        concluidas += 1                    
 
        # faz o registro da, ou das, solicitações
        for i in range(quantidade):

            if tipo_solic.descricao == 'Excluir atividade':
                dados_solic = str(dados_dic_l[i]).replace("'",'"').replace('None','null').\
                                             replace('True','true').replace('False','false').\
                                             replace('": ','":').replace(', "',',"')

            else:    
                dados_solic = str(dados_dic).replace("'",'"').replace('None','null').\
                                             replace('True','true').replace('False','false').\
                                             replace('": ','":').replace(', "',',"')

            nova_solic = Pactos_de_Trabalho_Solic(pactoTrabalhoSolicitacaoId = uuid.uuid4(),
                                                  pactoTrabalhoId            = pacto_id,  
                                                  tipoSolicitacaoId          = tipo,
                                                  dataSolicitacao            = hoje,
                                                  solicitante                = solicitante_id.pessoaId,
                                                  dadosSolicitacao           = dados_solic,
                                                  observacoesSolicitante     = form.desc.data.replace('"',''),
                                                  analisado                  = False,
                                                  dataAnalise                = None,
                                                  analista                   = None,
                                                  aprovado                   = None,
                                                  observacoesAnalista        = None)

            db.session.add(nova_solic)
                
            db.session.commit()

            registra_log_unid(current_user.pessoaId,'Solicitação '+ nova_solic.pactoTrabalhoSolicitacaoId +\
                                              ' de '+ tipo_solic.descricao  +' inserida no banco de dados.')

        if quantidade == 0 and tipo_solic.descricao == 'Excluir atividade':
            flash('Solicitação de exclusão ignorada!','erro')
        elif tipo_solic.descricao == 'Excluir atividade':
            flash('Solicitação registrada. Exclusão de '+str(programadas)+' programadas, '+str(execucao)+' em execução e '+str(concluidas)+' concluidas.','sucesso')
        else:
            flash('Solicitação registrada.','sucesso')

        # se a solicitação foi postada pelo chefe no plano de um subordinado, ocorre a aprovação automática
        if pacto.pessoaId != solicitante_id.pessoaId and (solicitante_id.tipoFuncaoId or solicitante_id != ''):
            return redirect(url_for('demandas.solicitacao_chefe_analise',solic_id=nova_solic.pactoTrabalhoSolicitacaoId,pacto_id=pacto_id))     
        else:
            return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('add_solicitacao.html', form=form, 
                                                   tipo=tipo_solic.descricao, 
                                                   pacto=pacto, 
                                                   items_cat=items_cat,
                                                   sum_ativs_tempo_total = sum_ativs_tempo_total)


#registrado uma solicitação de exclusão de ocorrência em atividade de um plano (pacto)
@demandas.route('/exclu_ativ/<ativ_id>',methods=['GET','POST'])
@login_required
def exclu_ativ(ativ_id):

    """+---------------------------------------------------------------------------------+
       |Registra solicitação de exclusão da ocorrência de uma atividade em um            |
       |em um pacto existente.                                                           |
       |                                                                                 |
       |Recebe o ID da ocorrência como parâmetro.                                        |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega id sisgp e unidade do usuário logado
    solicitante_id = db.session.query(Pessoas.pessoaId, Pessoas.unidadeId, Pessoas.tipoFuncaoId).filter(Pessoas.pesEmail == email).first()

    # pega dados da ocorrência
    ocor = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoId,
                            Pactos_de_Trabalho_Atividades.itemCatalogoId,
                            Pactos_de_Trabalho_Atividades.descricao,
                            Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                            Pactos_de_Trabalho_Atividades.tempoRealizado,
                            Atividades.titulo,
                            Atividades.complexidade,
                            Atividades.tempoPresencial,
                            Atividades.tempoRemoto)\
                     .join(Atividades, Atividades.itemCatalogoId==Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                     .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==ativ_id).first()

    form = SolicitacaoDesc()
    
    if form.validate_on_submit():                 

        # monta dados da solicitação de exclusão
        dados_dic = {"pactoTrabalhoId":ocor.pactoTrabalhoId.lower(),\
                    "pactoTrabalhoAtividadeId":ativ_id.lower(),\
                    "itemCatalogo":ocor.titulo + " - " + ocor.complexidade + \
                                " (pres.:" + str(ocor.tempoPresencial).replace('.',',') + \
                                "h / rem.:" + str(ocor.tempoRemoto).replace('.',',') +"h)",\
                    "justificativa":form.desc.data.replace('"','')}

        dados_solic = str(dados_dic).replace("'",'"').replace('None','null').\
                                    replace('True','true').replace('False','false').\
                                    replace('": ','":').replace(', "',',"')

        nova_solic = Pactos_de_Trabalho_Solic(pactoTrabalhoSolicitacaoId = uuid.uuid4(),
                                              pactoTrabalhoId            = ocor.pactoTrabalhoId,  
                                              tipoSolicitacaoId          = 604,
                                              dataSolicitacao            = hoje,
                                              solicitante                = solicitante_id.pessoaId,
                                              dadosSolicitacao           = dados_solic,
                                              observacoesSolicitante     = form.desc.data,
                                              analisado                  = False,
                                              dataAnalise                = None,
                                              analista                   = None,
                                              aprovado                   = None,
                                              observacoesAnalista        = None)

        db.session.add(nova_solic)
                    
        db.session.commit()

        registra_log_unid(current_user.pessoaId,'Solicitação '+ nova_solic.pactoTrabalhoSolicitacaoId +\
                                        ' de exclusão de ocorrência de atividade inserida no banco de dados.') 

        flash('Solicitação de exclusão registrada.','sucesso')  

        return redirect(url_for('demandas.ativ_ocor', pacto_id=ocor.pactoTrabalhoId,item_cat_id=ocor.itemCatalogoId))

    return render_template('add_solicitacao.html', form = form, 
                                                   tipo = 'Excluir ocorrência de atividade', 
                                                   pacto = None, 
                                                   items_cat = ocor,
                                                   sum_ativs_tempo_total = None) 


#registrado uma solicitação de estouro de praxo em ocorrência de atividade em um plano (pacto)
@demandas.route('/prazo_ativ/<ativ_id>',methods=['GET','POST'])
@login_required
def prazo_ativ(ativ_id):

    """+---------------------------------------------------------------------------------+
       |Registra solicitação de estouro de prazo em ocorrência de uma atividade em um    |
       |em um pacto existente.                                                           |
       |                                                                                 |
       |Recebe o ID da ocorrência como parâmetro.                                        |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega id sisgp e unidade do usuário logado
    solicitante_id = db.session.query(Pessoas.pessoaId, Pessoas.unidadeId, Pessoas.tipoFuncaoId).filter(Pessoas.pesEmail == email).first()

    # pega dados da ocorrência
    ocor = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoId,
                            Pactos_de_Trabalho_Atividades.itemCatalogoId,
                            Pactos_de_Trabalho_Atividades.descricao,
                            Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                            Pactos_de_Trabalho_Atividades.tempoRealizado,
                            Atividades.titulo,
                            Atividades.complexidade,
                            Atividades.tempoPresencial,
                            Atividades.tempoRemoto)\
                     .join(Atividades, Atividades.itemCatalogoId==Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                     .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==ativ_id).first()

    form = SolicitacaoDesc()
    
    if form.validate_on_submit():                 

        # monta dados da solicitação de estouro de prazo
        dados_dic = {"pactoTrabalhoId":ocor.pactoTrabalhoId.lower(),\
                         "pactoTrabalhoAtividadeId":ativ_id.lower(),\
                         "justificativa":form.desc.data.replace('"','')}

        dados_solic = str(dados_dic).replace("'",'"').replace('None','null').\
                                    replace('True','true').replace('False','false').\
                                    replace('": ','":').replace(', "',',"')

        nova_solic = Pactos_de_Trabalho_Solic(pactoTrabalhoSolicitacaoId = uuid.uuid4(),
                                              pactoTrabalhoId            = ocor.pactoTrabalhoId,  
                                              tipoSolicitacaoId          = 603,
                                              dataSolicitacao            = hoje,
                                              solicitante                = solicitante_id.pessoaId,
                                              dadosSolicitacao           = dados_solic,
                                              observacoesSolicitante     = form.desc.data,
                                              analisado                  = False,
                                              dataAnalise                = None,
                                              analista                   = None,
                                              aprovado                   = None,
                                              observacoesAnalista        = None)

        db.session.add(nova_solic)
                    
        db.session.commit()

        registra_log_unid(current_user.pessoaId,'Solicitação '+ nova_solic.pactoTrabalhoSolicitacaoId +\
                                        ' de estouro de prazo em ocorrência de atividade inserida no banco de dados.') 

        flash('Solicitação de estouro de prazo registrada.','sucesso')  

        return redirect(url_for('demandas.ativ_ocor', pacto_id=ocor.pactoTrabalhoId,item_cat_id=ocor.itemCatalogoId))

    return render_template('add_solicitacao.html', form = form, 
                                                   tipo = 'Justificar estouro de prazo', 
                                                   pacto = None, 
                                                   items_cat = ocor,
                                                   sum_ativs_tempo_total = None)


#analisando uma solicitação
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
    email = current_user.pesEmail

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
                                    Unidades.ufId,
                                    Pactos_de_Trabalho_Solic.tipoSolicitacaoId)\
                             .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == solic_id)\
                             .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho_Solic.solicitante)\
                             .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Solic.tipoSolicitacaoId)\
                             .join(Pactos_de_Trabalho, Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Solic.pactoTrabalhoId)\
                             .join(Unidades,Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                             .first()                        

    dados_solic = ast.literal_eval(str(solicitacao.tit).replace('null','None').replace('true','True').replace('false','False'))   

    #pega dados da atividade para a qual a solicitação é feita, se for o caso (Prazo de atividade ultrapassado ou Excluir atividade)
    if solicitacao.tipoSolicitacaoId == 603 or solicitacao.tipoSolicitacaoId == 604:
        ativ_solic = db.session.query(Pactos_de_Trabalho_Atividades.descricao,
                                      Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                                      Pactos_de_Trabalho_Atividades.tempoRealizado,
                                      Atividades.titulo)\
                               .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==dados_solic['pactoTrabalhoAtividadeId'].upper())\
                               .join(Atividades,Atividades.itemCatalogoId==Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                               .first()      
    else:
        ativ_solic = None                                   

    # verifica se há multiplas solicitações de exclusão não analisadas para a mesma atividade
    ocor_ativ_id_l = []
    if solicitacao.tipo[18:25] == 'Excluir': 
        multi_exclu = db.session.query(Pactos_de_Trabalho_Solic)\
                                .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == pacto_id,
                                        Pactos_de_Trabalho_Solic.tipoSolicitacaoId == 604,
                                        Pactos_de_Trabalho_Solic.analisado == False)\
                                .all()
        for solic in multi_exclu:
            ocor_ativ_dados = ast.literal_eval(str(solic.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False'))
            if ocor_ativ_dados['itemCatalogo'] == dados_solic['itemCatalogo']:
                ocor_ativ_id_l.append([solic.pactoTrabalhoSolicitacaoId, ocor_ativ_dados['pactoTrabalhoAtividadeId']])

    ocor_ativ_qtd = len(ocor_ativ_id_l) 

    # verifica se há multiplas solicitações de nova atividade com mesmo título não analisadas para o mesmo plano
    ocor_nova_id_l = []
    if solicitacao.tipo[18:22] == 'Nova':
        multi_nova = db.session.query(Pactos_de_Trabalho_Solic)\
                               .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == pacto_id,
                                        Pactos_de_Trabalho_Solic.tipoSolicitacaoId == 601,
                                        Pactos_de_Trabalho_Solic.analisado == False)\
                               .all()
        for solic in multi_nova:
            ocor_nova_dados = ast.literal_eval(str(solic.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False'))
            if ocor_nova_dados['itemCatalogo'] == dados_solic['itemCatalogo']:
                ocor_nova_id_l.append(solic.pactoTrabalhoSolicitacaoId)
    ocor_nova_qtd = len(ocor_nova_id_l)     

    form = SolicitacaoAnaliseForm()

    if form.validate_on_submit():

        # se for análise de exclusão de atividade ou de inserção de nova, decide se faz em lote ou indivitual a partir do informado em replicas 
        if form.replicas.data: 

            if solicitacao.tipo[18:25] == 'Excluir': 

                for id in ocor_ativ_id_l:

                    analisado = db.session.query(Pactos_de_Trabalho_Solic).filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == id[0]).first()

                    analisado.analisado           = True
                    analisado.dataAnalise         = hoje
                    analisado.analista            = analista.pessoaId
                    analisado.aprovado            = int(form.aprovado.data)
                    analisado.observacoesAnalista = form.observacoes.data

                    db.session.commit()

            elif solicitacao.tipo[18:22] == 'Nova': 

                for id in ocor_nova_id_l:

                    analisado = db.session.query(Pactos_de_Trabalho_Solic).filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == id).first()

                    analisado.analisado           = True
                    analisado.dataAnalise         = hoje
                    analisado.analista            = analista.pessoaId
                    analisado.aprovado            = int(form.aprovado.data)
                    analisado.observacoesAnalista = form.observacoes.data

                    db.session.commit()        
        else:

            analisado = db.session.query(Pactos_de_Trabalho_Solic).filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == solic_id).first()

            analisado.analisado           = True
            analisado.dataAnalise         = hoje
            analisado.analista            = analista.pessoaId
            analisado.aprovado            = int(form.aprovado.data)
            analisado.observacoesAnalista = form.observacoes.data   

            db.session.commit()     

        # o que fazer quando da aprovação de diferentes tipos de solicitação

        if form.aprovado.data == '1':

            if solicitacao.tipo[18:22] == 'Nova':

                for id in ocor_nova_id_l: 

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
                                                              tempoHomologado          = None,
                                                              nota                     = None,
                                                              justificativa            = None,
                                                              consideracoesConclusao   = None,
                                                              modalidadeExecucaoId     = modalidade,
                                                              responsavelAvaliacao     = None,
                                                              dataAvaliacao            = None)                 

                    db.session.add(nova_ativ)
                    db.session.commit()                      

                    registra_log_unid(current_user.pessoaId,'Atividade ' + nova_ativ.pactoTrabalhoAtividadeId + ' inserida no plano ' + pacto_id + '.')

                flash(str(ocor_nova_qtd)+' nova(s) atividade(s) registrada(s)!','sucesso')

            elif solicitacao.tipo[18:24] == 'Altera':    

                pacto = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

                # calcula a quantidade de dias úteis entre as datas de início e fim do pacto
                # pega feriados do DBSISGP, acrescentando os fixos para os anos de início de de fim da demanda (pacto)
                feriados = pega_feriados(solicitacao.ufId)

                if np.is_busday(pacto.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados):
                    n = 1
                else:
                    n = 0
                qtd_dias_uteis = n + np.busday_count(pacto.dataInicio,pacto.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados)

                # altera a data fim do pacto e recalcula o tempo total disponível
                pacto.dataFim = dados_solic['dataFim']
                pacto.tempoTotalDisponivel = int(pacto.cargaHorariaDiaria * qtd_dias_uteis)

                db.session.commit()

                registra_log_unid(current_user.pessoaId,'Plano ' + pacto_id + ' teve sua data final alterada.')

                flash('Data fim do plano foi alterada!','sucesso')

            elif solicitacao.tipo[18:23] == 'Prazo':    

                # altera o tempo previsto por item e o tempo homologado, se for o caso, da atividade para o valor que a pessoa informou como executado
                ativ_pacto_id = dados_solic['pactoTrabalhoAtividadeId'].upper()
                ativ = db.session.query(Pactos_de_Trabalho_Atividades)\
                                 .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==ativ_pacto_id)\
                                 .first() 

                ativ.tempoPrevistoPorItem = ativ.tempoRealizado

                if ativ.tempoHomologado:
                    ativ.tempoHomologado = ativ.tempoRealizado     

                db.session.commit() 

                registra_log_unid(current_user.pessoaId,'Atividade  '+ dados_solic['pactoTrabalhoAtividadeId'] +' com estouro de prazo aprovado.')
                    
                flash('Estouro de prazo aprovado!','sucesso')   

            elif solicitacao.tipo[18:25] == 'Excluir': 

                if form.replicas.data: 

                    for id in ocor_ativ_id_l:

                        ativ_pacto_id = id[1].upper()

                        # deleta eventual relação da atividade do pacto com objetos    
                        obj = db.session.query(Objeto_Atividade_Pacto).filter(Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == ativ_pacto_id).delete()
                        db.session.commit()

                        # deleta relacionamentos das atividades com assuntos
                        assunto_ativ_exclu = db.session.query(Atividade_Pacto_Assunto).filter(Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId == ativ_pacto_id).delete()
                        db.session.commit()

                        # deleta atividade no pacto
                        ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()

                        if ativ == None:
                            abort(404)

                        db.session.delete(ativ)
                        db.session.commit()

                        registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi retirada do plano de trabalho mediante aprovação.')
                    
                    flash(str(ocor_ativ_qtd)+' atividade(s) retirada(s) do plano de trabalho!','sucesso') 
                
                else:    

                    ativ_pacto_id = dados_solic['pactoTrabalhoAtividadeId'].upper()

                    # deleta eventual relação da atividade do pacto com objetos    
                    obj = db.session.query(Objeto_Atividade_Pacto).filter(Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == ativ_pacto_id).delete()
                    db.session.commit()

                    # deleta relacionamenotos da atividade com assuntos
                    assunto_ativ_exclu = db.session.query(Atividade_Pacto_Assunto).filter(Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId == ativ_pacto_id).delete()
                    db.session.commit()

                    # deleta atividade no pacto
                    ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()

                    if ativ == None:
                        abort(404)

                    db.session.delete(ativ)
                    db.session.commit()

                    registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi retirada do plano de trabalho mediante aprovação.')
                    
                    flash('Atividade retirada do plano de trabalho!','sucesso')   
    
        if form.replicas.data:
            registra_log_unid(current_user.pessoaId,'Lote de solicitações a partir da '+ solic_id +' foi analisado.')
        else:
            registra_log_unid(current_user.pessoaId,'Solicitação '+ solic_id +' foi analisada.')

        flash('Solicitação analisada!','sucesso')

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('analisa_solicitacao.html', form = form, 
                                                       pacto_id = pacto_id,
                                                       solicitacao = solicitacao,
                                                       dados_solic = dados_solic,
                                                       analista = analista,
                                                       ocor_ativ_qtd = ocor_ativ_qtd,
                                                       ocor_nova_qtd = ocor_nova_qtd,
                                                       ativ_solic = ativ_solic)


#analisando automaticamente uma solicitação feita pelo chefe
@demandas.route('/solicitacao_chefe_analise/<solic_id>/<pacto_id>',methods=['GET','POST'])
@login_required
def solicitacao_chefe_analise(solic_id,pacto_id):
    """+---------------------------------------------------------------------------------+
       |Realiza a analise automatica de uma solicitação feita pelo chefe em um pacto     |
       |de uma pessoa na sua unidade existente.                                          |
       |                                                                                 |
       |Recebe o ID da solicitação e o o ID do pacto como parâmetros.                    |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

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

    # verifica se há multiplas solicitações de exclusão não analisadas para a mesma atividade
    ocor_ativ_id_l = []
    if solicitacao.tipo[18:25] == 'Excluir': 
        multi_exclu = db.session.query(Pactos_de_Trabalho_Solic)\
                                .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == pacto_id,
                                        Pactos_de_Trabalho_Solic.tipoSolicitacaoId == 604,
                                        Pactos_de_Trabalho_Solic.analisado == False)\
                                .all()
        for solic in multi_exclu:
            ocor_ativ_dados = ast.literal_eval(str(solic.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False'))
            if ocor_ativ_dados['itemCatalogo'] == dados_solic['itemCatalogo']:
                ocor_ativ_id_l.append([solic.pactoTrabalhoSolicitacaoId, ocor_ativ_dados['pactoTrabalhoAtividadeId']])
    ocor_ativ_qtd = len(ocor_ativ_id_l) 

    # verifica se há multiplas solicitações de nova atividade com mesmo título não analisadas para o mesmo plano
    ocor_nova_id_l = []
    if solicitacao.tipo[18:22] == 'Nova':
        multi_nova = db.session.query(Pactos_de_Trabalho_Solic)\
                               .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == pacto_id,
                                        Pactos_de_Trabalho_Solic.tipoSolicitacaoId == 601,
                                        Pactos_de_Trabalho_Solic.analisado == False)\
                               .all()
        for solic in multi_nova:
            ocor_nova_dados = ast.literal_eval(str(solic.dadosSolicitacao).replace('null','None').replace('true','True').replace('false','False'))
            if ocor_nova_dados['itemCatalogo'] == dados_solic['itemCatalogo']:
                ocor_nova_id_l.append(solic.pactoTrabalhoSolicitacaoId)
    ocor_nova_qtd = len(ocor_nova_id_l) 

    # valores padrão da aprovação automática
    aprovado = 1
    observacoes = 'Solicitação da chefia da unidade é aprovada automaticamente.'

    # registra a, ou as, aprovações para cada solicitação
    if solicitacao.tipo[18:25] == 'Excluir': 

        for id in ocor_ativ_id_l:

            analisado = db.session.query(Pactos_de_Trabalho_Solic).filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == id[0]).first()

            analisado.analisado           = True
            analisado.dataAnalise         = hoje
            analisado.analista            = analista.pessoaId
            analisado.aprovado            = aprovado
            analisado.observacoesAnalista = observacoes

            db.session.commit()

    elif solicitacao.tipo[18:22] == 'Nova': 

        for id in ocor_nova_id_l:

            analisado = db.session.query(Pactos_de_Trabalho_Solic).filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == id).first()

            analisado.analisado           = True
            analisado.dataAnalise         = hoje
            analisado.analista            = analista.pessoaId
            analisado.aprovado            = aprovado
            analisado.observacoesAnalista = observacoes

            db.session.commit()  

    else:
            analisado = db.session.query(Pactos_de_Trabalho_Solic).filter(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId == solic_id).first()

            analisado.analisado           = True
            analisado.dataAnalise         = hoje
            analisado.analista            = analista.pessoaId
            analisado.aprovado            = aprovado
            analisado.observacoesAnalista = observacoes   

            db.session.commit()              
 
    # o que fazer com os pactos a depender do tipo de solicitação após a sua aprovação
    if solicitacao.tipo[18:22] == 'Nova':

        for id in ocor_nova_id_l: 

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
                                                      tempoHomologado          = None,
                                                      nota                     = None,
                                                      justificativa            = None,
                                                      consideracoesConclusao   = None,
                                                      modalidadeExecucaoId     = modalidade,
                                                      responsavelAvaliacao     = None,
                                                      dataAvaliacao            = None)                 

            db.session.add(nova_ativ)
            db.session.commit()                      

            registra_log_unid(current_user.pessoaId,'Atividade ' + nova_ativ.pactoTrabalhoAtividadeId + ' inserida no plano ' + pacto_id + '.')

        flash(str(ocor_nova_qtd)+' nova(s) atividade(s) registrada(s)!','sucesso')

    elif solicitacao.tipo[18:24] == 'Altera':    

        pacto = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

        # calcula a quantidade de dias úteis entre as datas de início e fim do pacto
        # pega feriados do DBSISGP, acrescentando os fixos para os anos de início de de fim da demanda (pacto)
        feriados = pega_feriados(solicitacao.ufId)

        if np.is_busday(pacto.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados):
            n = 1
        else:
            n = 0
        qtd_dias_uteis = n + np.busday_count(pacto.dataInicio,pacto.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados)

        # altera a data fim do pacto e recalcula o tempo total disponível
        pacto.dataFim = dados_solic['dataFim']
        pacto.tempoTotalDisponivel = int(pacto.cargaHorariaDiaria * qtd_dias_uteis)

        db.session.commit()

        registra_log_unid(current_user.pessoaId,'Plano ' + pacto_id + ' teve sua data final alterada.')

        flash('Data fim do plano foi alterada!','sucesso')

    elif solicitacao.tipo[18:23] == 'Prazo':    

        # altera o tempo previsto por item e o tempo homologado, se for o caso, da atividade para o valor que a pessoa informou como executado
        ativ = db.session.query(Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                                Pactos_de_Trabalho_Atividades.tempoRealizado,
                                Pactos_de_Trabalho_Atividades.tempoHomologado)\
                            .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==dados_solic['pactoTrabalhoAtividadeId'])\
                            .first() 

        ativ.tempoPrevistoPorItem = ativ.tempoRelizado

        if ativ.tempoHomologado:
            ativ.tempoHomologado = ativ.tempoRealizado     

        db.session.commit() 

        registra_log_unid(current_user.pessoaId,'Atividade  '+ dados_solic['pactoTrabalhoAtividadeId'] +' com estouro de prazo aprovado.')
            
        flash('Estouro de prazo aprovado!','sucesso') 

    elif solicitacao.tipo[18:25] == 'Excluir': 

        for id in ocor_ativ_id_l:

            ativ_pacto_id = id[1].upper()

            # deleta eventual relação da atividade do pacto com objetos    
            obj = db.session.query(Objeto_Atividade_Pacto).filter(Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == ativ_pacto_id).delete()
            db.session.commit()

            # deleta relacionamentos das atividades com assuntos
            assunto_ativ_exclu = db.session.query(Atividade_Pacto_Assunto).filter(Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId == ativ_pacto_id).delete()
            db.session.commit()

            # deleta atividade no pacto
            ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()

            if ativ == None:
                abort(404)

            db.session.delete(ativ)
            db.session.commit()

            registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi retirada do plano de trabalho mediante aprovação.')
        
        flash(str(ocor_ativ_qtd)+' atividade(s) retirada(s) do plano de trabalho!','sucesso') 
           
    registra_log_unid(current_user.pessoaId,'Solicitação, ou solicitações, registradas pela chefia foram analisadas automaticamente.')

    flash('Alteração realizada!','sucesso')

    return redirect(url_for('demandas.demanda',pacto_id=pacto_id))


# vendo todas as demandas de um usuário
@demandas.route('/<lista>/<int:pessoa_id>/list_demandas_usu')
@login_required
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
    email = current_user.pesEmail

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
                        .join(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
                        .first()
    
    if lista == 'Todas':
        lista = '%'

    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

    #subquery que conta atividades em cada plano de trabalho (pacto)
    ativs = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoId,
                             label('qtd_ativs',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)))\
                      .group_by(Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                      .subquery()
    
    #subquery que conta atividades com nota em cada plano de trabalho (pacto)
    ativs_com_nota = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoId,
                                      label('qtd_com_nota',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)))\
                               .filter(Pactos_de_Trabalho_Atividades.nota != None)\
                               .group_by(Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                               .subquery()                     

    if lista == 'Em execução':

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
                            label('forma',catdom.descricao),
                            ativs.c.qtd_ativs,
                            ativs_com_nota.c.qtd_com_nota)\
                    .filter(Pactos_de_Trabalho.pessoaId == pes.pessoaId,
                            Pactos_de_Trabalho.situacaoId == 405)\
                    .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                    .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                    .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                    .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                    .outerjoin(ativs_com_nota, ativs_com_nota.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                    .outerjoin(ativs, ativs.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                    .order_by(Pactos_de_Trabalho.situacaoId,Pactos_de_Trabalho.dataInicio.desc())\
                    .all()

        demandas_count = len(demandas)

    elif lista != '%':

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
                                    label('forma',catdom.descricao),
                                    ativs.c.qtd_ativs,
                                    ativs_com_nota.c.qtd_com_nota)\
                            .filter(Pactos_de_Trabalho.pessoaId == pes.pessoaId,
                                    Pactos_de_Trabalho.formaExecucaoId == lista[0],
                                    Pactos_de_Trabalho.situacaoId == lista[1])\
                            .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                            .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                            .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                            .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                            .outerjoin(ativs_com_nota, ativs_com_nota.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .outerjoin(ativs, ativs.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .order_by(Pactos_de_Trabalho.situacaoId,Pactos_de_Trabalho.dataInicio.desc())\
                            .all()

        demandas_count = len(demandas)
    
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
                                label('forma',catdom.descricao),
                                ativs.c.qtd_ativs,
                                ativs_com_nota.c.qtd_com_nota)\
                            .filter(Pactos_de_Trabalho.pessoaId == pes.pessoaId)\
                            .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                            .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                            .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                            .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                            .outerjoin(ativs_com_nota, ativs_com_nota.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .outerjoin(ativs, ativs.c.pactoTrabalhoId == Pactos_de_Trabalho.pactoTrabalhoId)\
                            .order_by(Pactos_de_Trabalho.situacaoId,Pactos_de_Trabalho.dataInicio.desc())\
                            .all()

        demandas_count = len(demandas)                        

    return render_template ('demandas_pessoa.html', lista=lista, 
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
    email = current_user.pesEmail

    # registro a ser alterado
    ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()              

    # pega titulo da atividade
    tit = db.session.query(Atividades.titulo)\
                    .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.itemCatalogoId == Atividades.itemCatalogoId)\
                    .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id)\
                    .first()

    # pega datas do pacto (plano de trabaho)
    pacto_datas = db.session.query(Pactos_de_Trabalho.dataInicio, Pactos_de_Trabalho.dataFim).filter(Pactos_de_Trabalho.pactoTrabalhoId==pacto_id).first()

    if ativ.dataInicio:
        ativ_ja_iniciada = True
    else:
        ativ_ja_iniciada = False

    form = InciaConcluiAtivForm()
    
    if form.validate_on_submit():

        if acao == 'i':
            ativ.descricao = form.descricao.data
            ativ.situacaoId = 502
            if form.data_ini.data < pacto_datas.dataInicio or form.data_ini.data > pacto_datas.dataFim:
                flash('A data de início deve estar compreendida no período de execução do plano de trabalho.','erro')
                return render_template('inicia_conclui_atividade.html', form=form, acao=acao, sit = ativ.situacaoId, tit=tit)
            else:
                ativ.dataInicio = form.data_ini.data
            ativ.consideracoesConclusao = form.consi_conclu.data

            db.session.commit()
            
        elif acao == 'f' or acao == 'c':
            ativ.descricao  = form.descricao.data
            ativ.situacaoId = 503
            if form.data_ini.data < pacto_datas.dataInicio or form.data_ini.data > pacto_datas.dataFim:
                flash('A data de início deve estar compreendida no período de execução do plano de trabalho.','erro')
                return render_template('inicia_conclui_atividade.html', form=form, acao=acao, sit = ativ.situacaoId, tit=tit)
            else:
                ativ.dataInicio = form.data_ini.data
            if form.data_fim.data > pacto_datas.dataFim or form.data_fim.data < pacto_datas.dataInicio:
                flash('A data de término deve estar compreendida no período de execução do plano de trabalho.','erro')
                return render_template('inicia_conclui_atividade.html', form=form, acao=acao, sit = ativ.situacaoId, tit=tit)
            else:    
                ativ.dataFim  = form.data_fim.data
            ativ.tempoRealizado = form.tempo_realizado.data.replace(',','.')
            ativ.consideracoesConclusao = form.consi_conclu.data

            db.session.commit()

            # calcular %execução e relação previsto/executado
            # pega as atividades no plano do cidadão
            itens_plano = db.session.query(label('tam_grupo',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)),
                                           label('tempo_prev_tot',func.sum((Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem))),
                                           label('tempo_realiz',func.sum((Pactos_de_Trabalho_Atividades.tempoRealizado))),
                                           label('tempo_prev_conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)], else_=0))),
                                           label('conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, 1)], else_=0))),
                                           label('exec',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 502, 1)], else_=0))))\
                                    .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                                    .first()                        

            if itens_plano.tempo_realiz == None:
                tempo_realiz = 0
            else:
                tempo_realiz = itens_plano.tempo_realiz   

            if itens_plano.tempo_prev_conclu == None:
                tempo_prev_conclu = 0
            else:
                tempo_prev_conclu = itens_plano.tempo_prev_conclu                          

            # percentual de execução calculado pela relação tempo realizado / tempo previsto no plano (todas as atividades)
            percentual_tempo_realizado = round(100 * float(tempo_realiz) / float(itens_plano.tempo_prev_tot),2)

            # percentual de execução caculado pela relação quantidade de atividades concluidas / quantidade total de atividades no plano
            if itens_plano.conclu == None:
                itens_plano_conclu = 0
            else:
                itens_plano_conclu = itens_plano.conclu
            percentual_qtd_ativs_executado = round(100 * float(itens_plano_conclu) / float(itens_plano.tam_grupo),2)

            # relacaoPrevistoRealizado é o percentual calculado pela relação tempo realizado / tempo previsto das concluídas 
            if tempo_prev_conclu != 0:
                rel_prev_realiz = round(100 * float(tempo_prev_conclu) / float(tempo_realiz),2)
            else:
                rel_prev_realiz = 0

            # gravar em Pactos_de_Trabalho (plano)
            plano = db.session.query(Pactos_de_Trabalho)\
                              .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                              .first()

            plano.percentualExecucao = percentual_qtd_ativs_executado
            plano.relacaoPrevistoRealizado = rel_prev_realiz

            db.session.commit()

        if acao == 'i':
            registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi colocada em execução.')
            flash('Atividade colocada em execução!','sucesso')
        elif acao == 'f':
            if ativ_ja_iniciada:
                registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi concluída.')
                flash('Atividade concluída!','sucesso')
            else:
                registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi colocada em execução.')
                registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi concluída.')
                flash('Atividade iniciada e concluída!','sucesso')   
        elif acao == 'c':
            registra_log_unid(current_user.pessoaId,'Atividade concluída '+ ativ_pacto_id +' foi corrigida.')
            flash('Efetuada correção em atividade concluída!','sucesso')    

        # return redirect(url_for('demandas.demanda',pacto_id=pacto_id))
        return redirect(url_for('demandas.ativ_ocor', pacto_id=pacto_id,item_cat_id=ativ.itemCatalogoId))

    form.tempo_realizado.data = str(ativ.tempoPrevistoPorItem).replace('.',',')

    if acao == 'f':
        form.descricao.data    = ativ.descricao
        form.data_ini.data     = ativ.dataInicio
        form.consi_conclu.data = ativ.consideracoesConclusao

    if acao == 'c':
        form.descricao.data    = ativ.descricao
        form.data_ini.data     = ativ.dataInicio
        form.data_fim.data     = ativ.dataFim
        form.consi_conclu.data = ativ.consideracoesConclusao
    

    return render_template('inicia_conclui_atividade.html', form=form, acao=acao, sit = ativ.situacaoId, tit=tit)

#corrigindo dados de uma atividae em execução em um pacto (plano de trabalho)
@demandas.route('/corrige_ocor_atividade/<pacto_id>/<ativ_pacto_id>',methods=['GET','POST'])
@login_required
def corrige_ocor_atividade(pacto_id,ativ_pacto_id):
    """+---------------------------------------------------------------------------------+
       |Corrige dados de uma ocorrência no plano de trabalho.                            |
       |                                                                                 |
       |Recebe o ID da atividade no pacto e ID da atividade como parâmetros.             |
       +---------------------------------------------------------------------------------+
    """

    acao = 'i'

    # registro a ser alterado
    ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()              

    # pega titulo da atividade
    tit = db.session.query(Atividades.titulo)\
                    .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.itemCatalogoId == Atividades.itemCatalogoId)\
                    .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id)\
                    .first()

    # pega datas do pacto (plano de trabaho)
    pacto_datas = db.session.query(Pactos_de_Trabalho.dataInicio, Pactos_de_Trabalho.dataFim).filter(Pactos_de_Trabalho.pactoTrabalhoId==pacto_id).first()                

    form = InciaConcluiAtivForm()
    
    if form.validate_on_submit():

        ativ.descricao = form.descricao.data
        ativ.situacaoId = 502
        if form.data_ini.data < pacto_datas.dataInicio:
            flash('A data de início deve ser maior ou igual a data de início do plano de trabalho','erro')
            return render_template('inicia_conclui_atividade.html', form=form, acao=acao, sit = ativ.situacaoId, tit=tit)
        else:
            ativ.dataInicio = form.data_ini.data
        ativ.consideracoesConclusao = form.consi_conclu.data

        db.session.commit()
            
        registra_log_unid(current_user.pessoaId,'Atividade em execução '+ ativ_pacto_id +' foi corrigida.')

        return redirect(url_for('demandas.ativ_ocor', pacto_id=pacto_id,item_cat_id=ativ.itemCatalogoId))

    form.descricao.data    = ativ.descricao
    form.data_ini.data     = ativ.dataInicio
    form.consi_conclu.data = ativ.consideracoesConclusao

    return render_template('inicia_conclui_atividade.html', form=form, acao=acao, sit = ativ.situacaoId, tit=tit)


#finalizando programadas em lote
@demandas.route('/finaliza_lote_atividade/<pacto_id>/<item_cat_id>',methods=['GET','POST'])
@login_required
def finaliza_lote_atividade(pacto_id,item_cat_id):
    """+---------------------------------------------------------------------------------+
       |Finaliza lote de atividades programadas em um pacto.                             |
       |                                                                                 |
       |Recebe o ID do pacto e ID da atividade no pacto como parâmetros.                 |
       +---------------------------------------------------------------------------------+
    """

    # pega inicio e final do plano (pacto no banco)
    plano = db.session.query(Pactos_de_Trabalho.dataInicio,
                             Pactos_de_Trabalho.dataFim)\
                      .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                      .first()

    # registro a ser alterado
    ativ = db.session.query(Pactos_de_Trabalho_Atividades)\
                     .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id,
                             Pactos_de_Trabalho_Atividades.itemCatalogoId == item_cat_id,
                             Pactos_de_Trabalho_Atividades.situacaoId == 501)\
                     .all()              

    for a in ativ:

        if a.consideracoesConclusao != None:
            consid = a.consideracoesConclusao + ' - '
        else:
            consid = ''
           
        a.situacaoId     = 503
        a.dataInicio     = plano.dataInicio
        a.dataFim        = plano.dataFim
        a.tempoRealizado = a.tempoPrevistoPorItem
        a.consideracoesConclusao = consid + 'Atividade concluída.'

        db.session.commit()

        # calcular %execução e relação previsto/executado pegando os tempos de todas as atividades no plano
        itens_plano = db.session.query(label('tam_grupo',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)),
                                       label('tempo_prev_tot',func.sum((Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem))),
                                       label('tempo_realiz',func.sum((Pactos_de_Trabalho_Atividades.tempoRealizado))),
                                       label('tempo_prev_conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)], else_=0))),
                                       label('conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, 1)], else_=0))),
                                       label('exec',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 502, 1)], else_=0))))\
                                .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                                .first()

        if itens_plano.tempo_realiz == None:
            tempo_realiz = 0
        else:
            tempo_realiz = itens_plano.tempo_realiz   

        if itens_plano.tempo_prev_conclu == None:
            tempo_prev_conclu = 0
        else:
            tempo_prev_conclu = itens_plano.tempo_prev_conclu                          

        # percentual de execução calculado pela relação tempo realizado / tempo previsto no plano (todas as atividades)
        percentual_tempo_realizado = round(100 * float(tempo_realiz) / float(itens_plano.tempo_prev_tot),2)

        # percentual de execução caculado pela relação quantidade de atividades concluidas / quantidade total de atividades no plano
        if itens_plano.conclu == None:
            itens_plano_conclu = 0
        else:
            itens_plano_conclu = itens_plano.conclu
        percentual_qtd_ativs_executado = round(100 * float(itens_plano_conclu) / float(itens_plano.tam_grupo),2)

        # relacaoPrevistoRealizado é o percentual calculado pela relação tempo realizado / tempo previsto das concluídas
        if tempo_prev_conclu != 0:
            rel_prev_realiz = round(100 * float(tempo_prev_conclu) / float(tempo_realiz),2)
        else:
            rel_prev_realiz = 0

        # gravar em Pactos_de_Trabalho (plano)
        plano = db.session.query(Pactos_de_Trabalho)\
                            .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                            .first()

        plano.percentualExecucao = percentual_qtd_ativs_executado
        plano.relacaoPrevistoRealizado = rel_prev_realiz

        db.session.commit()

    registra_log_unid(current_user.pessoaId,'Lote de programadas no pacto '+ pacto_id +' foi concluído.')
    flash('Lote de programadas concluído!','sucesso')

    return redirect(url_for('demandas.demanda',pacto_id=pacto_id))


#avaliando atividade
@demandas.route('/avalia_atividade/<pacto_id>/<acao>/<ativ_pacto_id>',methods=['GET','POST'])
@login_required
def avalia_atividade(pacto_id,ativ_pacto_id,acao):
    """+---------------------------------------------------------------------------------+
       |Avalia atividade concluida em um pacto de trabalho.                              |
       |                                                                                 |
       |Recebe o ID do pacto e ID da atividade no pacto como parâmetros.                 |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega id sisgp do usuário logado
    avaliador = db.session.query(Pessoas.pessoaId, Pessoas.pesNome).filter(Pessoas.pesEmail == email).first_or_404()

    ativ = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id).first()

    form = AvaliaAtivForm()

    if form.validate_on_submit():

        ativ.nota = form.nota.data
        ativ.responsavelAvaliacao = avaliador.pesNome
        ativ.dataAvaliacao = hoje
        if form.tempo_homologado.data == None or form.tempo_homologado.data == '':
            ativ.tempoHomologado = ativ.tempoRealizado
        else:
            ativ.tempoHomologado = str(form.tempo_homologado.data).replace(',','.')
        ativ.justificativa = form.justificativa.data
            
        db.session.commit()

        if acao == 'avaliar':

            registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi avaliada.')
            
            flash('Atividade avaliada!','sucesso')

        elif acao == 'reavaliar':

            registra_log_unid(current_user.pessoaId,'Atividade  '+ ativ_pacto_id +' foi reavaliada.')
            
            flash('Atividade reavaliada!','sucesso')

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    if acao == 'reavaliar':
        form.tempo_homologado.data = str(ativ.tempoHomologado).replace('.',',')
        form.nota.data = int(ativ.nota)
        form.justificativa.data = ativ.justificativa
    else:
        form.tempo_homologado.data = str(ativ.tempoRealizado).replace('.',',')        

    return render_template('avalia_atividade.html', form=form, avaliador = avaliador, tipo='unic', acao=acao)

#avaliando atividade
@demandas.route('/avalia_lote_atividade/<pacto_id>/<ativ_pacto_id>,<item_cat_id>',methods=['GET','POST'])
@login_required
def avalia_lote_atividade(pacto_id,ativ_pacto_id,item_cat_id):
    """+---------------------------------------------------------------------------------+
       |Avalia todas as ocorrências de uma atividade concluida em um pacto de trabalho.  |
       |                                                                                 |
       |Recebe o ID do pacto e ID da atividade no pacto como parâmetros.                 |
       +---------------------------------------------------------------------------------+
    """
    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega id sisgp do usuário logado
    avaliador = db.session.query(Pessoas.pessoaId, Pessoas.pesNome).filter(Pessoas.pesEmail == email).first_or_404()

    ativs = db.session.query(label('id',Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId),
                            label('situa',catdom.descricao),
                            Pactos_de_Trabalho_Atividades.nota,
                            Pactos_de_Trabalho_Atividades.tempoRealizado,
                            Pactos_de_Trabalho_Atividades.tempoHomologado,
                            Pactos_de_Trabalho_Atividades.justificativa)\
                        .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id,
                                Pactos_de_Trabalho_Atividades.itemCatalogoId == item_cat_id)\
                        .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                        .order_by(Pactos_de_Trabalho_Atividades.dataInicio.desc(),Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                        .all()

    form = AvaliaAtivForm()

    if form.validate_on_submit():

        for ativ in ativs:

            if ativ.situa == 'Concluída':

                ativ_av = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ.id).first()

                ativ_av.nota = form.nota.data
                ativ_av.responsavelAvaliacao = avaliador.pesNome
                ativ_av.dataAvaliacao = hoje
                if form.tempo_homologado.data == None or form.tempo_homologado.data == '':
                    ativ_av.tempoHomologado = ativ.tempoRealizado
                else:
                    ativ_av.tempoHomologado = str(form.tempo_homologado.data).replace(',','.')
                ativ_av.justificativa = form.justificativa.data
            
        db.session.commit()

        registra_log_unid(current_user.pessoaId,'Atividade (todas as ocorrências) '+ ativ_pacto_id +' foi avaliada.')
        
        flash('Toda as ocorrências da Atividade avaliadas!','sucesso')

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('avalia_atividade.html', form=form, avaliador = avaliador, tipo='lote', acao='avaliar')

#registrar assuntos
@demandas.route('/add_assunto/<pacto_id>/<ativ_pacto_id>',methods=['GET','POST'])
@login_required
def add_assunto(pacto_id,ativ_pacto_id):
    """+---------------------------------------------------------------------------------+
       |Registra assuntos para atividades de um pacto.                                   |
       |                                                                                 |
       |Recebe o ID do pacto e ID da atividade no pacto como parâmetros.                 |
       +---------------------------------------------------------------------------------+
    """

    # pega atividade individual e objeto associado
    ativ = db.session.query(Pactos_de_Trabalho_Atividades.itemCatalogoId,
                            Atividades.titulo)\
                         .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==ativ_pacto_id)\
                         .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                         .first()

    # resgata assuntos
    assuntos = db.session.query(Assuntos.chave,
                                Assuntos.valor,
                                Pactos_de_Trabalho_Atividades.dataInicio)\
                         .join(Atividade_Pacto_Assunto, Atividade_Pacto_Assunto.assuntoId == Assuntos.assuntoId)\
                         .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId)\
                         .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == ativ.itemCatalogoId,
                                 Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id)\
                         .order_by(Assuntos.chave.desc())\
                         .all()

    quantidade = len(assuntos)

    #resgata objetos
    objetos = db.session.query(Objetos.chave,
                                 Objetos.descricao)\
                                .join(Objeto_PG, Objeto_PG.objetoId==Objetos.objetoId)\
                                .join(Objeto_Atividade_Pacto,Objeto_Atividade_Pacto.planoTrabalhoObjetoId==Objeto_PG.planoTrabalhoObjetoId)\
                                .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId)\
                                .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == ativ.itemCatalogoId,
                                        Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == ativ_pacto_id)\
                                .all() 

    form = AddAssuntoForm()

    if form.validate_on_submit():

        assunto = Assuntos(assuntoId    = uuid.uuid4(),
                           assuntoPaiId = None,
                           valor        = form.valor.data,
                           chave        = str(date.today().strftime('%y%m%d'))+ str(form.valor.data)[0] + get_random_string(3),
                           ativo        = True)

        db.session.add(assunto)
        db.session.commit()

        assunto_ativ = Atividade_Pacto_Assunto(pactoTrabalhoAtividadeAssuntoId = uuid.uuid4(),
                                               pactoTrabalhoAtividadeId        = ativ_pacto_id,
                                               assuntoId                       = assunto.assuntoId)                 

        db.session.add(assunto_ativ)
        db.session.commit()                      

        registra_log_unid(current_user.pessoaId,'Assunto '+ assunto.assuntoId +' inserido no banco de dados.')

        flash('Assunto registrado!','sucesso')

        return redirect(url_for('demandas.ativ_ocor', pacto_id=pacto_id,item_cat_id=ativ.itemCatalogoId))

    return render_template('add_assunto.html', form=form, ativ_pacto_id = ativ_pacto_id,
                                                          ativ=ativ, 
                                                          assuntos=assuntos,
                                                          quantidade=quantidade,
                                                          objetos = objetos)

## lista assuntos associadas a uma atividade de um plano de trabalho
@demandas.route('/<item_cat_id>/<pacto_id>/lista_assuntos')
@login_required
def lista_assuntos(item_cat_id,pacto_id):
    """
    +---------------------------------------------------------------------------------------+
    |Lista os assuntos que foram registrados para uma atividade em um plano de trabalho.    |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    # nome da atividade
    ativ = db.session.query(Atividades.titulo).filter(Atividades.itemCatalogoId == item_cat_id).first()

    # resgata objetos atividade
    objetos = db.session.query(Pactos_de_Trabalho_Atividades.itemCatalogoId,
                               Objetos.chave,
                               Objetos.descricao,
                               label('qtd_ativs',func.count(Objetos.chave)))\
                        .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id,
                                Pactos_de_Trabalho_Atividades.itemCatalogoId == item_cat_id)\
                        .outerjoin(Objeto_Atividade_Pacto, Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                        .outerjoin(Objeto_PG, Objeto_PG.planoTrabalhoObjetoId == Objeto_Atividade_Pacto.planoTrabalhoObjetoId)\
                        .outerjoin(Objetos, Objetos.objetoId == Objeto_PG.objetoId)\
                        .group_by(Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                  Objetos.chave,
                                  Objetos.descricao)\
                        .all()

    qtd_objetos = len(objetos)                    

    # resgata assuntos
    
    assuntos = db.session.query(Assuntos.chave,Assuntos.valor,
                                Pactos_de_Trabalho_Atividades.dataInicio)\
                         .join(Atividade_Pacto_Assunto, Atividade_Pacto_Assunto.assuntoId == Assuntos.assuntoId)\
                         .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId)\
                         .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == item_cat_id,
                                 Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                         .order_by(Assuntos.chave.desc())\
                         .all()

    quantidade = len(assuntos)


    return render_template('lista_assuntos.html', assuntos=assuntos,
                                                  quantidade=quantidade,
                                                  objetos=objetos,
                                                  qtd_objetos=qtd_objetos,
                                                  ativ=ativ)

# criando um plano de trabalho (pacto)
@demandas.route('/<pg_id>/cria_plano', methods=['GET','POST'])
@login_required
def cria_plano(pg_id):
    """
    +---------------------------------------------------------------------------------------+
    |Criando um plano de trabalho (pacto de trabalho no DBSISGP).                           |    
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    # verifica se há condição em variável de ambiente
    condic = os.environ.get('CONDIC')

    hoje = datetime.now()

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == current_user.pesEmail).first()

    #verifica se o usuário logado é chefe
    chefia = db.session.query(Tipo_Func_Pessoa.tfnIndicadorChefia).filter(Tipo_Func_Pessoa.tipoFuncaoId==usuario.tipoFuncaoId).first()
    if chefia and chefia.tfnIndicadorChefia:
        chefe = True
    else:
        chefe = False

    #pega dados da pessoa do usuário logado ou da pessoa informada
    if not chefe:
        pes = db.session.query(Pessoas.unidadeId, 
                               Pessoas.pessoaId,
                               Pessoas.pesNome,
                               Pessoas.cargaHoraria,
                               Unidades.ufId)\
                        .join(Unidades, Unidades.unidadeId==Pessoas.unidadeId)\
                        .filter(Pessoas.pessoaId == usuario.pessoaId)\
                        .first()
    else:
        pes = db.session.query(Pessoas.pessoaId,
                               Pessoas.pesNome)\
                        .filter(Pessoas.unidadeId == usuario.unidadeId, Pessoas.pessoaId != usuario.pessoaId)\
                        .all()                    

    #pega PG escolhido pelo usuário
    pg = db.session.query(Planos_de_Trabalho.planoTrabalhoId,
                          Planos_de_Trabalho.dataInicio,
                          Planos_de_Trabalho.dataFim,
                          Planos_de_Trabalho.tempoComparecimento,
                          Planos_de_Trabalho.termoAceite,
                          Unidades.undSigla,
                          Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId,
                          Planos_de_Trabalho_Ativs.modalidadeExecucaoId)\
                   .join(Unidades, Unidades.unidadeId == Planos_de_Trabalho.unidadeId)\
                   .outerjoin(Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs.planoTrabalhoId==Planos_de_Trabalho.planoTrabalhoId)\
                   .filter(Planos_de_Trabalho.planoTrabalhoId == pg_id)\
                   .first()

    #pega atividades do PG escolhido pelo usuário
    ativs_pg = db.session.query(Atividades.itemCatalogoId,
                                Atividades.titulo,
                                Atividades.tempoRemoto,
                                Atividades.tempoPresencial)\
                           .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.itemCatalogoId == Atividades.itemCatalogoId)\
                           .join(Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId)\
                           .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId == pg_id)\
                           .order_by(Atividades.titulo)\
                           .all() 
    
    # monta opções para atividades no formulário
    ativs = [{'ativ_id':a.itemCatalogoId,'tempo_rem':a.tempoRemoto,'tempo_pre':a.tempoPresencial,'titulo':a.titulo,'modalidade':'','quantidade':0} for a in ativs_pg]                      
    dados = {'data_ini':None, 'data_fim':None, 'ativs':ativs}

    # pega modalidade de execução
    mod = db.session.query(catdom.descricao).filter(catdom.catalogoDominioId == pg.modalidadeExecucaoId).first()

    # este formulário tem outro formulário dentro dele, AtivForm, que monta as opções de atividades para escolha do usuário
    form = CriaPlanoForm(data=dados)

    # choices do selectfield pessoa a ser usado se o usuário for algum tipo de chefe
    if chefe:
        lista_pessoas = [(p.pessoaId, p.pesNome) for p in pes]
        lista_pessoas.insert(0,(str(usuario.pessoaId),usuario.pesNome))
        form.pessoa.choices = lista_pessoas

    # limita opções de forma de execução de atividades conforme modalidade do PG do do plano
    for field in form.ativs:
        if int(pg.modalidadeExecucaoId) == 101:
            field.modalidade.choices = [(101, 'Presencial')] 
        elif int(pg.modalidadeExecucaoId) == 102:
            field.modalidade.choices = [(103, 'Remoto'), (101, 'Presencial')]
        elif int(pg.modalidadeExecucaoId) == 103:
            field.modalidade.choices = [(103, 'Remoto')]    

    if form.validate_on_submit(): 

        if chefe:
            pes_sel = db.session.query(Pessoas.pessoaId,
                                       Pessoas.pesNome,
                                       Pessoas.cargaHoraria,
                                       Unidades.ufId)\
                                .join(Unidades, Unidades.unidadeId==Pessoas.unidadeId)\
                                .filter(Pessoas.pessoaId == form.pessoa.data)\
                                .first()
            # verifica se o sistema tem restrição para chefe
            if condic == 'chefe_nao_pode_remoto' and pes_sel.pessoaId == usuario.pessoaId and int(pg.modalidadeExecucaoId) == 103:
                flash ('Você possui função de chefia, desta forma não pode realizar um plano com teletrabalho integral!', 'erro')
                return render_template('add_plano.html', form=form, ativs_pg=ativs_pg, pg=pg, mod=mod, chefe=chefe, tipo='inc')

        else:
            pes_sel = pes
        
        #calcula tempo total disponível, pegando feriados e contando dias úteis no período do plano
        # pega feriados do DBSISGP, acrescentando os fixos para os anos de início de de fim da demanda (pacto)
        feriados = pega_feriados(pes_sel.ufId)

        if np.is_busday(form.data_fim.data,weekmask=[1,1,1,1,1,0,0],holidays=feriados):
            n = 1
        else:
            n = 0
        qtd_dias_uteis = n + np.busday_count(form.data_ini.data,form.data_fim.data,weekmask=[1,1,1,1,1,0,0],holidays=feriados)
        ttd = int(pes_sel.cargaHoraria * qtd_dias_uteis)

        #cria registro em Pactos_de_Trabalho já na situação "Enviado para aceite"
        plano = Pactos_de_Trabalho(pactoTrabalhoId          = uuid.uuid4(),
                                   planoTrabalhoId          = pg_id,
                                   unidadeId                = usuario.unidadeId,
                                   pessoaId                 = pes_sel.pessoaId,
                                   formaExecucaoId          = pg.modalidadeExecucaoId,
                                   situacaoId               = 402,
                                   dataInicio               = form.data_ini.data,
                                   dataFim                  = form.data_fim.data,
                                   tempoComparecimento      = pg.tempoComparecimento,
                                   cargaHorariaDiaria       = pes_sel.cargaHoraria,
                                   percentualExecucao       = None,
                                   relacaoPrevistoRealizado = None,
                                   avaliacaoId              = None,
                                   tempoTotalDisponivel     = ttd,
                                   termoAceite              = pg.termoAceite) 

        db.session.add(plano) 

        # cria registro em Plactos_de_Trabalho_Hist
        hist = Pactos_de_Trabalho_Hist(pactoTrabalhoHistoricoId = uuid.uuid4(),
                                       pactoTrabalhoId     = plano.pactoTrabalhoId,
                                       situacaoId          = plano.situacaoId,
                                       observacoes         = 'Criado de forma direta',
                                       responsavelOperacao = usuario.pessoaId,
                                       dataOperacao        = hoje)   

        db.session.add(hist)

        #cria registros em Pactos_de_Trabalho_Atividades
        tempo_plano = 0
        qtd_ativs = 0

        for field in form.ativs:
            if field.quantidade.data > 0:
                for a in range(1,field.quantidade.data + 1):
                    qtd_ativs += 1
                    if field.modalidade.data == 101:
                        tempo_prev = float(field.tempo_pre.data.replace(',','.'))
                    else:
                        tempo_prev = float(field.tempo_rem.data.replace(',','.'))
                    tempo_plano += tempo_prev
    
                    plano_ativs = Pactos_de_Trabalho_Atividades (pactoTrabalhoAtividadeId = uuid.uuid4(),
                                                                pactoTrabalhoId          = plano.pactoTrabalhoId,
                                                                itemCatalogoId           = field.ativ_id.data,
                                                                situacaoId               = 501,
                                                                quantidade               = 1,
                                                                tempoPrevistoPorItem     = tempo_prev,
                                                                tempoPrevistoTotal       = tempo_prev,
                                                                dataInicio               = None,
                                                                dataFim                  = None,
                                                                tempoRealizado           = None,
                                                                descricao                = None,
                                                                tempoHomologado          = None,
                                                                nota                     = None,
                                                                justificativa            = None,
                                                                consideracoesConclusao   = None,
                                                                modalidadeExecucaoId     = int(field.modalidade.data),
                                                                responsavelAvaliacao     = None,
                                                                dataAvaliacao            = None)

                    db.session.add(plano_ativs)

        if qtd_ativs == 0:
            flash('Plano não foi criado, pois nenhuma atividade foi selecionada!','erro')
            db.session.close()
        else:    
            if float(ttd) > tempo_plano:
                flash('ATENÇÃO! Plano criado, contudo as atividades não ocupam a totalidade do tempo disponível no período do plano!\
                    (Tempo disponível: '+ str(ttd) +'h , Soma dos tempos das atividades: '+ str(tempo_plano).replace('.',',') +' h)','perigo')
            elif float(ttd) < tempo_plano:
                flash('ATENÇÃO! Plano criado, contudo as atividades demandam mais tempo do que o disponível no período do plano!\
                    (Tempo disponível: '+ str(ttd) +'h , Soma dos tempos das atividades: '+ str(tempo_plano).replace('.',',') +' h)','perigo')
            else:
                flash('Plano criado e aguardando aprovação!','sucesso')
            
            db.session.commit()
            registra_log_unid(current_user.pessoaId,'Plano de Trabalho criado.')

            ## para efeitos de consistência com o SISGP, registra dados nas classes Atividade_Candidato e Atividade_Candidato_Hist
            if pg.planoTrabalhoAtividadeId:

                ativ_cand = Atividade_Candidato (planoTrabalhoAtividadeCandidatoId = uuid.uuid4(),
                                                planoTrabalhoAtividadeId          = pg.planoTrabalhoAtividadeId,
                                                pessoaId                          = pes_sel.pessoaId,
                                                situacaoId                        = 804,
                                                termoAceite                       = pg.termoAceite)
                db.session.add(ativ_cand)     

                ativ_cand_hist = Atividade_Candidato_Hist (planoTrabalhoAtividadeCandidatoHistoricoId = uuid.uuid4(),
                                                           planoTrabalhoAtividadeCandidatoId = ativ_cand.planoTrabalhoAtividadeCandidatoId,
                                                           situacaoId                        = ativ_cand.situacaoId,
                                                           data                              = hist.dataOperacao,
                                                           descricao                         = None,
                                                           responsavelOperacao               = pes_sel.pessoaId)
                db.session.add(ativ_cand_hist)  

                db.session.commit()                           

            return redirect(url_for('demandas.list_demandas', lista = 'Enviado para aceite', coord = '*'))


    return render_template('add_plano.html', form=form, ativs_pg=ativs_pg, pg=pg, mod=mod, chefe=chefe, tipo='inc')                                                                       

# alterando um plano de trabalho (pacto)
@demandas.route('/<pg_id>/<pacto_id>/altera_plano', methods=['GET','POST'])
@login_required
def altera_plano(pg_id,pacto_id):
    """
    +---------------------------------------------------------------------------------------+
    |Altera um plano de trabalho (pacto de trabalho no DBSISGP).                            |    
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    # verifica se há condição em variável de ambiente
    condic = os.environ.get('CONDIC')

    hoje = datetime.now()

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == current_user.pesEmail).first()

    #verifica se o usuário logado é chefe
    chefia = db.session.query(Tipo_Func_Pessoa.tfnIndicadorChefia).filter(Tipo_Func_Pessoa.tipoFuncaoId==usuario.tipoFuncaoId).first()
    if chefia and chefia.tfnIndicadorChefia:
        chefe = True
    else:
        chefe = False

    #pega dados da pessoa do usuário logado ou da pessoa informada
    if not chefe:
        pes = db.session.query(Pessoas.unidadeId, 
                               Pessoas.pessoaId,
                               Pessoas.pesNome,
                               Pessoas.cargaHoraria,
                               Unidades.ufId)\
                        .join(Unidades, Unidades.unidadeId==Pessoas.unidadeId)\
                        .filter(Pessoas.pessoaId == usuario.pessoaId)\
                        .first()
    else:
        pes = db.session.query(Pessoas.pessoaId,
                               Pessoas.pesNome)\
                        .filter(Pessoas.unidadeId == usuario.unidadeId, Pessoas.pessoaId != usuario.pessoaId)\
                        .all()                    

    #pega PG do plano 
    pg = db.session.query(Planos_de_Trabalho.planoTrabalhoId,
                          Planos_de_Trabalho.dataInicio,
                          Planos_de_Trabalho.dataFim,
                          Planos_de_Trabalho.tempoComparecimento,
                          Planos_de_Trabalho.termoAceite,
                          Unidades.undSigla,
                          Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId,
                          Planos_de_Trabalho_Ativs.modalidadeExecucaoId)\
                   .join(Unidades, Unidades.unidadeId == Planos_de_Trabalho.unidadeId)\
                   .outerjoin(Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs.planoTrabalhoId==Planos_de_Trabalho.planoTrabalhoId)\
                   .filter(Planos_de_Trabalho.planoTrabalhoId == pg_id)\
                   .first()

    #pega atividades do PG escolhido pelo usuário
    ativs_pg = db.session.query(Atividades.itemCatalogoId,
                                Atividades.titulo,
                                Atividades.tempoRemoto,
                                Atividades.tempoPresencial)\
                           .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.itemCatalogoId == Atividades.itemCatalogoId)\
                           .join(Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId)\
                           .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId == pg_id)\
                           .order_by(Atividades.titulo)\
                           .all() 
    
    # pega plano a ser alterado
    plano = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId==pacto_id).first()

    # monta opções para atividades no formulário
    ativs = [{'ativ_id':a.itemCatalogoId,'tempo_rem':a.tempoRemoto,'tempo_pre':a.tempoPresencial,'titulo':a.titulo,'modalidade':'','quantidade':0} for a in ativs_pg]                      
    dados = {'data_ini':None, 'data_fim':None, 'ativs':ativs}

    # pega modalidade de execução
    mod = db.session.query(catdom.descricao).filter(catdom.catalogoDominioId == pg.modalidadeExecucaoId).first()

    # este formulário tem outro formulário dentro dele, AtivForm, que monta as opções de atividades para escolha do usuário
    form = CriaPlanoForm(data=dados)

    # choices do selectfield pessoa a ser usado se o usuário for algum tipo de chefe
    if chefe:
        lista_pessoas = [(p.pessoaId, p.pesNome) for p in pes]
        lista_pessoas.insert(0,(str(usuario.pessoaId),usuario.pesNome))
        form.pessoa.choices = lista_pessoas

    # limita opções de forma de execução de atividades conforme modalidade do PG do do plano
    for field in form.ativs:
        if int(pg.modalidadeExecucaoId) == 101:
            field.modalidade.choices = [(101, 'Presencial')] 
        elif int(pg.modalidadeExecucaoId) == 102:
            field.modalidade.choices = [(103, 'Remoto'), (101, 'Presencial')]
        elif int(pg.modalidadeExecucaoId) == 103:
            field.modalidade.choices = [(103, 'Remoto')]

    if form.validate_on_submit(): 

        if chefe:
            pes_sel = db.session.query(Pessoas.pessoaId,
                                       Pessoas.pesNome,
                                       Pessoas.cargaHoraria,
                                       Unidades.ufId)\
                                .join(Unidades, Unidades.unidadeId==Pessoas.unidadeId)\
                                .filter(Pessoas.pessoaId == form.pessoa.data)\
                                .first()
            # verifica se o sistema tem restrição para chefe
            if condic == 'chefe_nao_pode_remoto' and pes_sel.pessoaId == usuario.pessoaId and int(pg.modalidadeExecucaoId) == 103:
                flash ('Você possui função de chefia, desta forma não pode realizar um plano com teletrabalho integral!', 'erro')
                return render_template('add_plano.html', form=form, ativs_pg=ativs_pg, pg=pg, mod=mod, chefe=chefe, tipo='alt')

        else:
            pes_sel = pes
        
        #calcula tempo total disponível, pegando feriados e contando dias úteis no período do plano
        # pega feriados do DBSISGP, acrescentando os fixos para os anos de início de de fim da demanda (pacto)
        feriados = pega_feriados(pes_sel.ufId)

        if np.is_busday(form.data_fim.data,weekmask=[1,1,1,1,1,0,0],holidays=feriados):
            n = 1
        else:
            n = 0
        qtd_dias_uteis = n + np.busday_count(form.data_ini.data,form.data_fim.data,weekmask=[1,1,1,1,1,0,0],holidays=feriados)
        ttd = int(pes_sel.cargaHoraria * qtd_dias_uteis)

        #altera registro do plano (pacto) selecionado, colocando-o na situação "Enviado para aceite"

        plano.formaExecucaoId = pg.modalidadeExecucaoId
        plano.situacaoId      = 402
        plano.dataInicio      = form.data_ini.data
        plano.dataFim         = form.data_fim.data

        # cria registro em Plactos_de_Trabalho_Hist
        hist = Pactos_de_Trabalho_Hist(pactoTrabalhoHistoricoId = uuid.uuid4(),
                                       pactoTrabalhoId     = plano.pactoTrabalhoId,
                                       situacaoId          = plano.situacaoId,
                                       observacoes         = 'Alterado de forma direta',
                                       responsavelOperacao = usuario.pessoaId,
                                       dataOperacao        = hoje)   

        db.session.add(hist)

        # deleta registros de atividades no plano (pacto) para que novos sejam inseridos
        plano_ativs_del = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId==pacto_id).delete()

        #cria registros em Pactos_de_Trabalho_Atividades
        tempo_plano = 0
        qtd_ativs = 0

        for field in form.ativs:
            if field.quantidade.data > 0:
                for a in range(1,field.quantidade.data + 1):
                    qtd_ativs += 1
                    if field.modalidade.data == 101:
                        tempo_prev = float(field.tempo_pre.data.replace(',','.'))
                    else:
                        tempo_prev = float(field.tempo_rem.data.replace(',','.'))
                    tempo_plano += tempo_prev
    
                    plano_ativs = Pactos_de_Trabalho_Atividades (pactoTrabalhoAtividadeId = uuid.uuid4(),
                                                                 pactoTrabalhoId          = plano.pactoTrabalhoId,
                                                                 itemCatalogoId           = field.ativ_id.data,
                                                                 situacaoId               = 501,
                                                                 quantidade               = 1,
                                                                 tempoPrevistoPorItem     = tempo_prev,
                                                                 tempoPrevistoTotal       = tempo_prev,
                                                                 dataInicio               = None,
                                                                 dataFim                  = None,
                                                                 tempoRealizado           = None,
                                                                 descricao                = None,
                                                                 tempoHomologado          = None,
                                                                 nota                     = None,
                                                                 justificativa            = None,
                                                                 consideracoesConclusao   = None,
                                                                 modalidadeExecucaoId     = int(field.modalidade.data),
                                                                 responsavelAvaliacao     = None,
                                                                 dataAvaliacao            = None)

                    db.session.add(plano_ativs)

        if qtd_ativs == 0:
                flash('Plano não foi alterado, pois nenhuma atividade foi selecionada!','erro')
                db.session.close()
        elif float(ttd) > tempo_plano:
            flash('Atividades não ocupam a totalidade do tempo disponível no plano!\
                 (Tempo disponíel: '+ str(ttd) +'h , Soma dos tempos das atividades: '+ str(tempo_plano).replace('.',',') +' h)','perigo')
            db.session.close()     
        elif float(ttd) < tempo_plano:
            flash('Atividades selecionadas demandam mais tempo do que o disponível no plano!\
                 (Tempo disponíel: '+ str(ttd) +'h , Soma dos tempos das atividades: '+ str(tempo_plano).replace('.',',') +' h)','erro')
            db.session.close()     
        else:
            
            flash('Plano alterado e aguardando aprovação!','sucesso')
            db.session.commit()
            registra_log_unid(current_user.pessoaId,'Plano de Trabalho '+pacto_id+' alterado.')

            return redirect(url_for('demandas.list_demandas', lista = 'Enviado para aceite', coord = '*'))
    
    # preenche tela com dados do plano a ser alterado

    # form.forma.data    = plano.formaExecucaoId
    form.data_ini.data = plano.dataInicio
    form.data_fim.data = plano.dataFim

    return render_template('add_plano.html', form=form, ativs_pg=ativs_pg, pg=pg, mod=mod, chefe=chefe, tipo='alt')                                                                       


#analisando um pacto encaminhado para aceite
@demandas.route('/analisa_plano/<pacto_id>',methods=['GET','POST'])
@login_required
def analisa_plano(pacto_id):
    """+---------------------------------------------------------------------------------+
       |Realiza a analise de um plano que foi enviado para aceite.                       |
       |                                                                                 |
       |Recebe o ID do plano como parâmetro.                                             |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega id sisgp do usuário logado
    analista = db.session.query(Pessoas.pessoaId, Pessoas.pesNome).filter(Pessoas.pesEmail == email).first_or_404()

    #pega o plano
    plano = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

    #pega dono do plano
    dono = db.session.query(Pessoas).filter(Pessoas.pessoaId == plano.pessoaId).first()

    #atividades do plano
    ativs = db.session.query(label('tempo_prev_tot',func.sum(Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)),
                             label('qtd_ativs',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)))\
                      .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                      .first()

    form = AnalisaPlano()
 
    if form.validate_on_submit():

        # cria registro em Plactos_de_Trabalho_Hist
        hist = Pactos_de_Trabalho_Hist(pactoTrabalhoHistoricoId = uuid.uuid4(),
                                       pactoTrabalhoId     = pacto_id,
                                       situacaoId          = form.parecer.data,
                                       observacoes         = form.obs.data,
                                       responsavelOperacao = analista.pessoaId,
                                       dataOperacao        = hoje)   
        db.session.add(hist)

        # altera situação do plano (pacto)
        plano.situacaoId = form.parecer.data

        db.session.commit()

        if plano.situacaoId == 404:

            flash('Plano de trabalho foi recusado!','erro')
            registra_log_unid(current_user.pessoaId,'Plano de Trabalho recusado.')
        
        if plano.situacaoId == 403:

            flash('Plano de trabalho foi aceito!','sucesso')
            registra_log_unid(current_user.pessoaId,'Plano de Trabalho aceito.')

        return redirect(url_for('demandas.list_demandas', lista = 'Enviado para aceite', coord = '*'))

    return render_template ('analisa_plano.html',form=form, plano=plano, analista=analista,dono=dono,ativs=ativs)


#iniciando um plano de trabalho (pacto) que foi aceito
@demandas.route('/inicia_plano/<pacto_id>',methods=['GET','POST'])
@login_required
def inicia_plano(pacto_id):
    """+---------------------------------------------------------------------------------+
       |Inicia a execução de um plano que foi enviado para aceite.                       |
       |                                                                                 |
       |Recebe o ID do plano como parâmetro.                                             |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega o plano
    plano = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

    #pega atividades do plano
    ativs = db.session.query(Pactos_de_Trabalho_Atividades).filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id).all()

    #pega dono do plano
    dono = db.session.query(Pessoas).filter(Pessoas.pessoaId == plano.pessoaId).first()

    if dono.pesEmail == email:

        # cria registro em Plactos_de_Trabalho_Hist
        hist = Pactos_de_Trabalho_Hist(pactoTrabalhoHistoricoId = uuid.uuid4(),
                                       pactoTrabalhoId     = pacto_id,
                                       situacaoId          = 405,
                                       observacoes         = 'Plano de Trabalho colocado em execução pelo próprio responsável.',
                                       responsavelOperacao = dono.pessoaId,
                                       dataOperacao        = hoje)   
        db.session.add(hist)

        # altera situação do plano (pacto)
        plano.situacaoId = 405

        db.session.commit()

        # realiza o desmembramento das atividades em ocorrências, caso necessário
        for a in ativs:
            if a.quantidade > 1:
                # desmenbra a atividade em quantidade-1 ocorrências
                for o in range(a.quantidade-1):
                    ocor = Pactos_de_Trabalho_Atividades (pactoTrabalhoAtividadeId = uuid.uuid4(),
                                                          pactoTrabalhoId          = pacto_id,
                                                          itemCatalogoId           = a.itemCatalogoId,
                                                          situacaoId               = 501,
                                                          quantidade               = 1,
                                                          tempoPrevistoPorItem     = a.tempoPrevistoPorItem,
                                                          tempoPrevistoTotal       = a.tempoPrevistoPorItem,
                                                          dataInicio               = None,
                                                          dataFim                  = None,
                                                          tempoRealizado           = None,
                                                          descricao                = None,
                                                          tempoHomologado          = None,
                                                          nota                     = None,
                                                          justificativa            = None,
                                                          consideracoesConclusao   = None,
                                                          modalidadeExecucaoId     = a.modalidadeExecucaoId,
                                                          responsavelAvaliacao     = None,
                                                          dataAvaliacao            = None)

                    db.session.add(ocor)
                # reduz a atividade original a uma ocorrência
                a.quantidade = 1
                a.tempoPrevistoTotal = a.tempoPrevistoPorItem
                db.session.commit()

        flash('Plano de trabalho colocado em execução!','sucesso')
        registra_log_unid(current_user.pessoaId,'Plano de Trabalho colocado em execução.')
    
    else:    
        flash('Este plano não é seu, não pode iniciá-lo!','erro')

    return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

#finalizando um plano de trabalho (pacto)
@demandas.route('/finaliza_plano/<pacto_id>',methods=['GET','POST'])
@login_required
def finaliza_plano(pacto_id):
    """+---------------------------------------------------------------------------------+
       |Finaliza um plano que está em execução.                                          |
       |                                                                                 |
       |Recebe o ID do plano como parâmetro.                                             |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #verifica se o usuário logado é chefe
    chefia = db.session.query(Tipo_Func_Pessoa.tfnIndicadorChefia).filter(Tipo_Func_Pessoa.tipoFuncaoId==current_user.tipoFuncaoId).first()
    if chefia and chefia.tfnIndicadorChefia:
        chefe = True
    else:
        chefe = False

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega o plano
    plano = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

    #pega dono do plano
    dono = db.session.query(Pessoas).filter(Pessoas.pessoaId == plano.pessoaId).first()

    if dono.pesEmail == email or chefe:

        # recalcular %execução e relação previsto/executado
        # pega as atividades no plano do cidadão
        itens_plano = db.session.query(label('tam_grupo',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)),
                                       label('tempo_prev_tot',func.sum((Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem))),
                                       label('tempo_realiz',func.sum((Pactos_de_Trabalho_Atividades.tempoRealizado))),
                                       label('tempo_prev_conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)], else_=0))),
                                       label('conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, 1)], else_=0))),
                                       label('exec',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 502, 1)], else_=0))))\
                                .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id)\
                                .first()

        if itens_plano.tempo_realiz == None:
            tempo_realiz = 0
        else:
            tempo_realiz = itens_plano.tempo_realiz   

        if itens_plano.tempo_prev_conclu == None:
            tempo_prev_conclu = 0
        else:
            tempo_prev_conclu = itens_plano.tempo_prev_conclu                          

        # percentual de execução calculado pela relação tempo realizado / tempo previsto no plano (todas as atividades)
        percentual_tempo_realizado = round(100 * float(tempo_realiz) / float(itens_plano.tempo_prev_tot),2)

        # percentual de execução caculado pela relação quantidade de atividades concluidas / quantidade total de atividades no plano
        if itens_plano.conclu == None:
            itens_plano_conclu = 0
        else:
            itens_plano_conclu = itens_plano.conclu
        percentual_qtd_ativs_executado = round(100 * float(itens_plano_conclu) / float(itens_plano.tam_grupo),2)

        # relacaoPrevistoRealizado é o percentual calculado pela relação tempo realizado / tempo previsto das concluídas
        if tempo_prev_conclu != 0:
            rel_prev_realiz = round(100 * float(tempo_prev_conclu) / float(tempo_realiz),2)
        else:
            rel_prev_realiz = 0

        # gravar em Pactos_de_Trabalho (plano)
        plano = db.session.query(Pactos_de_Trabalho)\
                            .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                            .first()

        plano.percentualExecucao = percentual_qtd_ativs_executado
        plano.relacaoPrevistoRealizado = rel_prev_realiz

        db.session.commit()

        # cria registro em Plactos_de_Trabalho_Hist
        hist = Pactos_de_Trabalho_Hist(pactoTrabalhoHistoricoId = uuid.uuid4(),
                                       pactoTrabalhoId     = pacto_id,
                                       situacaoId          = 406,
                                       observacoes         = 'Plano de Trabalho colocado como executado pelo próprio responsável.',
                                       responsavelOperacao = dono.pessoaId,
                                       dataOperacao        = hoje)   
        db.session.add(hist)

        plano.situacaoId = 406

        db.session.commit()

        flash('Plano de trabalho colocado como executado!','sucesso')
        registra_log_unid(current_user.pessoaId,'Plano de Trabalho colocado como executado.')
    
    else:    
        flash('Este plano não é seu, não pode finalizá-lo!','erro')

    return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

#finalizando um plano de trabalho (pacto)
@demandas.route('/reabre_plano/<pacto_id>',methods=['GET','POST'])
@login_required
def reabre_plano(pacto_id):
    """+---------------------------------------------------------------------------------+
       |Reabre um plano que está executado.                                              |
       |                                                                                 |
       |Recebe o ID do plano como parâmetro.                                             |
       +---------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega id do usuário logado
    usu = db.session.query(Pessoas.pessoaId).filter(Pessoas.pesEmail==email).first()

    #pega o plano e muda sua situação para Em execução
    plano = db.session.query(Pactos_de_Trabalho).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

    plano.situacaoId = 405

    db.session.commit()

    # cria registro em Plactos_de_Trabalho_Hist
    hist = Pactos_de_Trabalho_Hist(pactoTrabalhoHistoricoId = uuid.uuid4(),
                                    pactoTrabalhoId     = pacto_id,
                                    situacaoId          = 405,
                                    observacoes         = 'Plano de Trabalho reaberto.',
                                    responsavelOperacao = usu.pessoaId,
                                    dataOperacao        = hoje)   
    db.session.add(hist)

    flash('Plano de trabalho reaberto!','sucesso')
    registra_log_unid(current_user.pessoaId,'Plano de Trabalho reaberto.')
    
    return redirect(url_for('demandas.demanda',pacto_id=pacto_id))


# gera relatório de um plano de trabalho (pacto)
@demandas.route('/<pacto_id>/relatorio')
@login_required
def relatorio(pacto_id):

    """+--------------------------------------------------------------------------------------+
       |Gera relatório em pdf de uma atividade.                                               |
       |                                                                                      |
       +--------------------------------------------------------------------------------------+
    """

    class PDF_relatorio(FPDF):
        # cabeçalho
        def header(self):

            self.set_font('Arial', 'B', 10)
            self.set_text_color(127,127,127)
            self.cell(0, 10, 'Relatório de Plano de Trabalho', 1, 1,'C')
            pdf.ln(3)

        # Rodape da página
        def footer(self):
            # Posicionado a 1,5 cm do final da página
            self.set_y(-15)
            # Arial italic 8 cinza
            self.set_font('Arial', 'I', 8)
            self.set_text_color(127,127,127)
            # Numeração de página e data de geração
            self.cell(0, 10, 'Página ' + str(self.page_no()) + '/{nb}' +' - Gerado em '+date.today().strftime('%d/%m/%Y'), 0, 0, 'C')

    # pega o pacto informado
    catdom_1 = aliased(catdom)
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
                               catdom_1.descricao,
                               label('forma',catdom.descricao),
                               Planos_de_Trabalho.planoTrabalhoId,
                               UFs.ufId,
                               Pessoas.pesEmail,
                               Pactos_de_Trabalho.unidadeId,
                               Unidades.pessoaIdChefe,
                               Unidades.pessoaIdChefeSubstituto)\
                         .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                         .join(UFs, UFs.ufId == Unidades.ufId)\
                         .join(catdom_1, catdom_1.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                         .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Pactos_de_Trabalho.planoTrabalhoId)\
                         .first()

    # pega feriados do DBSISGP, acrescentando os fixos para os anos de início de de fim da demanda (pacto)
    feriados = pega_feriados(demanda.ufId)

    # calcula a quantidade de dias úteis entre as datas de início e fim do pacto - com feriados
    if np.is_busday(demanda.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados):
        n = 1
    else:
        n = 0
    qtd_dias_uteis = n + np.busday_count(demanda.dataInicio,demanda.dataFim,weekmask=[1,1,1,1,1,0,0],holidays=feriados)
    # calcula a quantidade de dias úteis entre as datas de início e fim do pacto - sem feriados
    if np.is_busday(demanda.dataFim,weekmask=[1,1,1,1,1,0,0]):
        n = 1
    else:
        n = 0
    qtd_dias_uteis_sf = n + np.busday_count(demanda.dataInicio,demanda.dataFim,weekmask=[1,1,1,1,1,0,0])

    # pega as atividades, agrupadas por itemCatalogoId, no plano do cidadão
    items_cat = db.session.query(label('seq',func.row_number().over(order_by=(Atividades.titulo))),
                                 Atividades.titulo,
                                 label('tam_grupo',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)),
                                 label('conclu',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 503, 1)], else_=0))),
                                 label('exec',func.sum(case([(Pactos_de_Trabalho_Atividades.situacaoId == 502, 1)], else_=0))),
                                 label('tempo_prev_total',func.sum(Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem)),
                                 Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                          .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                          .join(Atividades, Atividades.itemCatalogoId == Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                          .group_by(Pactos_de_Trabalho_Atividades.itemCatalogoId,
                                    Atividades.titulo)\
                          .order_by(Atividades.titulo)\
                          .all()

    # conta quantas atividades estão no plano
    qtd_items_cat = len(items_cat)

    # histórico do pg e do pacto 
    historico_pg = db.session.query(label('id',Planos_de_Trabalho_Hist.planoTrabalhoHistoricoId),
                                    label("situa",catdom.descricao),
                                    literal('Histórico PG').label("tipo"),
                                    label('data',Planos_de_Trabalho_Hist.DataOperacao),
                                    label('tit',Planos_de_Trabalho_Hist.observacoes),
                                    Pessoas.pesNome)\
                             .filter(Planos_de_Trabalho_Hist.planoTrabalhoId == demanda.planoTrabalhoId)\
                             .join(catdom, catdom.catalogoDominioId == Planos_de_Trabalho_Hist.situacaoId)\
                             .join(Pessoas, Pessoas.pessoaId == Planos_de_Trabalho_Hist.responsavelOperacao)\
                             .order_by(Planos_de_Trabalho_Hist.DataOperacao.desc())\
                             .all()

    historico_pt = db.session.query(label('id',Pactos_de_Trabalho_Hist.pactoTrabalhoHistoricoId),
                                    label("situa",catdom.descricao),
                                    literal('Histórico').label("tipo"),
                                    label('data',Pactos_de_Trabalho_Hist.dataOperacao),
                                    label('tit',Pactos_de_Trabalho_Hist.observacoes),
                                    Pessoas.pesNome)\
                             .filter(Pactos_de_Trabalho_Hist.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                             .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Hist.situacaoId)\
                             .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho_Hist.responsavelOperacao)\
                             .order_by(Pactos_de_Trabalho_Hist.dataOperacao.desc())\
                             .all()
    historico = historico_pg + historico_pt 

    # solicitações
    analistas = db.session.query(Pessoas.pessoaId, Pessoas.pesNome).subquery()
    
    solicit  = db.session.query(label('id',Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId),
                                label("tipo",catdom.descricao),
                                label('data',Pactos_de_Trabalho_Solic.dataSolicitacao),
                                label('dataFim',Pactos_de_Trabalho_Solic.dataAnalise),
                                label('tit',Pactos_de_Trabalho_Solic.dadosSolicitacao),
                                label('obs',Pactos_de_Trabalho_Solic.observacoesSolicitante),
                                label('desc',Pactos_de_Trabalho_Solic.observacoesAnalista),
                                label('nota',Pactos_de_Trabalho_Solic.aprovado),
                                Pessoas.pesNome,
                                label('analist',analistas.c.pesNome))\
                         .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho_Solic.solicitante)\
                         .outerjoin(analistas, analistas.c.pessoaId == Pactos_de_Trabalho_Solic.analista)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Solic.tipoSolicitacaoId)\
                         .order_by(Pactos_de_Trabalho_Solic.dataSolicitacao.desc())\
                         .all()                                           

    # Instanciando a classe herdada
    pdf = PDF_relatorio()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Times', '', 12)

    # dados do pacto
    pdf.set_text_color(0,0,0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(23, 7, 'Responsável:', 'LT', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(130, 7, demanda.pesNome, 'T', 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(15, 7, 'Unidade:', 'T', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, demanda.undSigla, 'TR', 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(17, 7, 'Situação:', 'L', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, demanda.descricao, 'R', 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(10, 7, 'Início: ', 'L' ,0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(22, 7, data_string(demanda.dataInicio), 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(8, 7, 'Fim:', 0, 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(22, 7, data_string(demanda.dataFim), 0, 0)   
    pdf.cell(0, 7,'('+str(qtd_dias_uteis_sf)+ ' dias de semana, sendo ' +str(qtd_dias_uteis)+ ' úteis)', 'R', 1)
    pdf.set_font('Arial', '', 10)                           
    pdf.cell(13, 7, 'Forma:', 'L', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, demanda.forma+ ' - ' +ponto_por_virgula(demanda.cargaHorariaDiaria)+ ' h/dia', 'R', 1)
    pdf.set_font('Arial', '', 10)                           
    pdf.cell(39, 7, 'Tempo total disponível:', 'L', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, ponto_por_virgula(demanda.tempoTotalDisponivel)+ ' h', 'R', 1)
    pdf.set_font('Arial', '', 10) 
    pdf.cell(41, 7, 'Percentual de execução:', 'LB', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(10, 7, ponto_por_virgula(demanda.percentualExecucao).replace('.',','), 'B', 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(46, 7, 'Relação Previsto/Realizado:', 'B', 0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, ponto_por_virgula(demanda.relacaoPrevistoRealizado).replace('.',',')+' %', 'BR', 1)

    pdf.ln(4)

    # atividades do pacto
    pdf.set_text_color(0,0,0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, str(qtd_items_cat)+' ATIVIDADES', 0, 1)

    for ativ in items_cat:
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 5, '    '+str(ativ.seq)+'. ' +ativ.titulo, 0, 1)
        pdf.set_font('Arial', '', 8)
        pdf.cell(0, 5, '       '+str(ativ.tempo_prev_total).replace(".",",")+ ' h', 0, 1)

        ocor = db.session.query(label('seq',func.row_number().over(order_by=(Pactos_de_Trabalho_Atividades.situacaoId,
                                                                             Pactos_de_Trabalho_Atividades.dataInicio,
                                                                             Pactos_de_Trabalho_Atividades.dataFim))),
                                label('id',Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId),
                                label('situa',catdom_1.descricao),
                                Pactos_de_Trabalho_Atividades.nota,
                                Pactos_de_Trabalho_Atividades.tempoPrevistoPorItem,
                                Pactos_de_Trabalho_Atividades.tempoPrevistoTotal,
                                Pactos_de_Trabalho_Atividades.dataInicio,
                                Pactos_de_Trabalho_Atividades.dataFim,
                                label('tit',Pactos_de_Trabalho_Atividades.descricao),
                                label('desc',Pactos_de_Trabalho_Atividades.consideracoesConclusao),
                                catdom.descricao,
                                Pactos_de_Trabalho_Atividades.tempoRealizado,
                                Pactos_de_Trabalho_Atividades.tempoHomologado,
                                Pactos_de_Trabalho_Atividades.justificativa,
                                Objetos.chave,
                                label('obj_desc',Objetos.descricao))\
                         .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id,
                                 Pactos_de_Trabalho_Atividades.itemCatalogoId == ativ.itemCatalogoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.modalidadeExecucaoId)\
                         .join(catdom_1, catdom_1.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                         .outerjoin(Objeto_Atividade_Pacto,Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId==Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                         .outerjoin(Objeto_PG, Objeto_PG.planoTrabalhoObjetoId==Objeto_Atividade_Pacto.planoTrabalhoObjetoId)\
                         .outerjoin(Objetos, Objetos.objetoId==Objeto_PG.objetoId)\
                         .order_by(Pactos_de_Trabalho_Atividades.situacaoId,
                                   Pactos_de_Trabalho_Atividades.dataInicio,
                                   Pactos_de_Trabalho_Atividades.dataFim)\
                         .all()

        pdf.set_font('Arial', 'B', 8)
        pdf.cell(0, 7, '        '+str(ativ.tam_grupo)+' OCORRÊNCIAS', 0, 1)
        pdf.set_font('Arial', '', 7)

        for o in ocor:

            assuntos = db.session.query(Assuntos)\
                                 .filter(Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId==o.id)\
                                 .join(Atividade_Pacto_Assunto,Atividade_Pacto_Assunto.assuntoId==Assuntos.assuntoId)\
                                 .order_by(Assuntos.chave)\
                                 .all()

            pdf.cell(0, 5, '            '+str(o.seq)+'. Situação: '+o.situa+'     Início: ' +data_string(o.dataInicio)+'    Fim: '+ data_string(o.dataFim), 0, 1)
            if o.tit:
                pdf.cell(0, 5, '                Descrição: '+o.tit, 0, 1)
            if o.desc:    
                pdf.cell(0, 5, '                Considerações e Conclusão: '+o.desc, 0, 1)
            if o.chave:    
                pdf.cell(0, 5, '                    Objeto: '+o.chave+' - '+o.obj_desc, 0, 1)
            if assuntos:
                pdf.cell(0, 5, '                    Assuntos:', 0, 1)
                for a in assuntos:
                    pdf.cell(0, 5, '                        '+a.chave[4:6]+'/'+a.chave[2:4]+'/'+a.chave[0:2]+' - '+a.valor, 0, 1)

        pdf.ln(5)


    # solicitações
    if solicit:
        pdf.set_text_color(0,0,0)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, 'SOLICITAÇÕES', 0, 1)
        pdf.set_font('Arial', '', 8)

        for sol in solicit:
            # monta dicionários com o campo dadosSolicitacao das solicitações do pacto que está sendo visto
            dados_solic = ast.literal_eval(str(sol.tit).replace('null','None').replace('true','True').replace('false','False'))

            pdf.cell(0, 5, 'Data: ' +data_string(sol.data)+ '    Tipo: ' +sol.tipo, 0, 1)
            pdf.cell(0, 5, 'Solicitante: ' +sol.pesNome, 0, 1)
            pdf.cell(0, 5, 'Observações: ' +sol.obs, 0, 1)
            if sol.nota != None and sol.nota != '':
                pdf.ln(2)
                if sol.nota == False:
                    parecer = 'Recusada'
                else:
                    parecer = 'Aprovada' 
                pdf.cell(0, 5, 'Data análise: ' +data_string(sol.dataFim)+ '    Avaliação: '+parecer, 0, 1)
                pdf.cell(0, 5, 'Analista: ' +sol.analist, 0, 1)
                pdf.cell(0, 5, 'Observações do analista: ' +sol.desc, 0, 1)
            else:
                pdf.cell(0, 7, 'NÃO AVALIADA', 0, 1)    
            pdf.ln(4)    

    # histórico 
    pdf.set_text_color(0,0,0)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, 'HISTÓRICO', 0, 1)
    pdf.set_font('Arial', '', 8)

    for hist in historico:
        pdf.cell(0, 5, '    Data: ' +data_string(hist.data), 0, 1)
        if hist.tipo == 'Histórico PG':
            tipo = 'Alteração em PG'
        else:
            tipo = 'Alteração em Plano'    
        pdf.cell(0, 5, '    Tipo: ' +tipo+ '    Situação: ' +hist.situa+ '    Responsável: ' +hist.pesNome , 0, 1)
        pdf.ln(4)



    pasta_pdf = os.path.normpath('/app/project/static/relatorio.pdf')
    # if not os.path.exists(os.path.normpath('/temp/')):
    #     os.makedirs(os.path.normpath('/temp/'))
    pdf.output(pasta_pdf, 'F')

    # o comandinho mágico que permite fazer o download de um arquivo
    send_from_directory('/app/project/static', 'relatorio.pdf')


    return render_template('relatorio.html')