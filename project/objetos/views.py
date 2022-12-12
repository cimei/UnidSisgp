"""
.. topic:: Objetos (views)

    Objetos de atividades.

.. topic:: Ações relacionadas a objetos

    * Lista objetos em uma coordenação: lista_objetos
    * Lista objetos de um PG: lista_objetos_pg
    * Cria um novo objeto: add_objeto
    * Altera um objeto existente: altera_objeto

"""

# views.py dentro da pasta objetos

from flask import render_template, url_for, flash, request, redirect, Blueprint, abort
from flask_login import current_user, login_required
from sqlalchemy import func, literal, distinct
from sqlalchemy.sql import label
from project import db 
from project.models import Atividades, Objetos, Objeto_Atividade_Pacto, Objeto_PG, Pactos_de_Trabalho, Pactos_de_Trabalho_Atividades, Pessoas, Planos_de_Trabalho, Planos_de_Trabalho_Reuniao, Unidades, VW_Unidades,\
                           Planos_de_Trabalho, Atividade_Pacto_Assunto, Assuntos

from project.objetos.forms import ObjetoEscolhaForm, ObjetoForm                               

from project.usuarios.views import registra_log_unid                                   

import uuid

objetos = Blueprint("objetos",__name__,template_folder='templates')

## lista objetos

@objetos.route('/<coord>/lista_objetos')
def lista_objetos(coord):
    """
    +---------------------------------------------------------------------------------------+
    |Lista conteudo da tabel Objeto relacionados a uma determinada unidade.                 |
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

    # resgata objetos 
    objetos = db.session.query(Objetos.objetoId,
                               Objetos.descricao,
                               Objetos.tipo,
                               Objetos.chave,
                               Objetos.ativo,
                               Unidades.undSigla)\
                        .join(Objeto_PG, Objeto_PG.objetoId == Objetos.objetoId)\
                        .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Objeto_PG.planoTrabalhoId)\
                        .join(Unidades, Unidades.unidadeId == Planos_de_Trabalho.unidadeId)\
                        .filter(Unidades.unidadeId.in_(tree[unid_dados.undSigla]))\
                        .all()

    quantidade = len(objetos)


    return render_template('lista_objetos.html', unid_dados = unid_dados, objetos=objetos, quantidade=quantidade, pg=None, usuario=None)

## lista objetos por PG

@objetos.route('/<pg>/lista_objetos_pg')
def lista_objetos_pg(pg):
    """
    +---------------------------------------------------------------------------------------+
    |Lista conteudo da tabel Objeto para um determinado PG                                  |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    # resgata objetos 
    objetos = db.session.query(Objetos.objetoId,
                               Objetos.descricao,
                               Objetos.tipo,
                               Objetos.chave,
                               Objetos.ativo)\
                        .join(Objeto_PG, Objeto_PG.objetoId == Objetos.objetoId)\
                        .filter(Objeto_PG.planoTrabalhoId == pg)\
                        .all()

    quantidade = len(objetos)


    return render_template('lista_objetos.html', unid_dados=None, objetos=objetos, quantidade=quantidade, pg=pg, usuario=None)

## lista objetos por Pessoa

@objetos.route('/<int:pessoa>/lista_objetos_pessoa')
def lista_objetos_pessoa(pessoa):
    """
    +---------------------------------------------------------------------------------------+
    |Lista conteudo da tabel Objeto para uma determinada Pessoa                             |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    #pega e-mail do usuário logado
    email = current_user.userEmail

    # possibilidade de consultar outra pessoa
    if pessoa != 0:
        #pega dados da pessoa informada
        pes = db.session.query(Pessoas.unidadeId,Pessoas.pessoaId,Pessoas.pesNome)\
                        .filter(Pessoas.pessoaId == pessoa).first()
        if pes == None:
            abort(404)
    else:
        #pega dados da pessoa logada
        pes = db.session.query(Pessoas.unidadeId,Pessoas.pessoaId,Pessoas.pesNome)\
                        .filter(Pessoas.pesEmail == email).first()

    # unidade do usuário
    unid = db.session.query(Unidades.undSigla).filter(Unidades.unidadeId == pes.unidadeId).first()

    # resgata objetos 
    objetos = db.session.query(distinct(Objetos.objetoId),
                               Objetos.descricao,
                               Objetos.tipo,
                               Objetos.chave,
                               Objetos.ativo)\
                        .join(Objeto_PG, Objeto_PG.objetoId == Objetos.objetoId)\
                        .join(Objeto_Atividade_Pacto, Objeto_Atividade_Pacto.planoTrabalhoObjetoId == Objeto_PG.planoTrabalhoObjetoId)\
                        .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId)\
                        .join(Pactos_de_Trabalho, Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                        .filter(Pactos_de_Trabalho.pessoaId == pes.pessoaId)\
                        .all()

    quantidade = len(objetos)


    return render_template('lista_objetos.html', unid_dados=None, objetos=objetos, quantidade=quantidade, pg=None,
                                                 usuario=pes, unid=unid)


## cria objeto

@objetos.route('/<plano_id>/<pacto_id>/add_objeto',methods=['GET','POST'])
@login_required
def add_objeto(plano_id,pacto_id):
    """
    +---------------------------------------------------------------------------------------+
    |Insere um objeto no banco de dados.                                                    |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    form = ObjetoForm()

    if form.validate_on_submit():

        # verifica se objeto já existe
        obj = db.session.query(Objetos).filter(Objetos.chave==form.chave.data).first()

        # não existindo, cria
        if not obj:

            objeto = Objetos(objetoId  = uuid.uuid4(),
                            descricao = form.desc.data,
                            tipo      = 1,
                            chave     = form.chave.data,
                            ativo     = True)

            db.session.add(objeto)
            db.session.commit()

        if obj:
            obj_id = obj.objetoId
        else:
            obj_id = objeto.objetoId

        objeto_pg = Objeto_PG(planoTrabalhoObjetoId = uuid.uuid4(),
                                planoTrabalhoId     = plano_id,
                                objetoId            = obj_id)                 

        db.session.add(objeto_pg)
        db.session.commit()

        registra_log_unid(current_user.id,'Objeto '+ obj_id +' inserido no banco de dados.')

        flash('Objeto registrado!','sucesso')

        if pacto_id == '*':

            return redirect(url_for('objetos.lista_objetos_pg',pg=plano_id))

        else:

            return redirect(url_for('demandas.demanda',pacto_id=pacto_id))


    return render_template('add_objeto.html', form=form, plano_id = plano_id)

## altera objeto

@objetos.route('/<objeto_id>/altera_objeto',methods=['GET','POST'])
@login_required
def altera_objeto(objeto_id):
    """
    +---------------------------------------------------------------------------------------+
    |Altera dados de um objeto.                                                             |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    objeto = db.session.query(Objetos).filter(Objetos.objetoId == objeto_id).first_or_404()

    form = ObjetoForm()

    if form.validate_on_submit():

        objeto.descricao = form.desc.data
        objeto.tipo      = 1
        objeto.chave     = form.chave.data
        objeto.ativo     = True

        db.session.commit()

        registra_log_unid(current_user.id,'Objeto '+ objeto_id +' alterado.')

        flash('Objeto alterado!','sucesso')

        return redirect(url_for('objetos.lista_objetos',coord='*'))

    form.desc.data  = objeto.descricao
    # form.tipo.data  = objeto.tipo
    form.chave.data = objeto.chave
    # form.ativo.data = objeto.ativo    

    return render_template('add_objeto.html', form=form)    

## relacionar objeto com atividade de um Pacto

@objetos.route('/<pacto_ativ_id>/<pacto_id>/objeto_ativ_pacto',methods=['GET','POST'])
@login_required
def objeto_ativ_pacto(pacto_id,pacto_ativ_id):
    """
    +---------------------------------------------------------------------------------------+
    |Relaciona um objeto a uma atividade de um pacto de trabalho.                           |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    # pega ocorrências da atividade no pacto de trabalho (plano)
    ativ = db.session.query(Pactos_de_Trabalho_Atividades.itemCatalogoId)\
                     .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == pacto_ativ_id)\
                     .first()

    # pega a unidade do pacto
    pacto = db.session.query(Pactos_de_Trabalho.unidadeId).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

    # identifica objetos da unidade
    objetos = db.session.query(Objetos.chave,
                               Objetos.descricao,
                               Objeto_PG.planoTrabalhoObjetoId)\
                        .join(Objeto_PG, Objeto_PG.objetoId == Objetos.objetoId)\
                        .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Objeto_PG.planoTrabalhoId)\
                        .filter(Planos_de_Trabalho.unidadeId == pacto.unidadeId)\
                        .order_by(Objetos.descricao)\
                        .all()                    

    # o choices do campo obj são definidos aqui e não no form
    lista_obj = [(o.planoTrabalhoObjetoId,(o.chave +' - '+ o.descricao)) for o in objetos]
    lista_obj.insert(0,('',''))

    form = ObjetoEscolhaForm()

    form.obj.choices = lista_obj 

    if form.validate_on_submit(): 

        if form.replicar.data:
            # atividades do pacto com um mesmo titulo (ocorrências), com situação "Programada" e sem objeto associado
            # junta este grupo com a ocorrência selecionada
            ocorrencias = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                            .outerjoin(Objeto_Atividade_Pacto, Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                            .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == ativ.itemCatalogoId,
                                    Pactos_de_Trabalho_Atividades.pactoTrabalhoId == pacto_id,
                                    Pactos_de_Trabalho_Atividades.situacaoId == 501,
                                    Objeto_Atividade_Pacto.pactoAtividadePlanoObjetoId == None)\
                            .all()\
                            +\
                            db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                            .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == ativ.itemCatalogoId,
                                    Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == pacto_ativ_id)\
                            .all()
        else:
            # ocorrência única selecionda de uma atividade no pacto
            ocorrencias = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                            .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == ativ.itemCatalogoId,
                                    Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == pacto_ativ_id)\
                            .all()

        for ocorrencia in ocorrencias:

            obj_atual = db.session.query(Objeto_Atividade_Pacto)\
                                  .filter(Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == ocorrencia.pactoTrabalhoAtividadeId)\
                                  .first()

            if obj_atual:
                # permite trocar objeto atual, caso ele exista
                obj_atual.planoTrabalhoObjetoId = form.obj.data
            else:
                # cria nova associação da ocorrência ao objeto escolhido 
                obj_ativ_pacto = Objeto_Atividade_Pacto(pactoAtividadePlanoObjetoId = uuid.uuid4(),
                                                        planoTrabalhoObjetoId = form.obj.data,
                                                        pactoTrabalhoAtividadeId = ocorrencia.pactoTrabalhoAtividadeId)

                db.session.add(obj_ativ_pacto)

            db.session.commit()

        if form.replicar.data:
            registra_log_unid(current_user.id,'Objeto relacionado à atividade de pacto de trabalho e demais ocorrências sem objeto prévio.')  
        else:
            registra_log_unid(current_user.id,'Objeto relacionado à uma ocorrência de atividade de pacto de trabalho.')

        return redirect(url_for('demandas.ativ_ocor', pacto_id=pacto_id,item_cat_id=ativ.itemCatalogoId))

    obj_atual = db.session.query(Objetos.chave,
                                 Objetos.descricao)\
                                .join(Objeto_PG, Objeto_PG.objetoId==Objetos.objetoId)\
                                .join(Objeto_Atividade_Pacto,Objeto_Atividade_Pacto.planoTrabalhoObjetoId==Objeto_PG.planoTrabalhoObjetoId)\
                                .filter(Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId == pacto_ativ_id)\
                                .all()
    # if obj_atual:
    #     form.obj.data = obj_atual.planoTrabalhoObjetoId

    return render_template('obj_ativ_pacto.html',form=form, obj_atual=obj_atual)
    

## relacionar objeto com reunião de um pg

@objetos.route('/<plano_id>/<pacto_id>/<reuniao_id>/objeto_reuniao',methods=['GET','POST'])
@login_required
def objeto_reuniao(plano_id,reuniao_id,pacto_id):
    """
    +---------------------------------------------------------------------------------------+
    |Relaciona um objeto a uma reunião.                                                     |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    # pega a unidade do pacto
    pacto = db.session.query(Pactos_de_Trabalho.unidadeId).filter(Pactos_de_Trabalho.pactoTrabalhoId == pacto_id).first()

    # identifica objetos do PG
    objetos = db.session.query(Objetos.chave,
                               Objetos.descricao,
                               Objeto_PG.planoTrabalhoObjetoId)\
                        .join(Objeto_PG, Objeto_PG.objetoId == Objetos.objetoId)\
                        .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Objeto_PG.planoTrabalhoId)\
                        .filter(Planos_de_Trabalho.unidadeId == pacto.unidadeId)\
                        .order_by(Objetos.descricao)\
                        .all()

    # o choices do campo obj são definidos aqui e não no form
    lista_obj = [(o.planoTrabalhoObjetoId,(o.chave +' - '+ o.descricao)) for o in objetos]
    lista_obj.insert(0,('',''))

    form = ObjetoEscolhaForm()

    form.obj.choices = lista_obj 

    if form.validate_on_submit():                   

        reuniao = db.session.query(Planos_de_Trabalho_Reuniao)\
                            .filter(Planos_de_Trabalho_Reuniao.planoTrabalhoReuniaoId==reuniao_id)\
                            .first()

        reuniao.planoTrabalhoObjetoId = form.obj.data

        db.session.commit()        

        registra_log_unid(current_user.id,'Objeto relacionado a uma reunião.')                                 

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('obj_ativ_pacto.html',form=form)    

## histórico de um objeto

@objetos.route('/<objeto_id>/objeto_hist')
@login_required
def objeto_hist(objeto_id):
    """
    +---------------------------------------------------------------------------------------+
    |Mostra o que foi feito (atividades) com um objeto registrado.                          |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """
    
    ativs_objeto = db.session.query(Objetos.chave,
                                    Objetos.descricao,
                                    Pactos_de_Trabalho_Atividades.dataInicio,
                                    Pactos_de_Trabalho_Atividades.dataFim,
                                    Pactos_de_Trabalho_Atividades.consideracoesConclusao,
                                    label('assunto_data',Assuntos.chave),
                                    Assuntos.valor,
                                    Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId,
                                    Pactos_de_Trabalho_Atividades.pactoTrabalhoId,
                                    Unidades.undSigla)\
                             .outerjoin(Objeto_PG, Objeto_PG.objetoId==Objetos.objetoId)\
                             .outerjoin(Objeto_Atividade_Pacto,Objeto_Atividade_Pacto.planoTrabalhoObjetoId==Objeto_PG.planoTrabalhoObjetoId)\
                             .outerjoin(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId==Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId)\
                             .outerjoin(Atividade_Pacto_Assunto, Atividade_Pacto_Assunto.pactoTrabalhoAtividadeId==Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                             .outerjoin(Assuntos, Assuntos.assuntoId==Atividade_Pacto_Assunto.assuntoId)\
                             .outerjoin(Pactos_de_Trabalho,Pactos_de_Trabalho.pactoTrabalhoId==Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                             .outerjoin(Unidades,Unidades.unidadeId==Pactos_de_Trabalho.unidadeId)\
                             .filter(Objetos.objetoId==objeto_id)\
                             .order_by(Pactos_de_Trabalho_Atividades.dataFim)\
                             .all() 
                             
    quantidade = len(ativs_objeto)

    return render_template('objeto_hist.html',ativs_objeto=ativs_objeto,quantidade=quantidade)

