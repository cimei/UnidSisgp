"""
.. topic:: **Objetos (formulários)**

    Os formulários do módulo *Objetos* recebem dados informados pelo usuário para
    registro, atualização de objetos.

    * ObjetoForm: iserir ou alterar objeto.

"""

# forms.py na pasta objetos

import datetime
from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SelectField, BooleanField, DecimalField,\
                    DateField, DateTimeField, TextAreaField, SubmitField, RadioField
from wtforms.validators import DataRequired, Regexp, Optional


class ObjetoForm(FlaskForm):

    desc = StringField('Descrição:', validators=[DataRequired(message="Insira uma descrição!")])
    tipo = IntegerField('Tipo:', validators=[DataRequired(message="Insira um tipo!")])
    chave = StringField('Chave:', validators=[DataRequired(message="Insira uma chave!")])
    ativo = BooleanField('Ativo?')

    submit      = SubmitField('Registrar')

class ObjetoEscolhaForm(FlaskForm):

    obj      = SelectField('Objeto:')
    replicar = BooleanField('Replicar para demais ocorrências?')

    submit = SubmitField('Registrar')     

