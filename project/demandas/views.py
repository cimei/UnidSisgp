"""
.. topic:: Demandas (views)

    Compõe o trabalho diário da coordenação. Consistem da atividades da coordenação, cadastratas no PGD.

.. topic:: Ações relacionadas às demandas

    * Listar programas de gestão da unidade: plano_trabalho
    * Lista atividades de um PG: lista_atividades_pg
    * Lista metas de um pg: lista_metas_pg
    * Lista pactos de um pg: lista_pactos_pg
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
                           Atividades, catdom, Pactos_de_Trabalho, Planos_de_Trabalho_Reuniao,\
                           Pactos_de_Trabalho_Solic, Pactos_de_Trabalho_Atividades, Planos_de_Trabalho_Metas    

from project.usuarios.views import registra_log_auto                                   

from datetime import datetime, date, timedelta
# from fpdf import FPDF

import pickle
import os.path
import sys

demandas = Blueprint("demandas",__name__,template_folder='templates')

## lista plano de trabalho

@demandas.route('/<lista>/plano_trabalho')
def plano_trabalho(lista):
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
    unid_dados = db.session.query(Unidades.undSigla, Unidades.unidadeIdPai).filter(Unidades.unidadeId == unid_id.unidadeId).first()

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

    if lista == 'Todas':
        lista = '%'

    planos_trab_unid = db.session.query(Planos_de_Trabalho.planoTrabalhoId,
                                        Planos_de_Trabalho.situacaoId,
                                        Planos_de_Trabalho.dataInicio,
                                        Planos_de_Trabalho.dataFim,
                                        catdom.descricao,
                                        ativs.c.qtd_ativs,
                                        metas.c.qtd_metas,
                                        pactos.c.qtd_pactos)\
                                 .join(catdom, catdom.catalogoDominioId == Planos_de_Trabalho.situacaoId)\
                                 .join(ativs, ativs.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .outerjoin(metas, metas.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .outerjoin(pactos,pactos.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .filter(Planos_de_Trabalho.unidadeId == unid_id.unidadeId, catdom.descricao.like(lista))\
                                 .order_by(catdom.descricao, Planos_de_Trabalho.dataInicio.desc())\
                                 .all() 


    quantidade = len(planos_trab_unid)


    return render_template('plano_trabalho.html', lista=lista, unid_dados = unid_dados, planos_trab_unid=planos_trab_unid, quantidade=quantidade)



## lista atividades de um pg

@demandas.route('/<pg>/lista_atividades_pg')

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

@demandas.route('/<pg>/lista_metas_pg')

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

@demandas.route('/<pg>/lista_pactos_pg')

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



#lendo uma demanda

@demandas.route('/demanda/<pacto_id>',methods=['GET','POST'])
def demanda(pacto_id):
    """+---------------------------------------------------------------------------------+
       |Resgata, para leitura, uma demanda (pacto de trabalho) e registros associados.   |
       |                                                                                 |
       |Recebe o ID do pacto como parâmetro.                                             |
       +---------------------------------------------------------------------------------+
    """

    catdom_1 = db.session.query(catdom.catalogoDominioId,
                                catdom.descricao)\
                         .filter(catdom.classificacao == 'SituacaoPactoTrabalho')\
                         .subquery()

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
                               label('forma',catdom.descricao))\
                         .filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id)\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                         .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                         .first()

    items_cat = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId, Atividades.titulo)\
                          .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId == demanda.planoTrabalhoId)\
                          .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                          .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
                          .order_by(Atividades.titulo)\
                          .all()
    
    reunioes = db.session.query(literal('Reunião').label("tipo"),
                                Planos_de_Trabalho_Reuniao.data,
                                literal(None).label("dataFim"),
                                label('tit',Planos_de_Trabalho_Reuniao.titulo),
                                label('desc',Planos_de_Trabalho_Reuniao.descricao),
                                literal(None).label("tempoRealizado"),
                                literal(None).label("nota"))\
                          .filter(Planos_de_Trabalho_Reuniao.planoTrabalhoId == demanda.planoTrabalhoId)\
                          .all()

    solicit  = db.session.query (literal('Solicitação').label("tipo"),
                                 label('data',Pactos_de_Trabalho_Solic.dataSolicitacao),
                                 label('dataFim',Pactos_de_Trabalho_Solic.dataAnalise),
                                 label('tit',Pactos_de_Trabalho_Solic.observacoesSolicitante),
                                 label('desc',Pactos_de_Trabalho_Solic.observacoesAnalista),
                                literal(None).label("tempoRealizado"),
                                literal(None).label("nota"))\
                         .filter(Pactos_de_Trabalho_Solic.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                         .all()

    ativs    = db.session.query (literal('Atividade').label("tipo"),
                                 label('data',Pactos_de_Trabalho_Atividades.dataInicio),
                                 Pactos_de_Trabalho_Atividades.dataFim,
                                 label('tit',Pactos_de_Trabalho_Atividades.descricao),
                                 label('desc',Pactos_de_Trabalho_Atividades.consideracoesConclusao),
                                 Pactos_de_Trabalho_Atividades.tempoRealizado,
                                 Pactos_de_Trabalho_Atividades.nota)\
                         .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == demanda.pactoTrabalhoId)\
                         .all()

    pro_des = reunioes + solicit + ativs
    pro_des.sort(key=lambda ordem: (ordem.data is not None,ordem.data),reverse=True)

    

#     # gera um pdf com todo o histórico da demanda

#     form = Pdf_Form()

#     if form.validate_on_submit():

#         class PDF(FPDF):
#             # cabeçalho com dados da demanda
#             def header(self):
#                 # Logo
#                 # self.image('logo_pb.png', 10, 8, 33)
#                 self.set_font('Arial', 'B', 13)
#                 self.set_text_color(127,127,127)
#                 self.cell(0, 10, 'Relatório de Demanda - gerado em '+date.today().strftime('%x'), 1, 1,'C')
#                 # Nº da demanda, coordenação e atividade
#                 if demanda.atividade_sigla == None:
#                     self.set_text_color(127,127,127)
#                     self.cell(25, 8, 'Demanda: ', 0, 0)
#                     self.set_text_color(0,0,0)
#                     self.cell(35, 8, str(demanda.id)+' ('+demanda.coord+')', 0, 0,'C')
#                     self.set_text_color(0,0,0)
#                     self.cell(0, 8, ' Atividade não definida', 0, 1)
#                 else:
#                     self.set_text_color(127,127,127)
#                     self.cell(25, 8, 'Demanda: ', 0, 0)
#                     self.set_text_color(0,0,0)
#                     self.cell(35, 8, str(demanda.id)+' ('+demanda.coord+')', 0, 0,'C')
#                     self.set_text_color(127,127,127)
#                     self.cell(25, 8, ' Atividade: ', 0, 0)
#                     self.set_text_color(0,0,0)
#                     self.cell(0, 8, demanda.atividade_sigla, 0, 1)
#                 # título da demanda
#                 self.set_text_color(127,127,127)
#                 self.cell(18, 6, 'Título: ', 0, 0)
#                 self.set_text_color(0,0,0)
#                 titulo = demanda.titulo.encode('latin-1', 'replace').decode('latin-1')
#                 tamanho_titulo = self.get_string_width(titulo)
#                 #print ('**** titulo ', tamanho_titulo)
#                 self.multi_cell(0, 6, titulo)
#                 if tamanho_titulo <= 100:
#                     pdf.ln(12)
#                 else:
#                     pdf.ln(tamanho_titulo/10)
#                 # tipo e SEI
#                 self.set_text_color(127,127,127)
#                 self.cell(12, 8, 'Tipo: ', 0, 0)
#                 self.set_text_color(0,0,0)
#                 self.cell(90, 8, demanda.tipo, 0, 0)
#                 self.set_text_color(127,127,127)
#                 self.cell(12, 8, 'SEI: ', 0, 0)
#                 self.set_text_color(0,0,0)
#                 self.cell(0, 8, demanda.sei, 0, 1)
#                 # responsável
#                 self.set_text_color(127,127,127)
#                 self.cell(16, 8, 'Resp.: ', 0, 0)
#                 self.set_text_color(0,0,0)
#                 self.cell(0, 8, demanda.username, 0, 1)
#                 # datas
#                 if demanda.conclu:
#                     self.set_text_color(127,127,127)
#                     self.cell(25, 8, 'Criada em: ', 0, 0)
#                     self.set_text_color(0,0,0)
#                     self.cell(30, 8, demanda.data.strftime('%x'), 0, 0)
#                     self.set_text_color(127,127,127)
#                     self.cell(33, 8, 'Finalizada em: ', 0, 0)
#                     self.set_text_color(0,0,0)
#                     self.cell(0, 8, demanda.data_conclu.strftime('%x'), 0, 1)
#                 else:
#                     self.set_text_color(127,127,127)
#                     self.cell(25, 8, 'Criada em: ', 0, 0)
#                     self.set_text_color(0,0,0)
#                     self.cell(30, 8, demanda.data.strftime('%x'), 0, 0)
#                     self.cell(0, 8,'Não concluída', 0, 1)
#                 # descrição
#                 self.set_text_color(127,127,127)
#                 self.cell(27, 6, 'Descrição: ', 0, 0)
#                 self.set_text_color(0,0,0)
#                 desc = demanda.desc.encode('latin-1', 'replace').decode('latin-1')
#                 tamanho_desc = self.get_string_width(desc)
#                 #print ('**** desc ', tamanho_desc)
#                 self.multi_cell(0, 6, desc)
#                 if tamanho_desc <= 100:
#                     pdf.ln(6)
#                 else:
#                     pdf.ln(tamanho_desc/12)
#                 # se necessita despachos
#                 if demanda.necessita_despacho:
#                     self.cell(0, 10, 'Aguarda despacho', 0, 1)
#                 if demanda.necessita_despacho_cg:
#                     self.cell(0, 10, 'Aguarda despacho Coord. Geral ou sup.', 0, 1)
#                 # Line break
#                 self.ln(10)
#                 self.set_text_color(127,127,127)
#                 self.cell(0, 10, 'Providências e Despachos', 1, 1,'C')

#             # Rodape da página
#             def footer(self):
#                 # Posicionado a 1,5 cm do final da página
#                 self.set_y(-15)
#                 # Arial italic 8 cinza
#                 self.set_font('Arial', 'I', 8)
#                 self.set_text_color(127,127,127)
#                 # Numeração de página
#                 self.cell(0, 10, 'Página ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

#         # Instanciando a classe herdada
#         pdf = PDF()
#         pdf.alias_nb_pages()
#         pdf.add_page()
#         pdf.set_font('Times', '', 12)
#         # Providêcias e Despachos: responsável, data e descrição
#         for item in pro_des:
#             pdf.set_text_color(0,0,0)
#             pdf.cell(50, 10, item.username, 0, 0)
#             pdf.set_text_color(127,127,127)
#             pdf.cell(8, 10, 'Em: ', 0, 0)
#             pdf.set_text_color(0,0,0)
#             pdf.cell(0, 10, item.data.strftime('%x'), 0, 1)
#             texto = item.texto.encode('latin-1', 'replace').decode('latin-1')
#             tamanho_texto = pdf.get_string_width(texto)
#             pdf.multi_cell(0, 5, texto)
#             if tamanho_texto <= 100:
#                 pdf.ln(15)
#             else:
#                 pdf.ln(tamanho_texto/10)
#             pdf.dashed_line(pdf.get_x(), pdf.get_y(), pdf.get_x()+190, pdf.get_y(), 2, 3)

#             #print ('**** prov_desp ', tamanho_texto)
#         #pasta_pdf = os.path.normpath('C:'+str(demanda.id)+'.pdf')

#         pasta_pdf = os.path.normpath('c:/temp/'+str(demanda.id)+'.pdf')
#         if not os.path.exists(os.path.normpath('c:/temp/')):
#             os.makedirs(os.path.normpath('c:/temp/'))
#         pdf.output(pasta_pdf, 'F')

#         flash ('Relatório da demanada '+str(demanda.id)+' gerado! Verifique na pasta temp do disco C: o arquivo '+str(demanda.id)+'.pdf','sucesso')

    return render_template('ver_demanda.html',
                            id        = pacto_id,
                            post      = demanda,
                            items_cat = items_cat,
                            pro_des   = pro_des)

# vendo todas as demandas da unidade

@demandas.route('/<lista>/demandas')
def list_demandas(lista):

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

    #pega unidade do usuário logado
    unid_id    = db.session.query(Pessoas.unidadeId).filter(Pessoas.pesEmail == email).first()

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
                               Unidades.undSigla,
                               catdom_1.c.descricao,
                               label('forma',catdom.descricao))\
                         .filter(Pactos_de_Trabalho.unidadeId == unid_id.unidadeId, catdom_1.c.descricao.like(lista))\
                         .join(Pessoas, Pessoas.pessoaId == Pactos_de_Trabalho.pessoaId)\
                         .join(Unidades, Unidades.unidadeId == Pactos_de_Trabalho.unidadeId)\
                         .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                         .join(catdom, catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                         .order_by(catdom_1.c.descricao,Pactos_de_Trabalho.dataInicio.desc())\
                         .paginate(page=page,per_page=8)

    demandas_count = db.session.query(Pactos_de_Trabalho)\
                               .join(catdom_1, catdom_1.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                               .filter(Pactos_de_Trabalho.unidadeId == unid_id.unidadeId, catdom_1.c.descricao.like(lista))\
                               .count()

    dem = db.session.query(Pactos_de_Trabalho.planoTrabalhoId)\
                    .filter(Pactos_de_Trabalho.unidadeId == unid_id.unidadeId)\
                    .all()
    
    pts = [item.planoTrabalhoId for item in dem]

    items_cat = db.session.query(Planos_de_Trabalho_Ativs.planoTrabalhoId, Atividades.titulo)\
                          .filter(Planos_de_Trabalho_Ativs.planoTrabalhoId.in_(pts))\
                          .join(Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Ativs_Items.planoTrabalhoAtividadeId == Planos_de_Trabalho_Ativs.planoTrabalhoAtividadeId)\
                          .join(Atividades, Atividades.itemCatalogoId == Planos_de_Trabalho_Ativs_Items.itemCatalogoId)\
                          .order_by(Atividades.titulo)\
                          .all()

    return render_template ('demandas.html', lista=lista, items_cat=items_cat, demandas=demandas, demandas_count=demandas_count)


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

