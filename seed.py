"""Скрипт для наполнения базы данных примерами пищевых добавок"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, db
from models import Additive


def seed_database():
    with app.app_context():
        # ВАЖНО: создаём таблицы, если их нет
        db.create_all()
        print("📁 Таблицы созданы (или уже существуют)")

        additives_data = [
            {
                'code': 'E100',
                'name': 'Куркумин',
                'name_en': 'Curcumin',
                'category': 'color',
                'status': 'safe',
                'description': 'Натуральный жёлтый краситель, получаемый из корня куркумы.',
                'effect_on_health': 'Считается безопасным, обладает антиоксидантными свойствами.',
                'daily_intake': 'До 3 мг/кг массы тела',
                'foods_contain': 'Карри, горчица, сыры, масло, маргарин',
                'hazard_level': 1
            },
            {
                'code': 'E202',
                'name': 'Сорбат калия',
                'name_en': 'Potassium sorbate',
                'category': 'preservative',
                'status': 'safe',
                'description': 'Консервант, предотвращающий рост плесени и дрожжей.',
                'effect_on_health': 'Безопасен для большинства людей, может вызывать аллергию у чувствительных.',
                'daily_intake': 'До 25 мг/кг массы тела',
                'foods_contain': 'Соусы, соки, йогурты, выпечка, сыры',
                'hazard_level': 1
            },
            {
                'code': 'E210',
                'name': 'Бензойная кислота',
                'name_en': 'Benzoic acid',
                'category': 'preservative',
                'status': 'caution',
                'description': 'Консервант, используется с осторожностью.',
                'effect_on_health': 'Может вызывать аллергические реакции, в сочетании с витамином C образует бензол (канцероген)',
                'daily_intake': 'До 5 мг/кг массы тела',
                'foods_contain': 'Газировка, соусы, маринады, джемы',
                'hazard_level': 3
            },
            {
                'code': 'E250',
                'name': 'Нитрит натрия',
                'name_en': 'Sodium nitrite',
                'category': 'preservative',
                'status': 'dangerous',
                'description': 'Консервант и фиксатор цвета в мясных продуктах.',
                'effect_on_health': 'Может образовывать канцерогенные нитрозамины. Связывают с раком желудка.',
                'daily_intake': 'До 0.07 мг/кг массы тела',
                'foods_contain': 'Колбасы, сосиски, ветчина, бекон',
                'hazard_level': 5
            },
            {
                'code': 'E300',
                'name': 'Аскорбиновая кислота',
                'name_en': 'Ascorbic acid',
                'category': 'antioxidant',
                'status': 'safe',
                'description': 'Витамин C, мощный антиоксидант.',
                'effect_on_health': 'Полезен, укрепляет иммунитет, улучшает усвоение железа.',
                'daily_intake': 'Не ограничено (GRAS)',
                'foods_contain': 'Соки, напитки, консервы, мука, вино',
                'hazard_level': 1
            },
            {
                'code': 'E320',
                'name': 'BHA (Бутилгидроксианизол)',
                'name_en': 'Butylated hydroxyanisole',
                'category': 'antioxidant',
                'status': 'caution',
                'description': 'Синтетический антиоксидант.',
                'effect_on_health': 'МЕП (Международное агентство по изучению рака) считает возможным канцерогеном.',
                'daily_intake': 'До 1 мг/кг массы тела',
                'foods_contain': 'Жиры, масла, чипсы, жевательная резинка',
                'hazard_level': 4
            },
            {
                'code': 'E621',
                'name': 'Глутамат натрия',
                'name_en': 'Monosodium glutamate',
                'category': 'flavor',
                'status': 'caution',
                'description': 'Усилитель вкуса и аромата.',
                'effect_on_health': 'Может вызывать головные боли, слабость, у некоторых людей - "синдром китайского ресторана"',
                'daily_intake': 'До 30 мг/кг массы тела',
                'foods_contain': 'Чипсы, сухарики, бульонные кубики, соевый соус, фастфуд',
                'hazard_level': 2
            },
            {
                'code': 'E951',
                'name': 'Аспартам',
                'name_en': 'Aspartame',
                'category': 'sweetener',
                'status': 'caution',
                'description': 'Искусственный подсластитель.',
                'effect_on_health': 'Безопасен для большинства, но противопоказан больным фенилкетонурией.',
                'daily_intake': 'До 40 мг/кг массы тела',
                'foods_contain': 'Диетические газировки, жевательная резинка, низкокалорийные десерты',
                'hazard_level': 2
            },
            {
                'code': 'E1105',
                'name': 'Лизоцим',
                'name_en': 'Lysozyme',
                'category': 'preservative',
                'status': 'safe',
                'description': 'Природный фермент, получаемый из яичного белка.',
                'effect_on_health': 'Безопасен, кроме людей с аллергией на яйца.',
                'daily_intake': 'Не ограничено',
                'foods_contain': 'Сыры, пиво, мясные продукты',
                'hazard_level': 1
            }
        ]

        added_count = 0
        for data in additives_data:
            existing = Additive.query.filter_by(code=data['code']).first()
            if not existing:
                additive = Additive(**data)
                db.session.add(additive)
                print(f"✅ Добавлена: {data['code']} - {data['name']}")
                added_count += 1
            else:
                print(f"⏭️ Пропущена (уже есть): {data['code']}")

        db.session.commit()
        print(f"\n📊 База данных успешно заполнена! Добавлено: {added_count} записей.")
        print(f"📈 Всего записей в БД: {Additive.query.count()}")


if __name__ == '__main__':
    seed_database()