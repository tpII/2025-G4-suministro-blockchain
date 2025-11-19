# app/forms.py

from flask_wtf import FlaskForm
from wtforms import FloatField, HiddenField, SelectField, StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, InputRequired, EqualTo
from app.models import User
from app.config import WINE_VARIETALS  

# Formulario de login
class LoginForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordar')
    submit = SubmitField('Iniciar sesión')
    client_login = SubmitField('Acceder como cliente')

# Formulario de registro
class RegistrationForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password2 = PasswordField(
        'Repetir contraseña', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Rol', choices=[('Productor', 'Productor'), ('Transportador', 'Transportador')])
    submit = SubmitField('Registrarse')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Ese nombre de usuario está en uso.')

# Formulario de lectura de asset
class ReadAssetForm(FlaskForm):
    rfid_tag = StringField('Rfid', validators=[DataRequired()])
    llenar_boton = SubmitField('Escanear RFID')
    enviar_boton = SubmitField('Enviar Formulario')

# Formulario de creación de asset
class CreateAssetForm(FlaskForm):
    rfid_tag = StringField('Rfid', validators=[InputRequired()])
    llenar_boton_rfid = SubmitField('Escanear RFID')
    precio = FloatField('Precio', validators=[DataRequired()])
    bodega = StringField('Bodega', validators=[DataRequired()])
    uva = SelectField("Varietal", choices=[(varietal, varietal) for varietal in WINE_VARIETALS.keys()])
    cosecha = StringField('Cosecha', validators=[DataRequired()])
    temperatura = FloatField('Temperatura', validators=[InputRequired()])
    humedad = FloatField('Humedad', validators=[InputRequired()])
    llenar_boton_dht = SubmitField('Escanear DHT')
    latitud = FloatField('Latitud', validators=[InputRequired()])
    longitud = FloatField('Longitud', validators=[InputRequired()])
    enviar_boton = SubmitField('Enviar Formulario')

class UpdateAssetForm(FlaskForm):
    precio = FloatField('Precio', validators=[DataRequired()])
    bodega = StringField('Bodega', validators=[DataRequired()])
    uva = SelectField("Varietal", choices=[(varietal, varietal) for varietal in WINE_VARIETALS.keys()])
    cosecha = StringField('Cosecha', validators=[DataRequired()])
    temperatura = FloatField('Temperatura', validators=[InputRequired()])
    humedad = FloatField('Humedad', validators=[InputRequired()])
    llenar_boton_dht = SubmitField('Escanear DHT')
    latitud = FloatField('Latitud', validators=[InputRequired()])
    longitud = FloatField('Longitud', validators=[InputRequired()])
    owner = HiddenField()
    actualizar_boton = SubmitField('Actualizar Formulario')

class TransferAssetForm(FlaskForm):
    owner = SelectField('Dueño', choices=[])
    transferir_boton = SubmitField('Transferir asset')

