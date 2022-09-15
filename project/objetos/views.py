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
                           Planos_de_Trabalho

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
    objetos = db.session.query(Objetos.descricao,
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

@objetos.route('/<pessoa>/lista_objetos_pessoa')
def lista_objetos_pessoa(pessoa):
    """
    +---------------------------------------------------------------------------------------+
    |Lista conteudo da tabel Objeto para uma determinada Pessoa                             |
    |                                                                                       |
    +---------------------------------------------------------------------------------------+
    """

    # usuário selecionado
    usuario = db.session.query(Pessoas).filter(Pessoas.pessoaId == int(pessoa)).first_or_404()

    # unidade do usuário
    unid = db.session.query(Unidades.undSigla).filter(Unidades.unidadeId == usuario.unidadeId).first()

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
                        .filter(Pactos_de_Trabalho.pessoaId == pessoa)\
                        .all()

    quantidade = len(objetos)


    return render_template('lista_objetos.html', unid_dados=None, objetos=objetos, quantidade=quantidade, pg=None,
                                                 usuario=usuario, unid=unid)


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

        objeto = Objetos(objetoId  = uuid.uuid4(),
                         descricao = form.desc.data,
                         tipo      = form.tipo.data,
                         chave     = form.chave.data,
                         ativo     = form.ativo.data)

        db.session.add(objeto)
        db.session.commit()

        objeto_pg = Objeto_PG(planoTrabalhoObjetoId = uuid.uuid4(),
                              planoTrabalhoId       = plano_id,
                              objetoId              = objeto.objetoId)                 

        db.session.add(objeto_pg)
        db.session.commit()                      

        registra_log_unid(current_user.id,'Objeto '+ objeto.objetoId +' inserido no banco de dados.')

        flash('Objeto registrado!','sucesso')

        if pacto_id == '*':

            return redirect(url_for('objetos.lista_objetos_pg',pg=plano_id))

        else:

            return redirect(url_for('demandas.demanda',pacto_id=pacto_id))


    return render_template('add_objeto.html', form=form, plano_id = plano_id)

## altera objeto

@objetos.route('/<objeto_id>/<plano_id>/altera_objeto',methods=['GET','POST'])
@login_required
def altera_objeto(objeto_id,plano_id):
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
        objeto.tipo      = form.tipo.data
        objeto.chave     = form.chave.data
        objeto.ativo     = form.ativo.data

        db.session.commit()

        registra_log_unid(current_user.id,'Objeto '+ objeto_id +' alterado.')

        flash('Objeto alterado!','sucesso')

        return redirect(url_for('objetos.lista_objetos_pg',pg=plano_id))

    form.desc.data  = objeto.descricao
    form.tipo.data  = objeto.tipo
    form.chave.data = objeto.chave
    form.ativo.data = objeto.ativo    

    return render_template('add_objeto.html', form=form, plano_id=plano_id)    

## relacionar objeto com atividade de um Pacto

@objetos.route('/<plano_id>/<pacto_ativ_id>/<pacto_id>/objeto_ativ_pacto',methods=['GET','POST'])
@login_required
def objeto_ativ_pacto(plano_id,pacto_id,pacto_ativ_id):
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

    ocorrencias = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)\
                           .filter(Pactos_de_Trabalho_Atividades.itemCatalogoId == ativ.itemCatalogoId)\
                           .all()

    # pega objetos do pg
    objetos = db.session.query(Objetos.descricao,
                               Objeto_PG.planoTrabalhoObjetoId)\
                        .join(Objeto_PG, Objeto_PG.objetoId == Objetos.objetoId)\
                        .filter(Objeto_PG.planoTrabalhoId == plano_id)\
                        .all()

    # o choices do campo obj são definidos aqui e não no form
    lista_obj = [(o.planoTrabalhoObjetoId,o.descricao) for o in objetos]
    lista_obj.insert(0,('',''))

    form = ObjetoEscolhaForm()

    form.obj.choices = lista_obj 

    if form.validate_on_submit(): 

        if form.replicar.data:

            for ocorrencia in ocorrencias:

                obj_ativ_pacto = Objeto_Atividade_Pacto(pactoAtividadePlanoObjetoId= uuid.uuid4(),
                                                        planoTrabalhoObjetoId= form.obj.data,
                                                        pactoTrabalhoAtividadeId= ocorrencia.pactoTrabalhoAtividadeId)

                db.session.add(obj_ativ_pacto)
                db.session.commit()

            registra_log_unid(current_user.id,'Objeto relacionado à atividade de pacto de trabalho e todas as demais ocorrências.')  

        else:                  

            obj_ativ_pacto = Objeto_Atividade_Pacto(pactoAtividadePlanoObjetoId= uuid.uuid4(),
                                                    planoTrabalhoObjetoId= form.obj.data,
                                                    pactoTrabalhoAtividadeId= pacto_ativ_id)

            db.session.add(obj_ativ_pacto)
            db.session.commit()                        

            registra_log_unid(current_user.id,'Objeto relacionado à uma ocorrência de atividade de pacto de trabalho.')                

        return redirect(url_for('demandas.demanda',pacto_id=pacto_id))

    return render_template('obj_ativ_pacto.html',form=form)

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

    # identifica objetos do PG
    objetos = db.session.query(Objetos.descricao,
                               Objeto_PG.planoTrabalhoObjetoId)\
                        .join(Objeto_PG, Objeto_PG.objetoId == Objetos.objetoId)\
                        .filter(Objeto_PG.planoTrabalhoId == plano_id)\
                        .all()

    # o choices do campo obj são definidos aqui e não no form
    lista_obj = [(o.planoTrabalhoObjetoId,o.descricao) for o in objetos]
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



