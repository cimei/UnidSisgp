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

from flask import render_template, url_for, flash, redirect, Blueprint
from flask_login import current_user, login_required
from sqlalchemy import func, literal, case, cast, String, literal_column
from sqlalchemy.sql import label
from sqlalchemy.orm import aliased
from project import db
from project.models import Planos_de_Trabalho_Ativs, Planos_de_Trabalho_Ativs_Items, Planos_de_Trabalho_Hist, Unidades, Pessoas, Planos_de_Trabalho,\
                           Atividades, VW_Unidades, cat_item_cat, catdom, Pactos_de_Trabalho, Planos_de_Trabalho_Metas, Objeto_PG, unidade_ativ

from project.pgs.forms import PGForm                               

from project.usuarios.views import registra_log_unid                           

from datetime import datetime

import uuid
import os

pgs = Blueprint("pgs",__name__,template_folder='templates')


# ver dados de um pg
@pgs.route('/<pg_id>/ver_pg')
@login_required
def ver_pg(pg_id):
    """
    +---------------------------------------------------------------------------------------+
    |Visualiza dados de um Programa de Gestão.                                              |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    pg = db.session.query(Planos_de_Trabalho.planoTrabalhoId,
                          Planos_de_Trabalho.dataInicio,
                          Planos_de_Trabalho.dataFim,
                          Planos_de_Trabalho.tempoComparecimento,
                          Planos_de_Trabalho.termoAceite,
                          Unidades.undSigla,
                          catdom.descricao)\
                   .join(Unidades, Unidades.unidadeId==Planos_de_Trabalho.unidadeId)\
                   .join(catdom, catdom.catalogoDominioId==Planos_de_Trabalho.situacaoId)\
                   .filter(Planos_de_Trabalho.planoTrabalhoId == pg_id)\
                   .first() 

    return render_template('ver_pg.html', pg=pg)

## lista plano de trabalho (programa de gestão)

@pgs.route('/<lista>/<coord>/plano_trabalho')
@login_required
def plano_trabalho(lista,coord):
    """
    +---------------------------------------------------------------------------------------+
    |Apresenta os planos de trabalho (programas de gestão) da unidade.                      |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """
    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega dados em Pessoas do usuário logado
    usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first()

    #pega unidade do usuário logado
    unid_id    = db.session.query(Pessoas.unidadeId).filter(Pessoas.pesEmail == email).first()
    unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                           .filter(Unidades.unidadeId == unid_id.unidadeId)\
                           .outerjoin(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
                           .first()
    unid = unid_id.unidadeId

    #possibilidade de ver outra unidade
    if coord != '*':
        unid_dados = db.session.query(Unidades.unidadeId, Unidades.undSigla, Unidades.unidadeIdPai, VW_Unidades.undSiglaCompleta)\
                               .outerjoin(VW_Unidades, VW_Unidades.unidadeId == Unidades.unidadeId)\
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

    # alias do catdom para pegar modalidade de execução do PG
    catdom_1 = aliased(catdom)    

    hoje = datetime.now()

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
                                        Unidades.unidadeId,
                                        label('modalidade',catdom_1.descricao),
                                        label('vencido',case((Planos_de_Trabalho.dataFim < hoje, literal_column("'s'")), else_=literal_column("'n'"))))\
                                 .join(catdom, catdom.catalogoDominioId == Planos_de_Trabalho.situacaoId)\
                                 .join(ativs, ativs.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .join(Unidades, Unidades.unidadeId == Planos_de_Trabalho.unidadeId)\
                                 .join(Planos_de_Trabalho_Ativs,Planos_de_Trabalho_Ativs.planoTrabalhoId==Planos_de_Trabalho.planoTrabalhoId)\
                                 .join(catdom_1, catdom_1.catalogoDominioId == Planos_de_Trabalho_Ativs.modalidadeExecucaoId)\
                                 .outerjoin(metas, metas.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .outerjoin(pactos,pactos.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .outerjoin(objetos,objetos.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                                 .filter(Planos_de_Trabalho.unidadeId.in_(tree[unid_dados.undSigla]), catdom.descricao.like(lista))\
                                 .order_by(Unidades.unidadeId,Planos_de_Trabalho.situacaoId, Planos_de_Trabalho.dataInicio.desc())\
                                 .all() 


    quantidade = len(planos_trab_unid)

    sit_pg_dict = {}
    sit_pg = db.session.query(catdom.descricao).filter(catdom.classificacao == 'SituacaoPlanoTrabalho').all()
    for s in sit_pg:
        sit_pg_dict[s.descricao] = s.descricao

    return render_template('plano_trabalho.html', lista=lista, 
                                                  unid_dados = unid_dados,
                                                  planos_trab_unid=planos_trab_unid,
                                                  quantidade=quantidade,
                                                  sit_pg_dict=sit_pg_dict,
                                                  usuario=usuario)



## lista atividades de um pg

@pgs.route('/<pg>/lista_atividades_pg')
@login_required
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
@login_required
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
@login_required
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


## criar um pg

@pgs.route('/cria_pg', methods=['GET','POST'])
@login_required
def cria_pg():
    """
    +---------------------------------------------------------------------------------------+
    |Criando um programa de gestão (plano de trabalho no DBSISGP).                          |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """ 

    hoje = datetime.now()

    #pega unidade e id pessoa do usuário logado
    unid = db.session.query(Pessoas.unidadeId, Pessoas.pessoaId).filter(Pessoas.pesEmail == current_user.pesEmail).first()

    #pega total de servidores do setor
    total_serv_setor = db.session.query(Pessoas).filter(Pessoas.pesEmail == current_user.pesEmail).count()

    #pega modalidades de execução
    mods = db.session.query(catdom).filter(catdom.classificacao == 'ModalidadeExecucao').all()

    #pega atividades associadas a unidade do usuário
    ativs_unid = db.session.query(Atividades.itemCatalogoId,
                                  label('desc',Atividades.titulo+' - '+Atividades.complexidade+' - (R: '+\
                                        cast(Atividades.tempoRemoto, String)+'h - P: '+ cast(Atividades.tempoPresencial, String)+'h)'))\
                           .join(cat_item_cat, cat_item_cat.itemCatalogoId == Atividades.itemCatalogoId)\
                           .join(unidade_ativ, unidade_ativ.catalogoId == cat_item_cat.catalogoId)\
                           .filter(unidade_ativ.unidadeId == unid.unidadeId)\
                           .order_by(Atividades.titulo)\
                           .all()          

    form = PGForm()

    form.ativs.choices = [(a.itemCatalogoId,a.desc) for a in ativs_unid]
    
    lista_mods = [(m.catalogoDominioId,m.descricao) for m in mods]
    lista_mods.insert(0,('',''))
    form.modalidade.choices = lista_mods 

    #pega o termo de aceite que fica na pasta static
    pasta_termo = os.path.normpath('/app/project/static/termo.txt')
    with open(pasta_termo, 'r') as file:
        termo_aceite = file.read().replace('\n', '')

    if form.validate_on_submit():

        #cria registro em Planos_de_Trabalho já como "Em Execução"
        pg = Planos_de_Trabalho(planoTrabalhoId = uuid.uuid4(),
                                unidadeId            = unid.unidadeId,
                                situacaoId           = 309,
                                avaliacaoId          = None,
                                dataInicio           = form.data_ini.data,
                                dataFim              = form.data_fim.data,
                                tempoComparecimento  = form.tempo_comp.data,
                                totalServidoresSetor = total_serv_setor,
                                tempoFaseHabilitacao = 1,
                                termoAceite          = termo_aceite)

        db.session.add(pg)

        #cria registro em Planos_de_Trabalho_Hist
        hist = Planos_de_Trabalho_Hist(planoTrabalhoHistoricoId = uuid.uuid4(),
                                       planoTrabalhoId     = pg.planoTrabalhoId,
                                       situacaoId          = pg.situacaoId,
                                       observacoes         = 'Criado de forma direta',
                                       responsavelOperacao = unid.pessoaId,
                                       DataOperacao        = hoje)

        db.session.add(hist)

        #cria um registro em Planos_de_Trabalho_Ativs
        pg_ativs = Planos_de_Trabalho_Ativs(planoTrabalhoAtividadeId = uuid.uuid4(),
                                            planoTrabalhoId         = pg.planoTrabalhoId,
                                            modalidadeExecucaoId    = int(form.modalidade.data),
                                            quantidadeColaboradores = int(form.qtd_colab.data),
                                            descricao               = None)

        db.session.add(pg_ativs)

        #cria registros em Planos_de_Trabalho_Ativs_Itens (um para cada atividade escolhida)
        for a in form.ativs.data:

            pg_ativs_item = Planos_de_Trabalho_Ativs_Items (planoTrabalhoAtividadeItemId = uuid.uuid4(),
                                                            planoTrabalhoAtividadeId = pg_ativs.planoTrabalhoAtividadeId,
                                                            itemCatalogoId = a)

            db.session.add(pg_ativs_item)

        db.session.commit()                                                  
          
        registra_log_unid(current_user.pessoaId,'Programa de Gestão criado.')                                 

        return redirect(url_for('pgs.plano_trabalho', lista = 'Todas', coord = '*'))

    return render_template('add_pg.html',form=form)



## finalizar programas de gestão vencidos

@pgs.route('/finaliza_pgs',methods=['GET','POST'])
@login_required
def finaliza_pgs():
    """
    +---------------------------------------------------------------------------------------+
    |Finaliza programas de gestão que estão com vigência expirada.                          |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    hoje = datetime.now()

    #pega e-mail do usuário logado
    email = current_user.pesEmail

    #pega unidade do usuário logado
    unid = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first()

    # subquery para identificar PGs que tem planos(pactos) associados
    pactos = db.session.query(Pactos_de_Trabalho.planoTrabalhoId,
                              label('qtd_pactos',func.count(Pactos_de_Trabalho.pactoTrabalhoId)))\
                       .filter(Pactos_de_Trabalho.unidadeId == unid.unidadeId)\
                       .group_by(Pactos_de_Trabalho.planoTrabalhoId)\
                       .subquery()

    pgs_unid = db.session.query(Planos_de_Trabalho.planoTrabalhoId,
                                Planos_de_Trabalho.unidadeId,
                                Planos_de_Trabalho.dataFim,
                                Planos_de_Trabalho.situacaoId,
                                pactos.c.qtd_pactos)\
                         .filter(Planos_de_Trabalho.unidadeId == unid.unidadeId, Planos_de_Trabalho.dataFim < hoje)\
                         .outerjoin(pactos,pactos.c.planoTrabalhoId == Planos_de_Trabalho.planoTrabalhoId)\
                         .order_by(Planos_de_Trabalho.situacaoId)\
                         .all() 

    quantidade = len(pgs_unid)

    for pg in pgs_unid:

        pg_finalizar = db.session.query(Planos_de_Trabalho).filter(Planos_de_Trabalho.planoTrabalhoId == pg.planoTrabalhoId).first()

        if pg.qtd_pactos == 0 or pg.qtd_pactos == None:
            pg_finalizar.situacaoId = 311  ## Concluído
        else:
            pg_finalizar.situacaoId = 310  ## Executado

        #cria registro em Planos_de_Trabalho_Hist
        hist = Planos_de_Trabalho_Hist(planoTrabalhoHistoricoId = uuid.uuid4(),
                                       planoTrabalhoId     = pg_finalizar.planoTrabalhoId,
                                       situacaoId          = pg_finalizar.situacaoId,
                                       observacoes         = 'Finalizado por vigência expirada',
                                       responsavelOperacao = unid.pessoaId,
                                       DataOperacao        = hoje)

        db.session.add(hist)

        db.session.commit()    

    registra_log_unid(current_user.pessoaId,'Procedimento de finalização de PGs vencidos foi realizado. '+str(quantidade)+' registros afetados.')
    flash(str(quantidade) +' Programas de Gestão foram Concluídos ou Executados por estarem com vigência encerrada!','sucesso')

    return redirect(url_for('pgs.plano_trabalho', lista = 'Todas', coord = '*'))



