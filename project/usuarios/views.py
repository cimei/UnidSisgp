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
from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from threading import Thread
from datetime import datetime, timedelta, time
from werkzeug.security import generate_password_hash
from sqlalchemy import func, distinct
from sqlalchemy.sql import label

from project import db, mail, app
from project.models import Pactos_de_Trabalho_Atividades, Pactos_de_Trabalho_Solic, users,\
                           Log_Unid, catdom, Pessoas, Unidades, Planos_de_Trabalho,\
                           Pactos_de_Trabalho, Atividade_Candidato, Objeto_Atividade_Pacto, Objeto_PG

from project.usuarios.forms import RegistrationForm, LoginForm, EmailForm, PasswordForm, AdminForm, LogForm
                                

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

# helper function que prepara email de conformação de endereço de e-mail
def send_confirmation_email(user_email):
    """+--------------------------------------------------------------------------------------+
       |Preparação dos dados para e-mail de confirmação de usuário                            |
       +--------------------------------------------------------------------------------------+
    """
    confirm_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    confirm_url = url_for(
        'usuarios.confirm_email',
        token=confirm_serializer.dumps(user_email, salt='email-confirmation-salt'),
        _external=True)

    html = render_template(
        'email_confirmation.html',
        confirm_url=confirm_url)

    send_email('Confirme seu endereço de e-mail', [user_email],'', html)

# helper function que prepara email com token para resetar a senha
def send_password_reset_email(user_email):
    """+--------------------------------------------------------------------------------------+
       |Preparação dos dados para e-mail de troca de senha.                                   |
       +--------------------------------------------------------------------------------------+
    """
    password_reset_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    password_reset_url = url_for(
        'usuarios.reset_with_token',
        token = password_reset_serializer.dumps(user_email, salt='password-reset-salt'),
        _external=True)

    html = render_template(
        'email_senha_atualiza.html',
        password_reset_url=password_reset_url)

    send_email('Atualização de senha solicitada', [user_email],'', html)

# registrar

@usuarios.route('/register', methods=['GET','POST'])
def register():
    """+--------------------------------------------------------------------------------------+
       |Efetua o registro de um usuário. Este recebe o aviso para verificar sua caixa de      |
       |e-mails, pois o aplicativo envia uma mensagem sobre a confirmação do registro.        |
       +--------------------------------------------------------------------------------------+
    """

    form = RegistrationForm()

    if form.validate_on_submit():
        
        if form.check_username(form.username) and form.check_email(form.email) and form.check_sisgp(form.email):

            # primeiro usuário é cadastrado como ativo
            if users.query.count() == 0:
                ativo = True
            else:
                ativo = False

            user = users(userNome                  = form.username.data,
                        userEmail                  = form.email.data,
                        plaintext_password         = form.password.data,
                        email_confirmation_sent_on = datetime.now(),
                        userAtivo                  = ativo)

            db.session.add(user)
            db.session.commit()

            last_id = db.session.query(users.id).order_by(users.id.desc()).first()

            registra_log_unid(last_id[0],'Usuário '+ form.username.data +' registrado.')

            send_confirmation_email(user.userEmail)
            
            flash('Usuário '+ form.username.data +' registrado! Verifique sua caixa de e-mail para confirmar o endereço.','sucesso')
            
            return redirect(url_for('core.index'))

    return render_template('register.html',form=form)

# gera novo link para confirmação de email

@usuarios.route('/<int:userId>/confirm')
def confirm(userId):
    """+--------------------------------------------------------------------------------------+
       |Gera novo link de confirmação de e-mail para usuário novo.                            |
       +--------------------------------------------------------------------------------------+
    """
    user = db.session.query(users.userEmail).filter(users.id == userId).first()

    send_confirmation_email(user.userEmail)

    registra_log_unid(current_user.id,'Novo e-mail de confirmação enviado para '+ user.userEmail +'.')

    flash('Novo e-mail de confirmação enviado para '+ user.userEmail +'.','sucesso')

    return redirect(url_for('usuarios.view_users'))

# confirmar registro

@usuarios.route('/confirm/<token>')
def confirm_email(token):
    """+--------------------------------------------------------------------------------------+
       |Trata o retorno do e-mail de confirmação de registro, verificano se o token enviado   |
       |é válido (igual ao enviado no momento do registro e tem menos de 1 hora de vida).     |
       +--------------------------------------------------------------------------------------+
    """
    try:
        confirm_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        email = confirm_serializer.loads(token, salt='email-confirmation-salt', max_age=3600)
    except:
        flash('O link de confirmação é inválido ou expirou.', 'erro')
        return redirect(url_for('usuarios.login'))

    user = users.query.filter_by(userEmail=email).first()

    if user.email_confirmed:
        flash('Confirmação já realizada. Por favor, faça o login.', 'erro')
    else:
        user.email_confirmed = True
        user.email_confirmed_on = datetime.now()

        db.session.commit()
        flash('Obrigado por confirmar seu endereço de e-mail! Caso já tenha uma janela do sistema aberta, pode fechar a anterior.','sucesso')

    return redirect(url_for('usuarios.login'))

# gera token para resetar senha

@usuarios.route('/reset', methods=["GET", "POST"])
def reset():
    """+--------------------------------------------------------------------------------------+
       |Trata o pedido de troca de senha. Enviando um e-mail para o usuário.                  |
       |O usuário deve estar registrado (com registro confirmado) antes de poder efetuar uma  |
       |troca de senha.                                                                       |
       |O aplicativo envia uma mensagem ao usuário sobre o procedimento de troca de senha.    |
       +--------------------------------------------------------------------------------------+
    """
    form = EmailForm()

    if form.validate_on_submit():
        try:
            user = users.query.filter_by(userEmail=form.email.data).first_or_404()
        except:
            flash('Endereço de e-mail inválido!', 'erro')
            return render_template('email.html', form=form)

        if user.email_confirmed:
            send_password_reset_email(user.userEmail)
            flash('Verifique a caixa de entrada de seu e-mail. Uma mensagem com o link de atualização de senha foi enviado.', 'sucesso')
        else:
            flash('Seu endereço de e-mail precisa ser confirmado antes de tentar efetuar uma troca de senha.', 'erro')
        return redirect(url_for('usuarios.login'))

    return render_template('email.html', form=form)

# trocar ou gerar nova senha

@usuarios.route('/reset/<token>', methods=["GET", "POST"])
def reset_with_token(token):
    """+--------------------------------------------------------------------------------------+
       |Trata o retorno do e-mail enviado ao usuário com token de troca de senha.             |
       |Verifica se o token é válido.                                                         |
       |Abre tela para o usuário informar nova senha.                                         |
       +--------------------------------------------------------------------------------------+
    """
    try:
        password_reset_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        email = password_reset_serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('O link de atualização de senha é inválido ou expirou.', 'erro')
        return redirect(url_for('usuarios.login'))

    form = PasswordForm()

    if form.validate_on_submit():
        try:
            user = users.query.filter_by(userEmail=email).first_or_404()
        except:
            flash('Endereço de e-mail inválido!', 'erro')
            return redirect(url_for('usuarios.login'))

        user.password_hash = generate_password_hash(form.password.data)

        db.session.commit()

        registra_log_unid(user.id,'Senha alterada.')

        flash('Sua senha foi atualizada!', 'sucesso')

        return redirect(url_for('usuarios.login'))

    return render_template('troca_senha_com_token.html', form=form, token=token)


# login

@usuarios.route('/login', methods=['GET','POST'])
def login():
    """+--------------------------------------------------------------------------------------+
       |Fornece a tela para que o usuário entre no sistema (login).                           |
       |O acesso é feito por e-mail e senha cadastrados.                                      |
       |Antes do primeiro acesso após o registro, o usuário precisa cofirmar este registro    |
       |para poder fazer o login, conforme mensagem enviada.                                  |
       +--------------------------------------------------------------------------------------+
    """
    form = LoginForm()

    if form.validate_on_submit():

        user = users.query.filter_by(userEmail=form.email.data).first()

        if user is not None:

            if user.check_password(form.password.data):

                if user.email_confirmed:

                    user.last_logged_in = user.current_logged_in
                    user.current_logged_in = datetime.now()
                    db.session.commit()

                    login_user(user)

                    flash('Login bem sucedido!','sucesso')

                    next = request.args.get('next')

                    if next == None or not next[0] == '/':
                        next = url_for('core.index')

                    return redirect(next)

                else:
                    flash('Endereço de e-mail não confirmado ainda!','erro')

            else:
                flash('Senha não confere, favor verificar!','erro')

        else:
            flash('E-mail informado não encontrado, favor verificar!','erro')

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
       |Mostra lista dos usuários da unidade do usuároi logado.                               |
       +--------------------------------------------------------------------------------------+
    """

    # pega unidadeId e pessoaId do usuário
    user_pes = db.session.query(Pessoas.unidadeId, Pessoas.pessoaId).filter(Pessoas.pesEmail == current_user.userEmail).first()

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
                      .filter(pessoas_sub.c.unidadeId == user_pes.unidadeId)\
                      .order_by(users.userNome).all()

    logado = db.session.query(Pessoas.tipoFuncaoId).filter(Pessoas.pesEmail == current_user.userEmail).first()

    return render_template('view_users.html', lista=lista, logado=logado)

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
@usuarios.route("/seus_numeros/<id>")
def seus_numeros(id):
    """+--------------------------------------------------------------------------------------+
       |Alguns números do usuário.                                                            |
       |                                                                                      |
       +--------------------------------------------------------------------------------------+
    """
    lista = 'pessoa'

    if id == '*':

        #pega e-mail do usuário logado
        email = current_user.userEmail

        #pega id sisgp do usuário logado
        usuario = db.session.query(Pessoas).filter(Pessoas.pesEmail == email).first_or_404()
        
    else:
        #pega id sisgp do usuário informado
        usuario = db.session.query(Pessoas).filter(Pessoas.pessoaId == int(id)).first_or_404()

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
    
    return render_template('numeros.html', pes_nome=usuario.pesNome,
                                           pes_id=usuario.pessoaId,
                                           programas_de_gestao=programas_de_gestao,
                                           candidaturas=candidaturas,
                                           planos_de_trabalho_fs=planos_de_trabalho_fs,
                                           solicit=solicit,
                                           ativs=ativs,
                                           objetos=objetos,
                                           unid=unid,
                                           id = id,
                                           lista = lista)

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

