from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

from config import Config
from models import db, User, City, CityPoint, PointImage, Vote, Comment
from database import init_db, add_default_cities

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация БД
db.init_app(app)
with app.app_context():
    init_db()
    add_default_cities()

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Создаем папку для загрузок если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Создаем фильтр escapejs для шаблонов
@app.template_filter('escapejs')
def escapejs_filter(s):
    """Экранирование строк для JavaScript"""
    if s is None:
        return ''
    # Экранируем специальные символы
    s = str(s)
    escape_dict = {
        '\\': '\\\\',
        '"': '\\"',
        "'": "\\'",
        '\n': '\\n',
        '\r': '\\r',
        '\t': '\\t',
    }
    return ''.join(escape_dict.get(c, c) for c in s)


# Главная страница с выбором города
@app.route('/')
@app.route('/city/<int:city_id>')
def index(city_id=None):
    cities = City.query.filter_by(is_active=True).all()

    if city_id:
        current_city = City.query.get_or_404(city_id)
    elif cities:
        current_city = cities[0]
    else:
        current_city = None

    points = []
    if current_city:
        points = CityPoint.query.filter_by(
            city_id=current_city.id,
            status='approved'
        ).order_by(CityPoint.created_at.desc()).all()

    categories = ['спорт', 'культура', 'детский досуг', 'экология', 'транспорт', 'благоустройство', 'безопасность']

    return render_template('index.html',
                           cities=cities,
                           current_city=current_city,
                           points=points,
                           categories=categories)


# API для получения точек города
@app.route('/api/points/<int:city_id>')
def api_points(city_id):
    points = CityPoint.query.filter_by(city_id=city_id, status='approved').all()
    points_data = []

    for point in points:
        points_data.append({
            'id': point.id,
            'title': point.title,
            'description': point.description,
            'category': point.category,
            'lat': point.latitude,
            'lng': point.longitude,
            'author': point.author.username,
            'created_at': point.created_at.strftime('%d.%m.%Y'),
            'images': [url_for('uploaded_file', filename=img.filename) for img in point.images]
        })

    return jsonify(points_data)


# API для получения списка городов
@app.route('/api/cities')
def api_cities():
    cities = City.query.filter_by(is_active=True).all()
    cities_data = []

    for city in cities:
        cities_data.append({
            'id': city.id,
            'name': city.name,
            'region': city.region,
            'lat': city.latitude,
            'lng': city.longitude,
            'zoom': city.zoom_level,
            'points_count': CityPoint.query.filter_by(city_id=city.id, status='approved').count()
        })

    return jsonify(cities_data)


# Аутентификация
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверный email или пароль')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password)

        # Подписываем на все активные города по умолчанию
        active_cities = City.query.filter_by(is_active=True).all()
        user.followed_cities = active_cities

        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# Профиль пользователя
@app.route('/profile')
@login_required
def profile():
    user_points = CityPoint.query.filter_by(user_id=current_user.id).order_by(CityPoint.created_at.desc()).all()
    followed_cities = current_user.followed_cities
    all_cities = City.query.filter_by(is_active=True).all()

    # Статистика по городам
    city_stats = []
    for city in all_cities:
        count = CityPoint.query.filter_by(
            user_id=current_user.id,
            city_id=city.id
        ).count()
        if count > 0:
            city_stats.append({
                'name': city.name,
                'count': count
            })

    return render_template('profile.html',
                           user_points=user_points,
                           followed_cities=followed_cities,
                           all_cities=all_cities,
                           city_stats=city_stats)


# Управление подписками на города
@app.route('/profile/follow_city/<int:city_id>', methods=['POST'])
@login_required
def follow_city(city_id):
    city = City.query.get_or_404(city_id)

    if city not in current_user.followed_cities:
        current_user.followed_cities.append(city)
        db.session.commit()
        flash(f'Вы подписались на город {city.name}')
    else:
        current_user.followed_cities.remove(city)
        db.session.commit()
        flash(f'Вы отписались от города {city.name}')

    return redirect(url_for('profile'))


# Добавление предложения
@app.route('/add_point', methods=['GET', 'POST'])
@login_required
def add_point():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        city_id = int(request.form.get('city_id'))
        address = request.form.get('address', '')
        latitude = float(request.form.get('latitude'))
        longitude = float(request.form.get('longitude'))

        point = CityPoint(
            title=title,
            description=description,
            category=category,
            address=address,
            latitude=latitude,
            longitude=longitude,
            user_id=current_user.id,
            city_id=city_id
        )

        db.session.add(point)
        db.session.flush()

        # Обработка загруженных файлов
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    point_image = PointImage(filename=filename, point_id=point.id)
                    db.session.add(point_image)

        db.session.commit()
        flash('Предложение успешно добавлено! Ожидайте модерации.')
        return redirect(url_for('index', city_id=city_id))

    cities = City.query.filter_by(is_active=True).all()
    if not cities:
        flash('Нет доступных городов. Обратитесь к администратору.')
        return redirect(url_for('index'))

    categories = ['спорт', 'культура', 'детский досуг', 'экология', 'транспорт', 'благоустройство', 'безопасность']

    return render_template('add_point.html',
                           cities=cities,
                           categories=categories)


# Детальная страница предложения
@app.route('/point/<int:point_id>')
def point_detail(point_id):
    point = CityPoint.query.get_or_404(point_id)
    votes_up = Vote.query.filter_by(point_id=point_id, vote_type='upvote').count()
    votes_down = Vote.query.filter_by(point_id=point_id, vote_type='downvote').count()

    user_vote = None
    if current_user.is_authenticated:
        vote = Vote.query.filter_by(user_id=current_user.id, point_id=point_id).first()
        if vote:
            user_vote = vote.vote_type

    comments = Comment.query.filter_by(point_id=point_id).order_by(Comment.created_at.desc()).all()

    # Похожие предложения в том же городе
    similar_points = CityPoint.query.filter(
        CityPoint.city_id == point.city_id,
        CityPoint.category == point.category,
        CityPoint.id != point_id,
        CityPoint.status == 'approved'
    ).limit(5).all()

    # Преобразуем данные для передачи в JavaScript
    point_data = {
        'id': point.id,
        'title': point.title,
        'latitude': point.latitude,
        'longitude': point.longitude,
        'city_name': point.city.name
    }

    return render_template('point_detail.html',
                           point=point,
                           votes_up=votes_up,
                           votes_down=votes_down,
                           user_vote=user_vote,
                           comments=comments,
                           similar_points=similar_points,
                           point_data=json.dumps(point_data))


# Голосование
@app.route('/vote/<int:point_id>/<vote_type>', methods=['POST'])
@login_required
def vote(point_id, vote_type):
    if vote_type not in ['upvote', 'downvote']:
        return jsonify({'error': 'Invalid vote type'}), 400

    point = CityPoint.query.get_or_404(point_id)
    existing_vote = Vote.query.filter_by(user_id=current_user.id, point_id=point_id).first()

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
        else:
            existing_vote.vote_type = vote_type
    else:
        vote = Vote(vote_type=vote_type, user_id=current_user.id, point_id=point_id)
        db.session.add(vote)

    db.session.commit()

    votes_up = Vote.query.filter_by(point_id=point_id, vote_type='upvote').count()
    votes_down = Vote.query.filter_by(point_id=point_id, vote_type='downvote').count()

    return jsonify({
        'votes_up': votes_up,
        'votes_down': votes_down
    })


# Комментарии
@app.route('/comment/<int:point_id>', methods=['POST'])
@login_required
def add_comment(point_id):
    content = request.form.get('content')
    if not content:
        flash('Комментарий не может быть пустым')
        return redirect(url_for('point_detail', point_id=point_id))

    comment = Comment(
        content=content,
        user_id=current_user.id,
        point_id=point_id
    )

    db.session.add(comment)
    db.session.commit()

    flash('Комментарий добавлен')
    return redirect(url_for('point_detail', point_id=point_id))


# Админ-панель
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('index'))

    points = CityPoint.query.order_by(CityPoint.created_at.desc()).all()
    users = User.query.all()
    cities = City.query.all()

    # Статистика
    stats = {
        'total_points': CityPoint.query.count(),
        'pending_points': CityPoint.query.filter_by(status='pending').count(),
        'total_users': User.query.count(),
        'total_cities': City.query.count(),
        'total_comments': Comment.query.count()
    }

    return render_template('admin.html',
                           points=points,
                           users=users,
                           cities=cities,
                           stats=stats)


# Управление городами
@app.route('/admin/cities', methods=['GET', 'POST'])
@login_required
def admin_cities():
    if not current_user.is_admin:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        region = request.form.get('region', 'Алтайский край')
        latitude = float(request.form.get('latitude'))
        longitude = float(request.form.get('longitude'))
        zoom_level = int(request.form.get('zoom_level', 12))

        if City.query.filter_by(name=name).first():
            flash('Город с таким названием уже существует')
            return redirect(url_for('admin_cities'))

        city = City(
            name=name,
            region=region,
            latitude=latitude,
            longitude=longitude,
            zoom_level=zoom_level
        )

        db.session.add(city)
        db.session.commit()

        # Подписываем всех пользователей на новый город
        users = User.query.all()
        for user in users:
            user.followed_cities.append(city)

        db.session.commit()
        flash(f'Город {name} успешно добавлен!')
        return redirect(url_for('admin_cities'))

    cities = City.query.all()
    return render_template('admin_cities.html', cities=cities)


# Обновление статуса города
@app.route('/admin/city/<int:city_id>/toggle', methods=['POST'])
@login_required
def toggle_city(city_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    city = City.query.get_or_404(city_id)
    city.is_active = not city.is_active
    db.session.commit()

    return jsonify({
        'success': True,
        'is_active': city.is_active
    })


# Обновление статуса предложения
@app.route('/admin/update_status/<int:point_id>', methods=['POST'])
@login_required
def update_status(point_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    point = CityPoint.query.get_or_404(point_id)
    new_status = request.json.get('status')

    if new_status in ['pending', 'approved', 'rejected', 'completed']:
        point.status = new_status
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'error': 'Invalid status'}), 400


# Статические файлы
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



# Игра Змейка
@app.route('/snake')
def snake_game():
    return render_template('snake.html')




if __name__ == '__main__':
    app.run(debug=True, port=5001)
