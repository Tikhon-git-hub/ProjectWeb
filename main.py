import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image
from sqlalchemy import or_
from functools import wraps
from datetime import datetime

load_dotenv()

from models import db, User, Additive, AdditiveImage, favorites
from forms import RegistrationForm, LoginForm, SearchForm, AdditiveForm

# ========== ИНИЦИАЛИЗАЦИЯ APP (СНАЧАЛА) ==========
app = Flask(__name__)

# ========== КОНФИГУРАЦИЯ ==========
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///additives.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ========== ИНИЦИАЛИЗАЦИЯ РАСШИРЕНИЙ ==========
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите, чтобы добавить в избранное'


# ========== ФУНКЦИИ ЗАГРУЗКИ ПОЛЬЗОВАТЕЛЯ ==========
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, prefix='additive'):
    """Сохранение и оптимизация изображения"""
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{prefix}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        img = Image.open(file)
        img.thumbnail((800, 800))
        img.save(filepath, optimize=True, quality=85)

        return filename
    return None


# Создание папок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ========== КОНТЕКСТНЫЙ ПРОЦЕССОР ==========
@app.context_processor
def inject_search_form():
    return {'search_form': SearchForm()}


# ========== МАРШРУТЫ ==========
@app.route('/')
def index():
    """Главная страница"""
    total_additives = Additive.query.count()
    safe_count = Additive.query.filter_by(status='safe').count()
    dangerous_count = Additive.query.filter_by(status='dangerous').count()

    popular_additives = db.session.query(
        Additive, db.func.count(favorites.c.additive_id).label('favorites_count')
    ).outerjoin(favorites, Additive.id == favorites.c.additive_id
                ).group_by(Additive.id
                           ).order_by(db.desc('favorites_count')
                                      ).limit(6).all()

    recent_additives = Additive.query.order_by(Additive.created_at.desc()).limit(6).all()

    return render_template('index.html',
                           total_additives=total_additives,
                           safe_count=safe_count,
                           dangerous_count=dangerous_count,
                           popular_additives=popular_additives,
                           recent_additives=recent_additives)


@app.route('/additives')
def additives_list():
    """Страница со списком всех добавок"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = Additive.query

    search_query = request.args.get('search', '')
    if search_query:
        query = query.filter(
            or_(
                Additive.code.ilike(f'%{search_query}%'),
                Additive.name.ilike(f'%{search_query}%'),
                Additive.name_en.ilike(f'%{search_query}%')
            )
        )

    category = request.args.get('category', '')
    if category:
        query = query.filter_by(category=category)

    status = request.args.get('status', '')
    if status:
        query = query.filter_by(status=status)

    sort = request.args.get('sort', 'code')
    if sort == 'code':
        query = query.order_by(Additive.code)
    elif sort == 'name':
        query = query.order_by(Additive.name)
    elif sort == 'hazard_desc':
        query = query.order_by(Additive.hazard_level.desc())
    else:
        query = query.order_by(Additive.code)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    additives = pagination.items

    return render_template('additives_list.html',
                           additives=additives,
                           pagination=pagination,
                           search_query=search_query,
                           category=category,
                           status=status,
                           sort=sort)


@app.route('/additive/<string:code>')
def additive_detail(code):
    """Детальная страница добавки"""
    additive = Additive.query.filter_by(code=code.upper()).first_or_404()

    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = additive in current_user.favorites

    # Получаем похожие добавки (из той же категории, исключая текущую)
    similar_additives = Additive.query.filter(
        Additive.category == additive.category,
        Additive.id != additive.id
    ).limit(5).all()

    return render_template('additive_detail.html',
                           additive=additive,
                           is_favorited=is_favorited,
                           similar_additives=similar_additives)


@app.route('/additive/add', methods=['GET', 'POST'])
@login_required
def add_additive():
    """Добавление новой добавки (только для зарегистрированных пользователей)"""
    form = AdditiveForm()

    if form.validate_on_submit():
        # Проверяем, существует ли уже добавка с таким кодом
        existing = Additive.query.filter_by(code=form.code.data.upper()).first()
        if existing:
            flash('Добавка с таким кодом уже существует в базе!', 'danger')
            return render_template('add_additive.html', form=form)

        # Создаем новую добавку
        additive = Additive(
            code=form.code.data.upper(),
            name=form.name.data,
            name_en=form.name_en.data or None,
            category=form.category.data,
            status=form.status.data,
            description=form.description.data or None,
            effect_on_health=form.effect_on_health.data or None,
            daily_intake=form.daily_intake.data or None,
            foods_contain=form.foods_contain.data or None,
            hazard_level=form.hazard_level.data
        )

        # Сохраняем изображение, если загружено
        if form.image.data:
            image_filename = save_image(form.image.data, prefix=additive.code)
            if image_filename:
                additive.image_filename = image_filename

        db.session.add(additive)
        db.session.commit()

        flash(f'✅ Добавка {additive.code} успешно добавлена в базу!', 'success')
        return redirect(url_for('additive_detail', code=additive.code))

    return render_template('add_additive.html', form=form)


@app.route('/additive/<string:code>/edit', methods=['GET', 'POST'])
@login_required
def edit_additive(code):
    """Редактирование добавки"""
    additive = Additive.query.filter_by(code=code.upper()).first_or_404()
    form = AdditiveForm()

    if request.method == 'GET':
        # Заполняем форму существующими данными
        form.code.data = additive.code
        form.name.data = additive.name
        form.name_en.data = additive.name_en
        form.category.data = additive.category
        form.status.data = additive.status
        form.hazard_level.data = additive.hazard_level
        form.description.data = additive.description
        form.effect_on_health.data = additive.effect_on_health
        form.daily_intake.data = additive.daily_intake
        form.foods_contain.data = additive.foods_contain

    if form.validate_on_submit():
        # Обновляем данные
        additive.code = form.code.data.upper()
        additive.name = form.name.data
        additive.name_en = form.name_en.data or None
        additive.category = form.category.data
        additive.status = form.status.data
        additive.description = form.description.data or None
        additive.effect_on_health = form.effect_on_health.data or None
        additive.daily_intake = form.daily_intake.data or None
        additive.foods_contain = form.foods_contain.data or None
        additive.hazard_level = form.hazard_level.data

        # Обновляем изображение, если загружено новое
        if form.image.data:
            # Удаляем старое изображение
            if additive.image_filename:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], additive.image_filename)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

            # Сохраняем новое
            image_filename = save_image(form.image.data, prefix=additive.code)
            if image_filename:
                additive.image_filename = image_filename

        db.session.commit()
        flash(f'✏️ Добавка {additive.code} успешно обновлена!', 'success')
        return redirect(url_for('additive_detail', code=additive.code))

    return render_template('edit_additive.html', form=form, additive=additive)


@app.route('/additive/<string:code>/delete', methods=['POST'])
@login_required
def delete_additive(code):
    """Удаление добавки"""
    additive = Additive.query.filter_by(code=code.upper()).first_or_404()

    # Сохраняем код для сообщения
    additive_code = additive.code

    # Удаляем изображение, если оно есть
    if additive.image_filename:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], additive.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    # Удаляем добавку из избранного у всех пользователей
    additive.users_favorited.clear()

    db.session.delete(additive)
    db.session.commit()

    flash(f'🗑️ Добавка {additive_code} удалена из базы.', 'warning')
    return redirect(url_for('additives_list'))


@app.route('/my_additives')
@login_required
def my_additives():
    """Список всех добавок (можно отфильтровать по создателю, если добавить поле created_by)"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Если в модели Additive есть поле created_by, можно фильтровать по пользователю
    # query = Additive.query.filter_by(created_by=current_user.id)
    # Пока показываем все добавки
    query = Additive.query

    search_query = request.args.get('search', '')
    if search_query:
        query = query.filter(
            or_(
                Additive.code.ilike(f'%{search_query}%'),
                Additive.name.ilike(f'%{search_query}%')
            )
        )

    pagination = query.order_by(Additive.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('my_additives.html',
                           additives=pagination.items,
                           pagination=pagination,
                           search_query=search_query)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный email или пароль.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@app.route('/favorites')
@login_required
def favorites_list():
    """Список избранных добавок пользователя"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    pagination = Additive.query.join(
        favorites, Additive.id == favorites.c.additive_id
    ).filter(
        favorites.c.user_id == current_user.id
    ).order_by(Additive.code).paginate(
        page=page, per_page=per_page, error_out=False
    )

    additives = pagination.items

    return render_template('favorites.html',
                           additives=additives,
                           pagination=pagination)


@app.route('/favorites/toggle/<int:additive_id>', methods=['POST'])
@login_required
def toggle_favorite(additive_id):
    additive = Additive.query.get_or_404(additive_id)

    if additive in current_user.favorites:
        current_user.favorites.remove(additive)
        flash(f'"{additive.code}" удалена из избранного.', 'info')
    else:
        current_user.favorites.append(additive)
        flash(f'"{additive.code}" добавлена в избранное!', 'success')

    db.session.commit()
    return redirect(request.referrer or url_for('additives_list'))


# ========== REST API ==========
@app.route('/api/additives', methods=['GET'])
def api_get_additives():
    query = Additive.query

    if request.args.get('category'):
        query = query.filter_by(category=request.args.get('category'))

    if request.args.get('status'):
        query = query.filter_by(status=request.args.get('status'))

    if request.args.get('search'):
        search = request.args.get('search')
        query = query.filter(
            or_(
                Additive.code.ilike(f'%{search}%'),
                Additive.name.ilike(f'%{search}%')
            )
        )

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
        'data': [{
            'code': a.code,
            'name': a.name,
            'category': a.category_ru,
            'status': a.status,
            'hazard_level': a.hazard_level,
            'url': url_for('additive_detail', code=a.code, _external=True)
        } for a in pagination.items]
    })


@app.route('/api/additives', methods=['POST'])
@login_required
def api_add_additive():
    """API для добавления новой добавки"""
    data = request.json

    # Проверка обязательных полей
    required_fields = ['code', 'name', 'category', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Проверка на существование
    existing = Additive.query.filter_by(code=data['code'].upper()).first()
    if existing:
        return jsonify({'error': 'Additive with this code already exists'}), 409

    additive = Additive(
        code=data['code'].upper(),
        name=data['name'],
        name_en=data.get('name_en'),
        category=data['category'],
        status=data['status'],
        description=data.get('description'),
        effect_on_health=data.get('effect_on_health'),
        daily_intake=data.get('daily_intake'),
        foods_contain=data.get('foods_contain'),
        hazard_level=data.get('hazard_level', 3)
    )

    db.session.add(additive)
    db.session.commit()

    return jsonify({
        'message': 'Additive created successfully',
        'code': additive.code,
        'url': url_for('additive_detail', code=additive.code, _external=True)
    }), 201


@app.route('/api/additives/<string:code>', methods=['GET'])
def api_get_additive(code):
    additive = Additive.query.filter_by(code=code.upper()).first_or_404()

    return jsonify({
        'code': additive.code,
        'name': additive.name,
        'name_en': additive.name_en,
        'category': additive.category_ru,
        'status': additive.status,
        'description': additive.description,
        'effect_on_health': additive.effect_on_health,
        'daily_intake': additive.daily_intake,
        'foods_contain': additive.foods_contain,
        'hazard_level': additive.hazard_level,
        'image_url': url_for('static', filename=f'uploads/{additive.image_filename}',
                             _external=True) if additive.image_filename else None
    })


@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    categories = {}
    for cat in ['color', 'preservative', 'antioxidant', 'emulsifier',
                'stabilizer', 'thickener', 'sweetener', 'other']:
        count = Additive.query.filter_by(category=cat).count()
        temp = Additive(category=cat)
        categories[cat] = {
            'name': temp.category_ru,
            'count': count
        }

    return jsonify(categories)


@app.route('/api/random', methods=['GET'])
def api_random_additive():
    count = Additive.query.count()
    if count == 0:
        return jsonify({'error': 'No additives found'}), 404

    import random
    random_id = random.randint(1, count)
    additive = Additive.query.get(random_id)

    return jsonify({
        'code': additive.code,
        'name': additive.name,
        'status': additive.status,
        'url': url_for('additive_detail', code=additive.code, _external=True)
    })


# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)