from models import db, User, City
from werkzeug.security import generate_password_hash


def init_db():
    db.create_all()

    # Создаем администратора если его нет
    admin = User.query.filter_by(email='admin@altai.ru').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@altai.ru',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()


def add_default_cities():
    """Добавляем города Алтайского края по умолчанию"""

    default_cities = [
        # Крупные города
        {'name': 'Барнаул', 'lat': 53.3606, 'lng': 83.7636, 'zoom': 12},
        {'name': 'Бийск', 'lat': 52.5186, 'lng': 85.2436, 'zoom': 12},
        {'name': 'Рубцовск', 'lat': 51.5147, 'lng': 81.2061, 'zoom': 13},
        {'name': 'Новоалтайск', 'lat': 53.4125, 'lng': 83.9311, 'zoom': 13},
        {'name': 'Заринск', 'lat': 53.7072, 'lng': 84.9333, 'zoom': 13},

        # Средние города
        {'name': 'Камень-на-Оби', 'lat': 53.7917, 'lng': 81.3486, 'zoom': 13},
        {'name': 'Славгород', 'lat': 53.0000, 'lng': 78.6500, 'zoom': 13},
        {'name': 'Алейск', 'lat': 52.5000, 'lng': 82.7833, 'zoom': 14},
        {'name': 'Яровое', 'lat': 52.9333, 'lng': 78.5833, 'zoom': 14},
        {'name': 'Белокуриха', 'lat': 51.9900, 'lng': 84.9833, 'zoom': 14},

        # Малые города
        {'name': 'Горняк', 'lat': 50.9500, 'lng': 81.4667, 'zoom': 14},
        {'name': 'Змеиногорск', 'lat': 51.1667, 'lng': 82.1667, 'zoom': 14},
        {'name': 'ЗАТО Сибирский', 'lat': 53.5667, 'lng': 83.8333, 'zoom': 14},
    ]

    for city_data in default_cities:
        if not City.query.filter_by(name=city_data['name']).first():
            city = City(
                name=city_data['name'],
                region='Алтайский край',
                latitude=city_data['lat'],
                longitude=city_data['lng'],
                zoom_level=city_data['zoom']
            )
            db.session.add(city)

    db.session.commit()