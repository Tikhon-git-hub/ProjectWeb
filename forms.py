from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from flask_wtf.file import FileField, FileAllowed, FileRequired
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(), Length(min=3, max=64)
    ])
    email = StringField('Email', validators=[
        DataRequired(), Email(), Length(max=120)
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(), Length(min=6, message='Пароль должен быть не менее 6 символов')
    ])
    confirm_password = PasswordField('Подтверждение пароля', validators=[
        DataRequired(), EqualTo('password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class SearchForm(FlaskForm):
    search = StringField('Поиск', validators=[DataRequired()])
    submit = SubmitField('Найти')

class AdditiveForm(FlaskForm):
    code = StringField('Код добавки (E-номер)', validators=[
        DataRequired(message='Код добавки обязателен'),
        Length(min=2, max=10, message='Код должен быть от 2 до 10 символов')
    ])
    name = StringField('Название', validators=[
        DataRequired(message='Название обязательно'),
        Length(max=200, message='Название не должно превышать 200 символов')
    ])
    name_en = StringField('Название (англ.)', validators=[
        Length(max=200, message='Название не должно превышать 200 символов')
    ])
    category = SelectField('Категория', choices=[
        ('color', 'Краситель'),
        ('preservative', 'Консервант'),
        ('antioxidant', 'Антиоксидант'),
        ('emulsifier', 'Эмульгатор'),
        ('stabilizer', 'Стабилизатор'),
        ('thickener', 'Загуститель'),
        ('sweetener', 'Подсластитель'),
        ('other', 'Другое')
    ], validators=[DataRequired()])
    status = SelectField('Статус', choices=[
        ('safe', 'Безопасная'),
        ('caution', 'Требует осторожности'),
        ('dangerous', 'Опасная')
    ], validators=[DataRequired()])
    hazard_level = SelectField('Уровень опасности', choices=[
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий')
    ], validators=[DataRequired()], default=3)
    description = TextAreaField('Описание', validators=[
        Length(max=1000, message='Описание не должно превышать 1000 символов')
    ])
    effect_on_health = TextAreaField('Влияние на здоровье', validators=[
        Length(max=1000, message='Текст не должен превышать 1000 символов')
    ])
    daily_intake = StringField('Допустимая суточная доза', validators=[
        Length(max=200)
    ])
    foods_contain = TextAreaField('Где содержится', validators=[
        Length(max=500)
    ])
    image = FileField('Изображение', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'],
                   message='Разрешены только изображения (jpg, jpeg, png, gif, webp)')
    ])
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super(AdditiveForm, self).__init__(*args, **kwargs)
        # Для редактирования делаем поле code необязательным
        if kwargs.get('obj'):
            self.code.validators = [Length(min=2, max=10)]