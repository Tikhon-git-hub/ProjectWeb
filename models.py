from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# Таблица для избранного (многие ко многим)
favorites = db.Table('favorites',
                     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                     db.Column('additive_id', db.Integer, db.ForeignKey('additive.id'), primary_key=True)
                     )


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с избранными добавками
    favorites = db.relationship('Additive', secondary=favorites,
                                backref=db.backref('users_favorited', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Additive(db.Model):
    __tablename__ = 'additive'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, index=True)  # safe, caution, dangerous
    description = db.Column(db.Text, nullable=True)
    effect_on_health = db.Column(db.Text, nullable=True)
    daily_intake = db.Column(db.String(200), nullable=True)
    foods_contain = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(200), nullable=True)
    hazard_level = db.Column(db.Integer, default=3)  # 1-5, где 5 - самый опасный
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def category_ru(self):
        """Возвращает русское название категории"""
        categories = {
            'color': 'Краситель',
            'preservative': 'Консервант',
            'antioxidant': 'Антиоксидант',
            'emulsifier': 'Эмульгатор',
            'stabilizer': 'Стабилизатор',
            'thickener': 'Загуститель',
            'sweetener': 'Подсластитель',
            'other': 'Другое'
        }
        return categories.get(self.category, self.category)

    @property
    def status_ru(self):
        """Возвращает русское название статуса"""
        statuses = {
            'safe': 'Безопасная',
            'caution': 'Требует осторожности',
            'dangerous': 'Опасная'
        }
        return statuses.get(self.status, self.status)

    def __repr__(self):
        return f'<Additive {self.code}: {self.name}>'


# Класс для дополнительных изображений (опционально)
class AdditiveImage(db.Model):
    __tablename__ = 'additive_image'

    id = db.Column(db.Integer, primary_key=True)
    additive_id = db.Column(db.Integer, db.ForeignKey('additive.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    additive = db.relationship('Additive', backref=db.backref('additional_images', lazy='dynamic'))

    def __repr__(self):
        return f'<AdditiveImage {self.filename}>'