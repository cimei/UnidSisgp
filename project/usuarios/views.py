"""
.. topic:: users (views)

    users são as pessoas que podem acessar o ApoioSisgp.

    O registro é feito por meio da respectiva opção no menu do aplicativo, com o preenchimento dos dados
    básicos do usuário. Este registro precisa ser confirmado com o token enviado pelo sistema, por e-mail,
    ao usúario.

    Para entrar no aplicativo, o usuário se idenfica com seu e-mail e informa sua senha pessoal.

    Para alterar sua senha, seja por motivo de esquecimento, ou simplemente porque quer alterá-la, 
    o procedimento envolve o envio de um e-mail do sistema para seu endereço de e-mail registrado, 
    com o token que abre uma tela para registro de nova senha. Este token tem validade de uma hora.

.. topic:: Ações relacionadas aos usuários:

    * Funções auxiliares:
        * Envia e-mail de forma assincrona: send_async_email
        * Prepara e-mail: send_email
        * Dados para e-mail de confirmação: send_confirmation_email
        * Dados para e-mail de troca de senha: send_password_reset_email
    * Registro de usuário: register
    * Trata retorno da confirmação: confirm_email
    * Trata pedido de troca de senha: reset
    * Realiza troca de senha: reset_with_token
    * Entrada de usuário: login
    * Saída de usuário: logout
    * Atualizar dados do usuário: account
    * Visão dos usuários: view_users
    * Log de atividades: user_log
    * Registro de observações do usuário no log: user_obs
    * Ver lista de usuários ativos da coordenação: coord_view_users

"""
# views.py na pasta users

from itsdangerous import URLSafeTimedSerializer
from flask import render_template, url_for, flash, redirect, request, Blueprint, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from threading import Thread
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from sqlalchemy import func, distinct, literal
from sqlalchemy.sql import label
import time
import uuid

from project import db, mail, app
from project.models import Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Solic, users,\
                           Log_Unid, catdom, Pessoas, Unidades, Planos_de_Trabalho,\
                           Pactos_de_Trabalho, Atividade_Candidato, Objeto_Atividade_Pacto, Objeto_PG, Log_Unid,\
                           AgendamentoPresencial

from project.usuarios.forms import RegistrationForm, LoginForm, EmailForm, PasswordForm, AdminForm, LogForm, AgendaForm
                                

usuarios = Blueprint('usuarios',__name__)


# função para registrar comits no log
def registra_log_unid(user_id,msg):
    """
    +---------------------------------------------------------------------------------------+
    |Função que registra ação do usuário na tabela log_unid.                                |
    |INPUT: user_id e msg                                                                   |
    +---------------------------------------------------------------------------------------+
    """

    reg_log = Log_Unid(data_hora  = datetime.now(),
                       user_id    = user_id,
                       msg        = msg)

    db.session.add(reg_log)

    db.session.commit()

    return

# helper function para envio de email em outra thread
def send_async_email(msg):
    """+--------------------------------------------------------------------------------------+
       |Executa o envio de e-mails de forma assíncrona.                                       |
       +--------------------------------------------------------------------------------------+
    """
    with app.app_context():
        mail.send(msg)

# helper function para enviar e-mail
def send_email(subject, recipients, text_body, html_body):
    """+--------------------------------------------------------------------------------------+
       |Envia e-mails.                                                                        |
       +--------------------------------------------------------------------------------------+
    """
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    thr = Thread(target=send_async_email, args=[msg])
    thr.start()

# login

@usuarios.route('/login', methods=['GET','POST'])
def login():
    """+--------------------------------------------------------------------------------------+
       |Fornece a tela para que o usuário entre no sistema (login).                           |
       |O acesso é feito por usuário e senha cadastrados, conforme ldap.                      |
       +--------------------------------------------------------------------------------------+
    """

    if current_user.is_authenticated:
        flash('Você já estava logado!')
        return redirect(url_for('core.inicio'))

    form = LoginForm()

    if form.validate_on_submit():

        username = form.username.data
        password = form.password.data

        try:
            conexao = users.conecta_ldap(username,password,'ou=People,dc=cnpq,dc=br')
        except:
            flash('Problema no acesso. Por favor, verifique suas credenciais e tente novamente.', 'erro')
            return render_template('login.html', form=form)

        if conexao == 'sem_credencial':
            retorno = False
            ldap_mail = None
            ldap_cpf  = None
            flash('Usuário desconhecido ou senha inválida. Por favor, tente novamente.', 'erro')
            return render_template('login.html', form=form)
        else:
            conexao.search('dc=cnpq,dc=br', '(uid='+username+')', attributes=['mail','carLicense'])
            retorno = True
            ldap_mail = str((conexao.entries[0])['mail'])
            ldap_cpf  = str((conexao.entries[0])['carLicense'])
            pessoa = Pessoas.query.filter_by(pesEmail = ldap_mail).first()
            if not pessoa:
                flash('Seu e-mail no PGD ('+pessoa.pesEmail+') não bate com sei e-mail no LDAP ('+ldap_mail+'). Acesso negado!','erro')
                return render_template('login.html', form=form)
        
        user = users.query.filter_by(userEmail = ldap_mail).first()

        if not user:
            user = users(userNome                   = pessoa.pesNome,
                         userEmail                  = pessoa.pesEmail,
                         plaintext_password         = 'sem_senha',
                         email_confirmation_sent_on = datetime.now(),
                         userAtivo                  = True,
                         avaliadorId                = None)
            db.session.add(user)
            db.session.commit()

        user.last_logged_in = user.current_logged_in
        user.current_logged_in = datetime.now()
        db.session.commit()

        login_user(user)

        flash('Login bem sucedido!','sucesso')

        next = request.args.get('next')

        if next == None or not next[0] == '/':
            next = url_for('core.inicio')

        return redirect(next)

    return render_template('login.html',form=form)

# logout

@usuarios.route('/logout')
def logout():
    """+--------------------------------------------------------------------------------------+
       |Efetua a saída do usuário do sistema.                                                 |
       +--------------------------------------------------------------------------------------+
    """
    logout_user()
    return redirect(url_for("core.index"))


# Lista dos usuários

@usuarios.route('/view_users')
@login_required

def view_users():
    """+--------------------------------------------------------------------------------------+
       |Mostra lista dos usuários da unidade do usuário logado.                               |
       +--------------------------------------------------------------------------------------+
    """

    pessoas_sub = db.session.query(Pessoas).subquery()

    lista = db.session.query(users.id,
                             users.userNome,
                             users.userEmail,
                             pessoas_sub.c.unidadeId,
                             users.registered_on,
                             users.email_confirmed,
                             users.email_confirmed_on,
                             users.current_logged_in,
                             users.userAtivo,
                             users.avaliadorId,
                             label('avalNome',Pessoas.pesNome),
                             label('avalUnid',Pessoas.unidadeId))\
                      .outerjoin(Pessoas, Pessoas.pessoaId == users.avaliadorId)\
                      .outerjoin(pessoas_sub, pessoas_sub.c.pesEmail == users.userEmail)\
                      .order_by(users.userNome).all()

    return render_template('view_users.html', lista=lista)

#
## alterações em users 

@usuarios.route("/<int:user_id>/update_user", methods=['GET', 'POST'])
@login_required
def update_user(user_id):
    """
    +----------------------------------------------------------------------------------------------+
    |Permite ao admin atualizar dados de um user.                                                  |
    |                                                                                              |
    |Recebe o id do user como parâmetro.                                                           |
    +----------------------------------------------------------------------------------------------+
    """
    # pega usuário 
    user = users.query.get_or_404(user_id)

    # pega unidadeId e pessoaId do usuário
    user_pes = db.session.query(Pessoas.unidadeId, Pessoas.pessoaId).filter(Pessoas.pesEmail == user.userEmail).first()

    # pega pessoas da unidade do usuário
    pessoas = db.session.query(Pessoas.pessoaId, Pessoas.pesNome)\
                        .filter(Pessoas.unidadeId == user_pes.unidadeId,
                                Pessoas.pessoaId != user_pes.pessoaId)\
                        .all()

    # o choices do campo atividade são definidos aqui e não no form
    lista_avalia = [(p.pessoaId,p.pesNome) for p in pessoas]
    lista_avalia.insert(0,('99999','RH'))
    lista_avalia.insert(0,('',''))                    

    form = AdminForm()

    form.avaliador.choices = lista_avalia

    if form.validate_on_submit():

        if current_user.userAtivo:

            user.userAtivo   = form.ativo.data
            user.avaliadorId = form.avaliador.data

            db.session.commit()

            registra_log_unid(current_user.id,'Usuário '+ user.userNome +' atualizado.')

            flash('Usuário '+ user.userNome +' atualizado!','sucesso')

            return redirect(url_for('usuarios.view_users'))

        else:

            flash('O seu usuário precisa ser ativado para esta operação!','erro')

            return redirect(url_for('usuarios.view_users'))


    # traz a informação atual do usuário
    elif request.method == 'GET':

        form.ativo.data     = user.userAtivo
        form.avaliador.data = str(user.avaliadorId)

    return render_template('update_user.html', title='Update', name=user.userNome,
                            form=form)

#
# mostra log

@usuarios.route("/log", methods=['GET', 'POST'])
@login_required
def log ():
    """+--------------------------------------------------------------------------------------+
       |Mostra a atividade no sistema em função dos principais commits.                       |
       |                                                                                      |
       +--------------------------------------------------------------------------------------+
    """

    form = LogForm()

    if form.validate_on_submit():

        data_ini = form.data_ini.data
        data_fim = form.data_fim.data

        log = db.session.query(Log_Unid.id,
                               Log_Unid.data_hora,
                               users.userNome,
                               Log_Unid.msg)\
                        .outerjoin(users, Log_Unid.user_id == users.id)\
                        .filter(Log_Unid.data_hora >= datetime.combine(data_ini,time.min),
                                Log_Unid.data_hora <= datetime.combine(data_fim,time.max))\
                        .order_by(Log_Unid.id.desc())\
                        .all()

        return render_template('user_log.html', log=log, name=current_user.userNome,
                               form=form)


    # traz a log das últimas 24 horas e registra entrada manual de log, se for o caso.
    else:

        log = db.session.query(Log_Unid.id,
                               Log_Unid.data_hora,
                               users.userNome,
                               Log_Unid.msg)\
                        .join(users, Log_Unid.user_id == users.id)\
                        .filter(Log_Unid.data_hora >= (datetime.now()-timedelta(days=1)))\
                        .order_by(Log_Unid.id.desc())\
                        .all()

        return render_template('user_log.html', log=log, name=current_user.userNome,
                           form=form)

#
# numeros do usuario
#
@usuarios.route("/seus_numeros/<pessoa_id>")
def seus_numeros(pessoa_id):
    """+--------------------------------------------------------------------------------------+
       |Alguns números do usuário.                                                            |
       |                                                                                      |
       +--------------------------------------------------------------------------------------+
    """
    lista = 'pessoa'

    if pessoa_id == '*':

        #pega e-mail do usuário logado
        email = current_user.userEmail
        user_id = current_user.id

        #pega id sisgp do usuário logado
        usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first_or_404()
        
    else:
        #pega id sisgp do usuário informado
        usuario = db.session.query(Pessoas).filter(Pessoas.pessoaId == int(pessoa_id)).first_or_404()
        user_id = db.session.query(users.id).filter(users.userEmail==usuario.pesEmail).first()

    # unidade do usuário
    unid = db.session.query(Unidades.undSigla).filter(Unidades.unidadeId == usuario.unidadeId).first()

    catdom_sit = db.session.query(catdom).subquery()

    # quantidade de programas de gestão da unidade
    programas_de_gestao = db.session.query(catdom.descricao, 
                                            label('qtd_pg',func.count(Planos_de_Trabalho.planoTrabalhoId)))\
                                        .join(catdom,catdom.catalogoDominioId == Planos_de_Trabalho.situacaoId)\
                                        .filter(Planos_de_Trabalho.unidadeId == usuario.unidadeId)\
                                        .group_by(catdom.descricao)\
                                        .all()

    # quantidade de objetos distintos nas atividade do usuário
    objetos = db.session.query(distinct(Objeto_PG.objetoId))\
                        .join(Objeto_Atividade_Pacto, Objeto_Atividade_Pacto.planoTrabalhoObjetoId == Objeto_PG.planoTrabalhoObjetoId)\
                        .join(Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId == Objeto_Atividade_Pacto.pactoTrabalhoAtividadeId)\
                        .join(Pactos_de_Trabalho, Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                        .filter(Pactos_de_Trabalho.pessoaId == usuario.pessoaId)\
                        .count()    
                                   
    
    # quantidade de candidaturas do usuário
    candidaturas = db.session.query(catdom.descricao, 
                                    label('qtd_cand',func.count(Atividade_Candidato.planoTrabalhoAtividadeCandidatoId)))\
                              .join(catdom,catdom.catalogoDominioId == Atividade_Candidato.situacaoId)\
                              .filter(Atividade_Candidato.pessoaId == usuario.pessoaId)\
                              .group_by(catdom.descricao)\
                              .all()

    # quantidades de planos de trabalho por forma e situação
    planos_de_trabalho_fs = db.session.query(label('forma',catdom.descricao),
                                             label('sit',catdom_sit.c.descricao),   
                                             label('qtd_planos',func.count(Pactos_de_Trabalho.pactoTrabalhoId)),
                                             Pactos_de_Trabalho.formaExecucaoId,
                                             Pactos_de_Trabalho.situacaoId)\
                                    .join(catdom,catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                                    .join(catdom_sit,catdom_sit.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                    .filter(Pactos_de_Trabalho.pessoaId == usuario.pessoaId)\
                                    .group_by(Pactos_de_Trabalho.formaExecucaoId,Pactos_de_Trabalho.situacaoId,
                                              catdom.descricao,catdom_sit.c.descricao)\
                                    .order_by(Pactos_de_Trabalho.formaExecucaoId,Pactos_de_Trabalho.situacaoId)\
                                    .all()                                                                                        

    # quantidades de solicitações
    solicit = db.session.query(Pactos_de_Trabalho_Solic.analisado,
                               Pactos_de_Trabalho_Solic.aprovado,
                               catdom.descricao,
                               label('qtd_solic',func.count(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId)))\
                        .join(Pactos_de_Trabalho,Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Solic.pactoTrabalhoId)\
                        .join(catdom,catdom.catalogoDominioId == Pactos_de_Trabalho_Solic.tipoSolicitacaoId)\
                        .filter(Pactos_de_Trabalho.pessoaId == usuario.pessoaId)\
                        .group_by(Pactos_de_Trabalho_Solic.analisado,Pactos_de_Trabalho_Solic.aprovado,catdom.descricao)\
                        .order_by(Pactos_de_Trabalho_Solic.analisado,Pactos_de_Trabalho_Solic.aprovado,catdom.descricao)\
                        .all()
                        
    # quantidades de atividades em planos (pactos)
    ativs = db.session.query(catdom.descricao, 
                             label('qtd_ativs',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)))\
                      .join(Pactos_de_Trabalho,Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                      .join(catdom,catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                      .filter(Pactos_de_Trabalho.pessoaId == usuario.pessoaId)\
                      .group_by(catdom.descricao)\
                      .all()

    # medindo o comprometimento do usuário (icp) por meio do registro de início de ocorrências das atividades
    plano_em_exec = db.session.query(Pactos_de_Trabalho.pactoTrabalhoId,
                                     Pactos_de_Trabalho.dataFim,
                                     Pactos_de_Trabalho.dataInicio)\
                              .filter(Pactos_de_Trabalho.situacaoId==405,
                                      Pactos_de_Trabalho.pessoaId == usuario.pessoaId)\
                              .first()

    if plano_em_exec:
        ativs_plano_em_exec = db.session.query(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId,
                                               Pactos_de_Trabalho_Atividades.dataInicio)\
                                .filter(Pactos_de_Trabalho_Atividades.pactoTrabalhoId == plano_em_exec.pactoTrabalhoId).all()
        log_plano = db.session.query(Log_Unid.msg, Log_Unid.data_hora)\
                          .filter(Log_Unid.msg.like('Atividade%'),
                                  Log_Unid.msg.like('% colocada em execução.'),
                                  Log_Unid.user_id == user_id,
                                  Log_Unid.data_hora > plano_em_exec.dataInicio).all()                        
    
        # iri é o índice de registro de início de atividade
        # iri próximo de 1: registro de início de atividade próximo do início do plano
        # iri próximo de 0: registro de início de atividade próxomo ao final do plano
        iris = []
        reg_log = 0
        if log_plano:
            for l in log_plano:
                if l.msg[11:47] in [a.pactoTrabalhoAtividadeId for a in ativs_plano_em_exec]:
                    reg_log += 1
                    dif_data_plano = (plano_em_exec.dataFim - plano_em_exec.dataInicio).days
                    if not(plano_em_exec.dataFim - l.data_hora.date()) or (plano_em_exec.dataFim - l.data_hora.date()) == 0:
                        dif_data_reg = 0
                    elif plano_em_exec.dataFim < l.data_hora.date():
                        dif_data_reg = -1    
                    else:    
                        dif_data_reg = (plano_em_exec.dataFim - l.data_hora.date()).days
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
                peso = reg_log/len(ativs_plano_em_exec)       
                icp = round(peso*(sum(iris)/len(iris)),2)
            else:
                icp = 0
        else:
            icp = 0
    else:
        icp = 0                     


    return render_template('numeros.html', pes_nome=usuario.pesNome,
                                           pes_id=usuario.pessoaId,
                                           programas_de_gestao=programas_de_gestao,
                                           candidaturas=candidaturas,
                                           planos_de_trabalho_fs=planos_de_trabalho_fs,
                                           solicit=solicit,
                                           ativs=ativs,
                                           objetos=objetos,
                                           unid=unid,
                                           lista = lista,
                                           icp = icp)

#
# números da unidade
#
@usuarios.route("/unidade_numeros/<id>")
def unidade_numeros(id):
    """+--------------------------------------------------------------------------------------+
       |Alguns números da unidade.                                                            |
       |                                                                                      |
       +--------------------------------------------------------------------------------------+
    """
    lista = 'unidade'

    if id == '*':

        #pega e-mail do usuário logado
        email = current_user.userEmail

        #pega id sisgp do usuário logado
        usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first_or_404()

        # unidade do usuário
        unid = db.session.query(Unidades).filter(Unidades.unidadeId == usuario.unidadeId).first()
        
    else:
        #dados da unidade selecionada
        unid = db.session.query(Unidades).filter(Unidades.undSigla == id).first()

    catdom_sit = db.session.query(catdom).subquery()

    # quantidade de programas de gestão da unidade
    programas_de_gestao = db.session.query(catdom.descricao, 
                                            label('qtd_pg',func.count(Planos_de_Trabalho.planoTrabalhoId)))\
                                        .join(catdom,catdom.catalogoDominioId == Planos_de_Trabalho.situacaoId)\
                                        .filter(Planos_de_Trabalho.unidadeId == unid.unidadeId)\
                                        .group_by(catdom.descricao)\
                                        .all()

    # quantidade de objetos nas atividade do usuário
    objetos = db.session.query(Objeto_PG.objetoId)\
                        .join(Planos_de_Trabalho, Planos_de_Trabalho.planoTrabalhoId == Objeto_PG.planoTrabalhoId)\
                        .filter(Planos_de_Trabalho.unidadeId == unid.unidadeId)\
                        .count()    
    
    # quantidade de candidaturas do usuário
    candidaturas = db.session.query(catdom.descricao, 
                                    label('qtd_cand',func.count(Atividade_Candidato.planoTrabalhoAtividadeCandidatoId)))\
                              .join(catdom,catdom.catalogoDominioId == Atividade_Candidato.situacaoId)\
                              .join(Pessoas,Pessoas.pessoaId == Atividade_Candidato.pessoaId)\
                              .join(Unidades, Unidades.unidadeId == Pessoas.unidadeId)\
                              .filter(Unidades.unidadeId == unid.unidadeId)\
                              .group_by(catdom.descricao)\
                              .all()

    # quantidades de planos de trabalho por forma e situação
    planos_de_trabalho_fs = db.session.query(label('forma',catdom.descricao),
                                             label('sit',catdom_sit.c.descricao),   
                                             label('qtd_planos',func.count(Pactos_de_Trabalho.pactoTrabalhoId)),
                                             Pactos_de_Trabalho.formaExecucaoId,
                                             Pactos_de_Trabalho.situacaoId)\
                                    .join(catdom,catdom.catalogoDominioId == Pactos_de_Trabalho.formaExecucaoId)\
                                    .join(catdom_sit,catdom_sit.c.catalogoDominioId == Pactos_de_Trabalho.situacaoId)\
                                    .filter(Pactos_de_Trabalho.unidadeId == unid.unidadeId)\
                                    .group_by(Pactos_de_Trabalho.formaExecucaoId,Pactos_de_Trabalho.situacaoId,
                                              catdom.descricao,catdom_sit.c.descricao)\
                                    .order_by(Pactos_de_Trabalho.formaExecucaoId,Pactos_de_Trabalho.situacaoId)\
                                    .all()                                                                                        

    # quantidades de solicitações
    solicit = db.session.query(Pactos_de_Trabalho_Solic.analisado,
                               Pactos_de_Trabalho_Solic.aprovado,
                               catdom.descricao,
                               label('qtd_solic',func.count(Pactos_de_Trabalho_Solic.pactoTrabalhoSolicitacaoId)))\
                        .join(Pactos_de_Trabalho,Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Solic.pactoTrabalhoId)\
                        .join(catdom,catdom.catalogoDominioId == Pactos_de_Trabalho_Solic.tipoSolicitacaoId)\
                        .filter(Pactos_de_Trabalho.unidadeId == unid.unidadeId)\
                        .group_by(Pactos_de_Trabalho_Solic.analisado,Pactos_de_Trabalho_Solic.aprovado,catdom.descricao)\
                        .order_by(Pactos_de_Trabalho_Solic.analisado,Pactos_de_Trabalho_Solic.aprovado,catdom.descricao)\
                        .all()
                        
    # quantidades de atividades em planos (pactos)
    ativs = db.session.query(catdom.descricao, 
                             label('qtd_ativs',func.count(Pactos_de_Trabalho_Atividades.pactoTrabalhoAtividadeId)))\
                      .join(Pactos_de_Trabalho,Pactos_de_Trabalho.pactoTrabalhoId == Pactos_de_Trabalho_Atividades.pactoTrabalhoId)\
                      .join(catdom,catdom.catalogoDominioId == Pactos_de_Trabalho_Atividades.situacaoId)\
                      .filter(Pactos_de_Trabalho.unidadeId == unid.unidadeId)\
                      .group_by(catdom.descricao)\
                      .all()
    
    return render_template('numeros.html', pes_nome='',
                                           pes_id=0,
                                           programas_de_gestao=programas_de_gestao,
                                           candidaturas=candidaturas,
                                           planos_de_trabalho_fs=planos_de_trabalho_fs,
                                           solicit=solicit,
                                           ativs=ativs,
                                           objetos=objetos,
                                           unid=unid,
                                           id = id,
                                           lista = lista)

# calendário de presença

@usuarios.route('/calendario')
@login_required

def calendario():
    """+--------------------------------------------------------------------------------------+
       |Prepara calendário com pessoas presentes na unidade conforme o agendamento.           |
       +--------------------------------------------------------------------------------------+
    """

    # pega unidadeId e pessoaId do usuário
    user_pes = db.session.query(Pessoas.unidadeId, Pessoas.pessoaId).filter(Pessoas.pesEmail == current_user.userEmail).first()

    # pega pessoas com agenda da unidade do usuário
    pessoas_orig = db.session.query(label('id',AgendamentoPresencial.agendamentoPresencialId),
                               label('title',Pessoas.pesNome),
                               label('data',AgendamentoPresencial.dataAgendada))\
                        .join(AgendamentoPresencial, AgendamentoPresencial.pessoaId == Pessoas.pessoaId)\
                        .filter(Pessoas.unidadeId == user_pes.unidadeId)\
                        .order_by(Pessoas.pesNome)\
                        .all()

    nomes = set([p.title for p in pessoas_orig])
    list_classes = ['event-important','event-warning','event-info','event-inverse','event-success','event-specioal','event-error']
    nome_classe = {}
    i = 0
    for n in nomes:
        nome_classe[n] = list_classes[i]
        i += 1
        if i == len(list_classes):
            i = 0

    pessoas_list = []
    for p in pessoas_orig:
        pessoas_dic = {}
        pessoas_dic['id']    = p.id
        pessoas_dic['title'] = p.title
        pessoas_dic['url']   = 'agenda_remove/'+p.id
        pessoas_dic['class'] = nome_classe[p.title]
        pessoas_dic['start'] = int(time.mktime(p.data.timetuple()))*1000
        pessoas_dic['end']   = int(time.mktime(p.data.timetuple()))*1000
        pessoas_list.append(pessoas_dic)

    resp = jsonify({'success' : 1, 'result' : pessoas_list})
    resp.status_code = 200

    #return render_template('calendario.html', resp=resp)
    return resp

#
# chama calendário de presença

@usuarios.route('/mostra_calendario')
@login_required

def mostra_calendario():
    """+--------------------------------------------------------------------------------------+
       |Mostra calendário com pessoas presentes na unidade conforme o agendamento.            |
       +--------------------------------------------------------------------------------------+
    """

    return render_template('calendario.html')

## agendamento de presença 

@usuarios.route("/agenda_presenca", methods=['GET', 'POST'])
@login_required
def agenda_presenca():
    """
    +----------------------------------------------------------------------------------------------+
    |Cria agendamento presencial para pessoa da unidade.                                           |
    |                                                                                              |
    +----------------------------------------------------------------------------------------------+
    """

    # pega unidadeId e pessoaId do usuário logado
    user_pes = db.session.query(Pessoas.unidadeId, Pessoas.pessoaId).filter(Pessoas.pesEmail == current_user.userEmail).first()

    # pega pessoas da unidade do usuário
    pessoas = db.session.query(Pessoas.pessoaId, Pessoas.pesNome)\
                        .filter(Pessoas.unidadeId == user_pes.unidadeId)\
                        .all()

    # o choices do campo atividade são definidos aqui e não no form
    lista_pes = [(p.pessoaId,p.pesNome) for p in pessoas]
    lista_pes.insert(0,('',''))                    

    form = AgendaForm()

    form.pessoa.choices = lista_pes

    if form.validate_on_submit():

        if current_user.userAtivo:

            nome_pessoa =  db.session.query(Pessoas.pesNome)\
                                     .filter(Pessoas.pessoaId == form.pessoa.data)\
                                     .first()

            ver_previa = db.session.query(AgendamentoPresencial)\
                                   .filter(AgendamentoPresencial.pessoaId == form.pessoa.data,
                                           AgendamentoPresencial.dataAgendada == form.data_agenda.data)\
                                   .first()

            if ver_previa:
                flash('Pessoa '+ nome_pessoa.pesNome +' já estava agendada para a data informada.','perigo')
                return redirect(url_for('usuarios.mostra_calendario'))
            else:    
                agendamento = AgendamentoPresencial(agendamentoPresencialId = uuid.uuid4(),
                                                    pessoaId                = form.pessoa.data,
                                                    dataAgendada            = form.data_agenda.data)
                db.session.add(agendamento)
                db.session.commit()

            registra_log_unid(current_user.id,'Pessoa '+ nome_pessoa.pesNome +' agendada para trabalho presencial.')

            flash('Pessoa '+ nome_pessoa.pesNome +' agendada para trabalho presencial.','sucesso')

            return redirect(url_for('usuarios.mostra_calendario'))

        else:

            flash('O seu usuário precisa ser ativado para esta operação!','erro')

            return redirect(url_for('usuarios.mostra_calendário'))


    return render_template('agenda_presenca.html',form=form)

#    
## remoção de agendamento de presença 

@usuarios.route("/agenda_remove/<id>")
@login_required
def agenda_remove(id):
    """
    +----------------------------------------------------------------------------------------------+
    |Remove agendamento presencial para pessoa da unidade.                                         |
    |                                                                                              |
    +----------------------------------------------------------------------------------------------+
    """

    agendamento = db.session.query(AgendamentoPresencial).filter(AgendamentoPresencial.agendamentoPresencialId==id).first()

    pessoa = db.session.query(Pessoas.pesNome).filter(Pessoas.pessoaId==agendamento.pessoaId).first()

    db.session.delete(agendamento)
    db.session.commit()

    registra_log_unid(current_user.id,'Um agendamento presencial de '+ pessoa.pesNome +' foi removido.')

    flash('Um agendamento presencial de '+ pessoa.pesNome +' foi removido.','sucesso')

    return redirect(url_for('usuarios.mostra_calendario'))