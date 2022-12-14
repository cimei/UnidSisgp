"""
.. topic:: **PGs (formulários)**

    Os formulários do módulo *pgs* recebem dados informados pelo usuário para
    registro, atualização de programas de gestão.

    * PGForm: iserir ou alterar pg.

"""

# forms.py na pasta objetos

import datetime
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, SelectMultipleField,\
                    TextAreaField, SubmitField
from wtforms.fields.html5 import DateField                    
from wtforms.validators import DataRequired, Regexp, Optional


class PGForm(FlaskForm):

    data_ini     = DateField('Data início', format='%Y-%m-%d', validators=[DataRequired(message="Informe data de início!")])
    data_fim     = DateField('Data fim', format='%Y-%m-%d', validators=[DataRequired(message="Informe data de fim!")])
    tempo_comp   = IntegerField('T.C.',validators=[DataRequired(message="Insira o tempo para comparecimento!")])
    # modalidade   = SelectField('Modalidade', validators=[DataRequired(message="Informa a modalidade!")])
    termo_aceite = TextAreaField('Termo de aceite', validators=(Optional(),))
    ativs        = SelectMultipleField('Atividades', validators=[DataRequired(message="Escolha atividades!")])

    submit       = SubmitField('Registrar') 
    

