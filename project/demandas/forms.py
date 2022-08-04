"""
.. topic:: **Demandas (formulários)**

    Os formulários do módulo *Demandas* recebem dados informados pelo usuário para
    registro, atualização, procura e deleção de demandas.

    Uma demanda, após criada, só pode ser alterda e removida pelo seu autor.

    Para o tratamento de demandas, foram definidos 4 formulários:

    * Plano_TrabalhoForm: iserir ou alterar atividade no plano de trabalho.
    * Tipos_DemandaForm: criação ou atualização de tipos de demanda.
    * Passos_Tipos_Form: criação de passos para tipos de demanda.
    * Admin_Altera_Demanda_Form: admin altera data de conclusão de uma demanda.
    * DemandaForm1: triagem antes da criação de uma demanda.
    * DemandaForm: criação ou atualização de uma demanda.
    * Demanda_ATU_Form: atualizar demanda.
    * TransferDemandaForm: passar demanda para outra pessoa.
    * DespachoForm: criação de um despacho relativo a uma demanda existente.
    * ProvidenciaForm: criação de uma providência relativa a uma demanda existente.
    * PesquisaForm: localizar demandas conforme os campos informados.
    * PesosForm: atribuição de pesos para os critérios de priorização de demandas.
    * Afere_Demanda_Form: atribuir nota a uma demanda
    * Pdf_Demanda_Form: para gerar pdf da demanda em tela
    * CoordForm: escolher uma coordeação específica


**Campos definidos em cada formulário de *Demandas*:**

"""

# forms.py na pasta demandas

import datetime
from email.policy import default
from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SelectField, BooleanField, DecimalField,\
                    TextAreaField, SubmitField, RadioField
from wtforms.fields.html5 import DateField, DateTimeField                    
from wtforms.validators import DataRequired, Regexp, Optional
from project import db
from project.models import catdom


class PreSolicitacaoForm(FlaskForm):

    tipos = db.session.query(catdom.catalogoDominioId, catdom.descricao)\
                      .filter(catdom.classificacao == 'TipoSolicitacaoPactoTrabalho')\
                      .order_by(catdom.descricao).all()
    lista_tipos = [(t[0],t[1]) for t in tipos]
    lista_tipos.insert(0,('',''))

    tipo        = SelectField('Tipo de solicitação:',choices= lista_tipos)

    submit      = SubmitField('Verificar')

class SolicitacaoForm601(FlaskForm):

    tipos = db.session.query(catdom.catalogoDominioId, catdom.descricao)\
                      .filter(catdom.classificacao == 'SituacaoAtividadePactoTrabalho')\
                      .order_by(catdom.descricao).all()
    lista_tipos = [(t[0],t[1]) for t in tipos]
    lista_tipos.insert(0,('',''))

    quantidade = IntegerField('Quantidade:',default=1,validators=[DataRequired(message="Informe a quantidade!")])
    atividade  = SelectField('Atividade:')
    remoto     = BooleanField('Execução remota?')
    situacao   = SelectField('Situação:',choices= lista_tipos)
    data_ini   = DateField('Data de início:',format='%Y-%m-%d', validators=(Optional(),))
    data_fim   = DateField('Data de término:',format='%Y-%m-%d', validators=(Optional(),))
    tempo_real = StringField('Tempo realizado:')
    desc       = TextAreaField('Observações:',validators=[DataRequired(message="Insira observações!")])

    submit     = SubmitField('Registrar')

class SolicitacaoForm602(FlaskForm):

    data_fim   = DateField('Data de término:',format='%Y-%m-%d')
    desc       = TextAreaField('Observações:',validators=[DataRequired(message="Insira observações!")])

    submit     = SubmitField('Registrar')

class SolicitacaoForm603(FlaskForm):

    atividade  = SelectField('Atividade:')
    desc       = TextAreaField('Justificativa:',validators=[DataRequired(message="Insira justificativa!")])

    submit     = SubmitField('Registrar')   


class SolicitacaoAnaliseForm(FlaskForm):

    aprovado    = RadioField("Aprovado?", choices=[(1,'Sim'),(0,'Não')],validators=[DataRequired(message="Escolha uma opção!")])
    observacoes = TextAreaField('Observações:',validators=[DataRequired(message="Insira observações!")])

    submit       = SubmitField('Registrar')

class InciaConcluiAtivForm(FlaskForm):

    data_ini        = DateField('Data', format='%Y-%m-%d', validators=(Optional(),))
    data_fim        = DateField('Data', format='%Y-%m-%d', validators=(Optional(),))
    consi_conclu    = TextAreaField('',validators=[DataRequired(message="Insira considerações ou conclusão!")])
    tempo_realizado = StringField('Tempo realizado:')

    submit       = SubmitField('Registrar')   

class AvaliaAtivForm(FlaskForm):

    nota             = IntegerField('Nota: ', validators=[DataRequired(message="Informe a nota!")])
    justificativa    = TextAreaField('Justificativa', validators=[DataRequired(message="Informe a justificativa!")])
    tempo_homologado = StringField('Tempo homologado:')

    submit       = SubmitField('Registrar')      

   


# class PesquisaForm(FlaskForm):

    # coords = db.session.query(Coords.sigla)\
    #                   .order_by(Coords.sigla).all()
    # lista_coords = [(c[0],c[0]) for c in coords]
    # lista_coords.insert(0,('',''))

    # tipos = db.session.query(Tipos_Demanda.tipo)\
    #                   .order_by(Tipos_Demanda.tipo).all()
    # lista_tipos = [(t[0],t[0]) for t in tipos]
    # lista_tipos.insert(0,('',''))

    # pessoas = db.session.query(User.username, User.id)\
    #                   .order_by(User.username).all()
    # lista_pessoas = [(str(p[1]),p[0]) for p in pessoas]
    # lista_pessoas.insert(0,('',''))

    # atividades = db.session.query(Plano_Trabalho.atividade_sigla, Plano_Trabalho.id)\
    #                   .order_by(Plano_Trabalho.atividade_sigla).all()
    # lista_atividades = [(str(a[1]),a[0]) for a in atividades]
    # lista_atividades.insert(0,('',''))

    # coord               = SelectField('Coordenação:',choices= lista_coords)
    # sei                 = StringField('SEI:')
    # convênio            = StringField('Convênio:')
    # tipo                = SelectField(choices= lista_tipos)
    # titulo              = StringField('Título:')
    # ## os valore nos dois campos a seguir vão ao contrário, pois na view a condição de pesquisa usa o !=
    # necessita_despacho  = SelectField('Aguarda Despacho',choices=[('Todos','Todos'),
    #                                            ('Sim','Não'),
    #                                            ('Não','Sim')])
    # necessita_despacho_cg  = SelectField('Aguarda Despacho superior',choices=[('Todos','Todos'),
    #                                           ('Sim','Não'),
    #                                           ('Não','Sim')])
    # # conclu              = SelectField('Concluído',choices=[('Todos','Todos'),
    # #                                             ('Sim','Não'),
    # #                                             ('Não','Sim')])
    # conclu              = SelectField('Concluída?',choices=[('Todos','Todos'),('0','Não'),('1','Sim, com sucesso'),('2','Sim, com insucesso')])

    # autor               = SelectField('Responsável:',choices= lista_pessoas)

    # demanda_id          = StringField('Número da demanda:')

    # atividade           = SelectField('Atividade:',choices= lista_atividades)

    # submit              = SubmitField('Pesquisar')

# form para definir o peso de cada componente RDU
# class PesosForm(FlaskForm):

    # coords = db.session.query(Coords.sigla)\
    #                   .order_by(Coords.sigla).all()
    # lista_coords = [(c[0],c[0]) for c in coords]
    # lista_coords.insert(0,('',''))

    # pessoas = db.session.query(User.username, User.id)\
    #                   .order_by(User.username).all()
    # lista_pessoas = [(str(p[1]),p[0]) for p in pessoas]
    # lista_pessoas.insert(0,('',''))

    # peso_R = SelectField('Relevância:',choices= [('0.5','Importante'),('1','Normal'),('1.5','Sem importância')],default='1')
    # peso_D = SelectField('Momento:',choices= [('0.5','Importante'),('1','Normal'),('1.5','Sem importância')],default='1')
    # peso_U = SelectField('Urgência:',choices= [('0.5','Importante'),('1','Normal'),('1.5','Sem importância')],default='1')
    # coord  = SelectField('Coordenação:',choices= lista_coords)
    # pessoa = SelectField('Responsável:',choices= lista_pessoas)
    # submit = SubmitField('Aplicar')

# form para aferir demanda
class Afere_Demanda_Form(FlaskForm):

    nota = RadioField('Nota:',choices=[('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')],
                              validators=[DataRequired(message="Escolha a nota!")])

    submit      = SubmitField('Registrar')



