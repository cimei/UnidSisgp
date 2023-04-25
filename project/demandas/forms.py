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
                    TextAreaField, SubmitField, RadioField, SelectMultipleField, FieldList, FormField, Form
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

    tipo        = SelectField('Tipo:',choices= lista_tipos)

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

class SolicitacaoForm604(FlaskForm):

    atividade  = SelectField('Atividade:')
    qtd        = IntegerField('Qtd ocor.:',default=1)
    desc       = TextAreaField('Justificativa:',validators=[DataRequired(message="Insira justificativa!")])

    submit     = SubmitField('Registrar')      

class SolicitacaoDesc(FlaskForm):

    desc       = TextAreaField('Justificativa:',validators=[DataRequired(message="Insira justificativa!")])

    submit     = SubmitField('Registrar') 

class SolicitacaoAnaliseForm(FlaskForm):

    aprovado    = RadioField("Aprovado?", choices=[(1,'Sim'),(0,'Não')],validators=[DataRequired(message="Escolha uma opção!")])
    observacoes = TextAreaField('Observações:',validators=[DataRequired(message="Insira observações!")])
    replicas    = BooleanField(default=False)

    submit       = SubmitField('Registrar')

class InciaConcluiAtivForm(FlaskForm):

    descricao       = TextAreaField('',validators=(Optional(),))
    data_ini        = DateField('Data', format='%Y-%m-%d', validators=(Optional(),))
    data_fim        = DateField('Data', format='%Y-%m-%d', validators=(Optional(),))
    consi_conclu    = TextAreaField('',validators=[DataRequired(message="Insira considerações ou conclusão!")])
    tempo_realizado = StringField('Tempo realizado:')

    submit       = SubmitField('Registrar')   

class AvaliaAtivForm(FlaskForm):

    nota =IntegerField('Nota:',validators=[DataRequired(message="Informe uma nota de 0 a 10. Valor inteiro!")])
    justificativa    = TextAreaField('Justificativa', validators=[DataRequired(message="Informe a justificativa!")])
    tempo_homologado = StringField('Tempo homologado:')

    submit       = SubmitField('Registrar')      

class AddAssuntoForm(FlaskForm):

    valor = StringField('Descrição:', validators=[DataRequired(message="Insira uma descrição!")])
    # chave = StringField('Chave:', validators=[DataRequired(message="Insira uma chave!")])
    # ativo = BooleanField('Ativo?')

    submit      = SubmitField('Registrar')  


class AtivForm(Form):
    ativ_id    = StringField('itemCatalogoId')
    titulo     = StringField('Titulo')
    tempo_rem  = StringField('Tempo remoto')
    tempo_pre  = StringField('Tempo presencial')
    modalidade = SelectField('Modalidade')
    # modalidade = SelectField('Modalidade', choices=[(103, 'Remoto'), (101, 'Presencial')])
    quantidade = IntegerField('Quantidade')

class CriaPlanoForm(FlaskForm):
    pessoa   = SelectField('Pessoa', validators=(Optional(),))
    data_ini = DateField('Data início', format='%Y-%m-%d', validators=[DataRequired(message="Informe data de início!")])
    data_fim = DateField('Data fim', format='%Y-%m-%d', validators=[DataRequired(message="Informe data de fim!")])
    ativs    = FieldList(FormField(AtivForm))

    submit      = SubmitField('Registrar')

class AnalisaPlano(FlaskForm):
    obs     = TextAreaField('Observações', validators=[DataRequired(message="Faça uma observação!")])
    parecer = SelectField('Parecer sobre plano proposto?',choices=[('403', 'Aceitar'),('404', 'Rejeitar')])

    submit  = SubmitField('Registrar')



# form para aferir demanda
class Afere_Demanda_Form(FlaskForm):

    nota = RadioField('Nota:',choices=[('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')],
                              validators=[DataRequired(message="Escolha a nota!")])

    submit      = SubmitField('Registrar')



