from flask import Flask, render_template, request, redirect, session, g
import sqlite3
import hashlib
import re
import os

app = Flask(__name__)
app.secret_key = 'ваш-секретный-ключ-из-случайных-символов'

# ==================== ФУНКЦИИ ИНИЦИАЛИЗАЦИИ ====================
def get_db():
    """Получение соединения с БД"""
    db = getattr(g, '_database', None)
    if db is None:
        # Создаем папку для базы данных, если ее нет
        os.makedirs('instance', exist_ok=True)
        db = g._database = sqlite3.connect('instance/database.db')
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Закрытие соединения с БД"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ==================== ВАЛИДАТОРЫ ====================
def validate_phone(phone):
    """Валидация номера телефона РФ"""
    pattern = r'^(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$'
    return re.match(pattern, phone) is not None

def validate_passport_series(series):
    """Валидация серии паспорта (4 цифры)"""
    return len(str(series)) == 4 and str(series).isdigit()

def validate_passport_number(number):
    """Валидация номера паспорта (6 цифр)"""
    return len(str(number)) == 6 and str(number).isdigit()

def validate_password(password):
    """Валидация пароля: минимум 8 символов, буквы и цифры"""
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit

def validate_organization(number):
    """Валидация номера организации (5-15 цифр)"""
    cleaned = re.sub(r'\D', '', str(number))
    return 5 <= len(cleaned) <= 15

def hash_password(password):
    """Хэширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_client_ip():
    """Получение IP-адреса клиента"""
    return request.remote_addr

# ==================== МИДЛВАРЬ ДЛЯ ПРОВЕРКИ АВТОРИЗАЦИИ ====================
@app.before_request
def check_auth():
    """Проверка авторизации перед каждым запросом"""
    # Пути, которые доступны без авторизации
    public_paths = ['/', '/login', '/register/client', '/register/cashier', 
                   '/static/', '/welcome']
    
    # Если путь публичный - пропускаем проверку
    if any(request.path.startswith(path) for path in public_paths):
        return
    
    # Если пользователь не авторизован - перенаправляем на страницу выбора регистрации
    if 'user_id' not in session:
        return redirect('/welcome')

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    """Главная страница - страница приветствия"""
    return redirect('/welcome')

@app.route('/welcome/')
def welcome():
    """Страница приветствия для новых пользователей"""
    # Если пользователь уже авторизован - перенаправляем в личный кабинет
    if 'user_id' in session:
        role = session.get('role')
        if role == 'client':
            return redirect('/client')
        elif role == 'cashier':
            return redirect('/cashier')
        elif role == 'admin':
            return redirect('/admin')
    return render_template('welcome.html')

@app.route('/login/', methods=['GET', 'POST'])
def login():
    """Страница входа (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        
        # Проверяем валидность телефона
        if not validate_phone(phone):
            return render_template('login.html', error='Неверный формат номера телефона')
        
        # Ищем пользователя в БД
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        user = cursor.fetchone()
        
        if user and user['password'] == hash_password(password):
            # ПРОСТОЙ ВАРИАНТ - без обновления last_login
            try:
                # Пытаемся обновить, но если колонки нет - игнорируем
                cursor.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user['id'],))
            except:
                pass  # Игнорируем ошибку, если колонки нет
            
            db.commit()
            
            # Создаем сессию
            session['user_id'] = user['id']
            session['phone'] = user['phone']
            session['role'] = user['role']
            
            # Редирект в зависимости от роли
            if user['role'] == 'client':
                return redirect('/client')
            elif user['role'] == 'cashier':
                return redirect('/cashier')
            elif user['role'] == 'admin':
                return redirect('/admin')
        
        return render_template('login.html', error='Неверный телефон или пароль')
    
    return render_template('login.html')

# ==================== БАЗА ДАННЫХ ====================
def get_db():
    """Получение соединения с БД"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('database.db')
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Закрытие соединения с БД"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Инициализация базы данных"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Создаем таблицу пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                passport_series TEXT NOT NULL,
                passport_number TEXT NOT NULL,
                organization_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        db.commit()

# ==================== МАРШРУТЫ ====================

@app.route('/register/client/', methods=['GET', 'POST'])
def register_client():
    """Регистрация клиента"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Валидация
        errors = []
        if not validate_phone(phone):
            errors.append('Неверный формат номера телефона')
        if not validate_passport_series(passport_series):
            errors.append('Серия паспорта должна содержать 4 цифры')
        if not validate_passport_number(passport_number):
            errors.append('Номер паспорта должен содержать 6 цифр')
        if not validate_password(password):
            errors.append('Пароль должен содержать минимум 8 символов, буквы и цифры')
        if password != password_confirm:
            errors.append('Пароли не совпадают')
        
        if errors:
            return render_template('register_client.html', errors=errors)
        
        # Проверяем, существует ли пользователь
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        if cursor.fetchone():
            return render_template('register_client.html', errors=['Пользователь с таким номером уже существует'])
        
        # Создаем пользователя
        try:
            cursor.execute('''
                INSERT INTO users (phone, password, role, passport_series, passport_number)
                VALUES (?, ?, ?, ?, ?)
            ''', (phone, hash_password(password), 'client', passport_series, passport_number))
            db.commit()
            
            # Автоматически входим
            cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            user = cursor.fetchone()
            session['user_id'] = user['id']
            session['phone'] = phone
            session['role'] = 'client'
            
            return redirect('/client')
        except:
            return render_template('register_client.html', errors=['Ошибка при регистрации'])
    
    return render_template('register_client.html')

@app.route('/register/cashier/', methods=['GET', 'POST'])
def register_cashier():
    """Регистрация кассира"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        organization_number = request.form.get('organization_number', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Валидация
        errors = []
        if not validate_phone(phone):
            errors.append('Неверный формат номера телефона')
        if not validate_passport_series(passport_series):
            errors.append('Серия паспорта должна содержать 4 цифры')
        if not validate_passport_number(passport_number):
            errors.append('Номер паспорта должен содержать 6 цифр')
        if not validate_organization(organization_number):
            errors.append('Номер организации должен содержать 5-15 цифр')
        if not validate_password(password):
            errors.append('Пароль должен содержать минимум 8 символов, буквы и цифры')
        if password != password_confirm:
            errors.append('Пароли не совпадают')
        
        if errors:
            return render_template('register_cashier.html', errors=errors)
        
        # Проверяем, существует ли пользователь
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        if cursor.fetchone():
            return render_template('register_cashier.html', errors=['Пользователь с таким номером уже существует'])
        
        # Создаем пользователя
        try:
            cursor.execute('''
                INSERT INTO users (phone, password, role, passport_series, passport_number, organization_number)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (phone, hash_password(password), 'cashier', passport_series, passport_number, organization_number))
            db.commit()
            
            # Автоматически входим
            cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            user = cursor.fetchone()
            session['user_id'] = user['id']
            session['phone'] = phone
            session['role'] = 'cashier'
            
            return redirect('/cashier')
        except:
            return render_template('register_cashier.html', errors=['Ошибка при регистрации'])
    
    return render_template('register_cashier.html')

@app.route('/client/')
def client_page():
    """Личный кабинет клиента"""
    if 'user_id' not in session or session.get('role') != 'client':
        return redirect('/login')
    
    return render_template('client.html', phone=session.get('phone'))

@app.route('/cashier/')
def cashier_page():
    """Личный кабинет кассира"""
    if 'user_id' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    return render_template('cashier.html', phone=session.get('phone'))

@app.route('/logout/')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect('/login')

# ==================== МАРШРУТЫ КЛИЕНТА ====================
@app.route('/client/search/', methods=['GET', 'POST'])
def search_flights():
    """Поиск рейсов"""
    if 'user_id' not in session or session.get('role') != 'client':
        return redirect('/login')
    
    flights = []
    
    if request.method == 'POST':
        departure = request.form.get('departure', '').strip()
        arrival = request.form.get('arrival', '').strip()
        date = request.form.get('date', '').strip()
        
        db = get_db()
        cursor = db.cursor()
        
        query = "SELECT * FROM flights WHERE status = 'active' AND seats_available > 0"
        params = []
        
        if departure:
            query += " AND departure_city LIKE ?"
            params.append(f'%{departure}%')
        
        if arrival:
            query += " AND arrival_city LIKE ?"
            params.append(f'%{arrival}%')
        
        if date:
            query += " AND departure_time LIKE ?"
            params.append(f'{date}%')
        
        cursor.execute(query, params)
        flights = cursor.fetchall()
    
    return render_template('search_flights.html', flights=flights)

@app.route('/client/buy/<int:flight_id>/', methods=['GET', 'POST'])
def buy_ticket(flight_id):
    """Покупка билета"""
    if 'user_id' not in session or session.get('role') != 'client':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Получаем информацию о рейсе
    cursor.execute("SELECT * FROM flights WHERE id = ? AND status = 'active'", (flight_id,))
    flight = cursor.fetchone()
    
    if not flight:
        return redirect('/client/search')
    
    if request.method == 'POST':
        passenger_name = request.form.get('passenger_name', '').strip()
        passenger_passport = request.form.get('passenger_passport', '').strip()
        
        if not passenger_name or not passenger_passport:
            return render_template('buy_ticket.html', flight=flight, error='Заполните все поля')
        
        # Симуляция оплаты (в реальном проекте здесь был бы платежный шлюз)
        # В учебном проекте просто считаем, что оплата прошла успешно
        
        # Покупаем билет
        try:
            # Создаем билет
            cursor.execute('''
                INSERT INTO tickets (user_id, flight_id, passenger_name, passenger_passport, status)
                VALUES (?, ?, ?, ?, 'active')
            ''', (session['user_id'], flight_id, passenger_name, passenger_passport))
            
            # Уменьшаем количество доступных мест
            cursor.execute('''
                UPDATE flights 
                SET seats_available = seats_available - 1 
                WHERE id = ? AND seats_available > 0
            ''', (flight_id,))
            
            db.commit()
            
            # Получаем ID нового билета
            ticket_id = cursor.lastrowid
            
            # Симуляция отправки на почту
            print(f"[СИМУЛЯЦИЯ] Билет №{ticket_id} отправлен на email пользователя")

            # ВАЖНО: записываем продажу в таблицу sales
            cursor.execute('''
                INSERT INTO sales (ticket_id, cashier_id, amount, payment_method, sale_date)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (ticket_id, flight['staff_id'], flight['price'], "cash"))
            
            db.commit()
            
            return redirect('/client/my_tickets?success=true')
            
        except Exception as e:
            db.rollback()
            print(e)
            return render_template('buy_ticket.html', flight=flight, error='Ошибка при покупке билета')
    
    return render_template('buy_ticket.html', flight=flight)

@app.route('/client/my_tickets/')
def my_tickets():
    """Список купленных билетов"""
    if 'user_id' not in session or session.get('role') != 'client':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Получаем билеты пользователя
    cursor.execute('''
        SELECT t.*, f.flight_number, f.departure_city, f.arrival_city, 
               f.departure_time, f.arrival_time, f.price
        FROM tickets t
        JOIN flights f ON t.flight_id = f.id
        WHERE t.user_id = ? AND t.status = 'active'
        ORDER BY t.purchase_date DESC
    ''', (session['user_id'],))
    
    tickets = cursor.fetchall()
    
    success = request.args.get('success') == 'true'
    
    return render_template('my_tickets.html', tickets=tickets, success=success)

@app.route('/client/return/<int:ticket_id>/', methods=['GET', 'POST'])
def return_ticket(ticket_id):
    """Возврат билета"""
    if 'user_id' not in session or session.get('role') != 'client':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Проверяем, что билет принадлежит пользователю
    cursor.execute('''
        SELECT t.*, f.flight_number, f.departure_city, f.arrival_city, 
               f.departure_time, f.price
        FROM tickets t
        JOIN flights f ON t.flight_id = f.id
        WHERE t.id = ? AND t.user_id = ? AND t.status = 'active'
    ''', (ticket_id, session['user_id']))
    
    ticket = cursor.fetchone()
    
    if not ticket:
        return redirect('/client/my_tickets')
    
    if request.method == 'POST':
        confirm = request.form.get('confirm')
        
        if confirm == 'yes':
            try:
                cursor.execute('''
                SELECT *
                FROM flights
                WHERE id = ?
                ''', (ticket['flight_id'],))

                flight = cursor.fetchone()

                # Регистрируем возврат
                cursor.execute('''
                    INSERT INTO returns (ticket_id, cashier_id, reason, explanation, return_date)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (ticket_id, flight['staff_id'], " ", " "))
                
                db.commit()
                # Возвращаем билет
                cursor.execute("UPDATE tickets SET status = 'returned' WHERE id = ?", (ticket_id,))
                
                # Увеличиваем количество доступных мест
                cursor.execute('''
                    UPDATE flights 
                    SET seats_available = seats_available + 1 
                    WHERE id = ?
                ''', (ticket['flight_id'],))
                
                db.commit()
                
                # Симуляция возврата денег
                print(f"[СИМУЛЯЦИЯ] Возврат {ticket['price']} руб. на карту пользователя")
                
                return redirect('/client/my_tickets?returned=true')
                
            except Exception as e:
                db.rollback()
                print(e)
                return render_template('return_ticket.html', ticket=ticket, error='Ошибка при возврате билета')
        else:
            return redirect('/client/my_tickets')
    
    return render_template('return_ticket.html', ticket=ticket)


# ==================== ОБНОВЛЯЕМ ПРОДАЖУ БИЛЕТА ====================
@app.route('/cashier/sell/<int:flight_id>/', methods=['GET', 'POST'])
def cashier_sell(flight_id):
    """Продажа билета через кассу (ПРОСТАЯ ВЕРСИЯ)"""
    if 'user_id' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Получаем рейс
    cursor.execute("SELECT * FROM flights WHERE id = ?", (flight_id,))
    flight = cursor.fetchone()
    
    if not flight:
        print('Рейс не найден', 'error')
        return redirect('/cashier/search')
    
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        passenger_name = request.form.get('passenger_name', '').strip()
        payment_method = request.form.get('payment_method', 'cash')
        
        if not phone or not passenger_name:
            print('Заполните все поля', 'error')
            return render_template('cashier_sell.html', flight=flight)
        
        try:
            # Ищем клиента
            cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            user = cursor.fetchone()
            
            if not user:
                print('Клиент не найден', 'error')
                return render_template('cashier_sell.html', flight=flight)
            
            # Уменьшаем места
            cursor.execute('''
                UPDATE flights 
                SET seats_available = seats_available - 1 
                WHERE id = ? AND seats_available > 0
            ''', (flight_id,))
            
            # Создаем билет
            cursor.execute('''
                INSERT INTO tickets (user_id, flight_id, passenger_name, passenger_passport, status)
                VALUES (?, ?, ?, ?, 'active')
            ''', (user['id'], flight_id, passenger_name, f"из регистрации"))
            
            ticket_id = cursor.lastrowid
            
            # ВАЖНО: записываем продажу в таблицу sales
            cursor.execute('''
                INSERT INTO sales (ticket_id, cashier_id, amount, payment_method, sale_date)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (ticket_id, session['user_id'], flight['price'], payment_method))
            
            db.commit()
            
            print(f"✅ Продажа записана! Билет: {ticket_id}, Кассир: {session['user_id']}, Сумма: {flight['price']}")
            
            print('Билет продан!', 'success')
            return redirect(f'/cashier/receipt/{ticket_id}')
            
        except Exception as e:
            db.rollback()
            print(f"❌ Ошибка при продаже: {e}")
            print(f'Ошибка: {str(e)}', 'error')
            return render_template('cashier_sell.html', flight=flight)
    
    return render_template('cashier_sell.html', flight=flight)

# ==================== ОБНОВЛЯЕМ ОТЧЕТ ====================
@app.route('/cashier/daily_report/', methods=['GET', 'POST'])
def daily_report():
    """Отчет по дневной выручке (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    if 'user_id' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    report_date = request.form.get('date', '')
    
    if not report_date:
        from datetime import datetime
        report_date = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # ПРОСТОЙ ЗАПРОС БЕЗ СЛОЖНЫХ JOIN
        # 1. Продажи за день
        cursor.execute('''
            SELECT 
                COUNT(*) as sales_count,
                COALESCE(SUM(amount), 0) as total_sales,
                COALESCE(SUM(amount) * 0.1, 0) as commission
            FROM sales 
            WHERE DATE(sale_date) = ? AND cashier_id = ?
        ''', (report_date, session['user_id']))
        
        sales_data = cursor.fetchone()
        
        # 2. Возвраты за день
        cursor.execute('''
            SELECT 
                COUNT(*) as returns_count,
                COALESCE((
                    SELECT SUM(f.price)
                    FROM returns r2
                    JOIN tickets t2 ON r2.ticket_id = t2.id
                    JOIN flights f ON t2.flight_id = f.id
                    WHERE DATE(r2.return_date) = ? AND r2.cashier_id = ?
                ), 0) as total_returns
            FROM returns
            WHERE DATE(return_date) = ? AND cashier_id = ?
        ''', (report_date, session['user_id'], report_date, session['user_id']))
        
        returns_data = cursor.fetchone()
        
        # 3. Детализация продаж
        cursor.execute('''
            SELECT s.*, f.flight_number, t.passenger_name, 
                   f.price as ticket_price, f.airplane
            FROM sales s
            JOIN tickets t ON s.ticket_id = t.id
            JOIN flights f ON t.flight_id = f.id
            WHERE DATE(s.sale_date) = ? AND s.cashier_id = ?
            ORDER BY s.sale_date DESC
        ''', (report_date, session['user_id']))
        
        sales_details = cursor.fetchall()
        
        # 4. Детализация возвратов
        cursor.execute('''
            SELECT r.*, f.flight_number, t.passenger_name, 
                   f.price as ticket_price, f.airplane
            FROM returns r
            JOIN tickets t ON r.ticket_id = t.id
            JOIN flights f ON t.flight_id = f.id
            WHERE DATE(r.return_date) = ? AND r.cashier_id = ?
            ORDER BY r.return_date DESC
        ''', (report_date, session['user_id']))
        
        returns_details = cursor.fetchall()
        
        # 5. Статистика по созданным рейсам
        cursor.execute('''
            SELECT 
                COUNT(*) as flights_created,
                COALESCE(SUM(seats_available), 0) as total_seats,
                COALESCE(SUM(price * seats_available), 0) as potential_revenue
            FROM flights 
            WHERE staff_id = ? AND DATE(departure_time) = ?
        ''', (session['user_id'], report_date))
        
        flights_stats = cursor.fetchone()
        
        # Формируем единый отчет
        report = {
            'sales_count': sales_data['sales_count'] if sales_data else 0,
            'total_sales': sales_data['total_sales'] if sales_data else 0,
            'commission': sales_data['commission'] if sales_data else 0,
            'returns_count': returns_data['returns_count'] if returns_data else 0,
            'total_returns': returns_data['total_returns'] if returns_data else 0,
            'commission_loss': (returns_data['total_returns'] * 0.1) if returns_data else 0
        }
        
        return render_template('daily_report.html',
                             report_date=report_date,
                             report=report,
                             flights_stats=flights_stats,
                             sales_details=sales_details,
                             returns_details=returns_details)
    
    except Exception as e:
        import traceback
        print(f"Ошибка в daily_report: {str(e)}")
        print(traceback.format_exc())
        print(f'Ошибка при формировании отчета: {str(e)}', 'error')
        return redirect('/cashier')

# ==================== МАРШРУТЫ КАССИРА (ИСПРАВЛЕННЫЕ) ====================

@app.route('/cashier/search', methods=['GET', 'POST'])
def cashier_search():
    """Поиск рейсов для кассира"""
    if 'user_id' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    flights = []
    
    if request.method == 'POST':
        departure = request.form.get('departure', '').strip()
        arrival = request.form.get('arrival', '').strip()
        date = request.form.get('date', '').strip()
        flight_number = request.form.get('flight_number', '').strip()
        
        db = get_db()
        cursor = db.cursor()
        
        query = "SELECT * FROM flights WHERE status = 'active'"
        params = []
        
        if departure:
            query += " AND departure_city LIKE ?"
            params.append(f'%{departure}%')
        
        if arrival:
            query += " AND arrival_city LIKE ?"
            params.append(f'%{arrival}%')
        
        if date:
            query += " AND departure_time LIKE ?"
            params.append(f'{date}%')
        
        if flight_number:
            query += " AND flight_number LIKE ?"
            params.append(f'%{flight_number}%')
        
        cursor.execute(query, params)
        flights = cursor.fetchall()
    
    return render_template('cashier_search.html', flights=flights)

@app.route('/cashier/receipt/<int:ticket_id>/')
def cashier_receipt(ticket_id):
    """Чек продажи"""
    if 'user_id' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT t.*, f.flight_number, f.departure_city, f.arrival_city, 
               f.departure_time, f.arrival_time, f.price,
               u.phone as customer_phone, s.payment_method
        FROM tickets t
        JOIN flights f ON t.flight_id = f.id
        JOIN users u ON t.user_id = u.id
        LEFT JOIN sales s ON t.id = s.ticket_id
        WHERE t.id = ?
    ''', (ticket_id,))
    
    ticket = cursor.fetchone()
    
    if not ticket:
        print('Билет не найден', 'error')
        return redirect('/cashier/search')
    
    return render_template('cashier_receipt.html', ticket=ticket)

@app.route('/cashier/return/', methods=['GET', 'POST'])
def cashier_return():
    """Возврат билета через кассу"""
    if 'user_id' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    ticket = None
    reason_options = [
        ('passenger_request', 'По желанию пассажира'),
        ('flight_cancelled', 'Отмена рейса'),
        ('passenger_illness', 'Болезнь пассажира'),
        ('schedule_change', 'Изменение расписания'),
        ('other', 'Другая причина')
    ]
    
    if request.method == 'POST' and 'search' in request.form:
        # Поиск билета
        ticket_number = request.form.get('ticket_number', '').strip()
        passenger_passport = request.form.get('passenger_passport', '').strip()
        phone = request.form.get('phone', '').strip()
        
        query = '''
            SELECT t.*, f.flight_number, f.departure_city, f.arrival_city, 
                   f.departure_time, f.price, u.phone
            FROM tickets t
            JOIN flights f ON t.flight_id = f.id
            JOIN users u ON t.user_id = u.id
            WHERE t.status = 'active'
        '''
        params = []
        
        if ticket_number:
            query += " AND t.id = ?"
            params.append(ticket_number)
        
        if passenger_passport:
            query += " AND t.passenger_passport LIKE ?"
            params.append(f'%{passenger_passport}%')
        
        if phone:
            query += " AND u.phone LIKE ?"
            params.append(f'%{phone}%')
        
        cursor.execute(query, params)
        ticket = cursor.fetchone()
    
    elif request.method == 'POST' and 'return' in request.form:
        # Возврат билета
        ticket_id = request.form.get('ticket_id')
        reason = request.form.get('reason', 'passenger_request')
        explanation = request.form.get('explanation', '').strip()
        
        cursor.execute('''
            SELECT t.*, f.id as flight_id
            FROM tickets t
            JOIN flights f ON t.flight_id = f.id
            WHERE t.id = ? AND t.status = 'active'
        ''', (ticket_id,))
        
        ticket = cursor.fetchone()
        
        if ticket:
            try:
                # Возвращаем билет
                cursor.execute("UPDATE tickets SET status = 'returned' WHERE id = ?", (ticket_id,))
                
                # Увеличиваем количество доступных мест
                cursor.execute('''
                    UPDATE flights 
                    SET seats_available = seats_available + 1 
                    WHERE id = ?
                ''', (ticket['flight_id'],))
                
                # Регистрируем возврат
                cursor.execute('''
                    INSERT INTO returns (ticket_id, cashier_id, reason, explanation, return_date)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (ticket_id, session['user_id'], reason, explanation))
                
                db.commit()
                
                print('Билет успешно возвращен!', 'success')
                return redirect(f'/cashier/return_success/{ticket_id}')
                
            except Exception as e:
                db.rollback()
                print(f'Ошибка при возврате билета: {str(e)}', 'error')
    
    return render_template('cashier_return.html', 
                         ticket=ticket, 
                         reason_options=reason_options)

@app.route('/cashier/return_success/<int:ticket_id>/')
def return_success(ticket_id):
    """Успешный возврат"""
    if 'user_id' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT t.*, f.flight_number, f.price, r.reason, r.explanation
        FROM tickets t
        JOIN flights f ON t.flight_id = f.id
        JOIN returns r ON t.id = r.ticket_id
        WHERE t.id = ?
    ''', (ticket_id,))
    
    ticket = cursor.fetchone()
    
    if not ticket:
        print('Информация о возврате не найдена', 'error')
        return redirect('/cashier/return')
    
    return render_template('cashier_return_success.html', ticket=ticket)

# ==================== ОБНОВЛЯЕМ ИНИЦИАЛИЗАЦИЮ БАЗЫ ====================
def init_flights_table():
    """Инициализация таблиц рейсов и билетов (обновленная)"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Таблица рейсов (добавляем поля для кассира)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_number TEXT NOT NULL,
                departure_city TEXT NOT NULL,
                arrival_city TEXT NOT NULL,
                departure_time TEXT NOT NULL,
                arrival_time TEXT NOT NULL,
                price REAL NOT NULL,
                seats_available INTEGER NOT NULL,
                airplane TEXT,
                staff_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_id) REFERENCES users (id)
            )
        ''')
        
        # Остальные таблицы без изменений...
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                flight_id INTEGER NOT NULL,
                passenger_name TEXT NOT NULL,
                passenger_passport TEXT NOT NULL,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (flight_id) REFERENCES flights (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                cashier_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT DEFAULT 'cash',
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id),
                FOREIGN KEY (cashier_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                cashier_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                explanation TEXT,
                return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id),
                FOREIGN KEY (cashier_id) REFERENCES users (id)
            )
        ''')
        
        db.commit()

# ==================== МАРШРУТЫ АДМИНИСТРАТОРА ====================

@app.route('/admin/')
def admin_panel():
    """Главная панель администратора"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Статистика
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'cashier'")
    cashiers_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'client'")
    clients_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM flights")
    flights_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'active'")
    active_tickets = cursor.fetchone()[0]

    
    return render_template('admin.html',
                         phone=session.get('phone'),
                         cashiers_count=cashiers_count,
                         clients_count=clients_count,
                         flights_count=flights_count,
                         active_tickets=active_tickets)

# ==================== УПРАВЛЕНИЕ РЕЙСАМИ ====================

@app.route('/admin/flights/', methods=['GET', 'POST'])
def admin_flights():
    """Управление рейсами"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    status_arg = request.args.get('status')

    db = get_db()
    cursor = db.cursor()
    
    flights = []
    search_performed = False

    status_arg = request.args.get('status')
    
    if status_arg:
        query = "SELECT f.*, u.phone as cashier_phone FROM flights f LEFT JOIN users u ON f.staff_id = u.id WHERE 1=1 AND status = ?"
        params = [status_arg]

        cursor.execute(query, params)
        flights = cursor.fetchall()
        search_performed = True
    
    if request.method == 'POST':
        # Поиск рейсов
        flight_number = request.form.get('flight_number', '').strip()
        departure_city = request.form.get('departure_city', '').strip()
        arrival_city = request.form.get('arrival_city', '').strip()
        status = request.form.get('status', '').strip()
        
        query = "SELECT f.*, u.phone as cashier_phone FROM flights f LEFT JOIN users u ON f.staff_id = u.id WHERE 1=1"
        params = []
        
        if flight_number:
            query += " AND f.flight_number LIKE ?"
            params.append(f'%{flight_number}%')
        
        if departure_city:
            query += " AND f.departure_city LIKE ?"
            params.append(f'%{departure_city}%')
        
        if arrival_city:
            query += " AND f.arrival_city LIKE ?"
            params.append(f'%{arrival_city}%')
        
        if status:
            query += " AND f.status = ?"
            params.append(status)
        
        query += " ORDER BY f.departure_time DESC"
        
        cursor.execute(query, params)
        flights = cursor.fetchall()
        search_performed = True
    
    # Если не было поиска, показываем все рейсы
    if not search_performed:
        cursor.execute('''
            SELECT f.*, u.phone as cashier_phone 
            FROM flights f 
            LEFT JOIN users u ON f.staff_id = u.id 
            ORDER BY f.departure_time DESC 
            LIMIT 50
        ''')
        flights = cursor.fetchall()
    
    return render_template('admin_flights.html', 
                         flights=flights,
                         search_performed=search_performed)

@app.route('/admin/flights/add/', methods=['GET', 'POST'])
def admin_add_flight():
    """Добавление рейса администратором"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    if request.method == 'POST':
        flight_number = request.form.get('flight_number', '').strip()
        departure_city = request.form.get('departure_city', '').strip()
        arrival_city = request.form.get('arrival_city', '').strip()
        departure_time = request.form.get('departure_time', '').strip()
        arrival_time = request.form.get('arrival_time', '').strip()
        price = request.form.get('price', '0').strip()
        seats_available = request.form.get('seats_available', '0').strip()
        airplane = request.form.get('airplane', '').strip()
        cashier_id = request.form.get('cashier_id', '').strip()
        
        # Валидация
        errors = []
        if not flight_number:
            errors.append('Введите номер рейса')
        if not departure_city:
            errors.append('Введите город отправления')
        if not arrival_city:
            errors.append('Введите город прибытия')
        if not departure_time:
            errors.append('Введите время вылета')
        if not arrival_time:
            errors.append('Введите время прилета')
        if not price.isdigit() or int(price) <= 0:
            errors.append('Введите корректную цену')
        if not seats_available.isdigit() or int(seats_available) <= 0:
            errors.append('Введите корректное количество мест')
        
        if errors:
            print(', '.join(errors), 'error')
            return redirect('/admin/flights/add')
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Если указан кассир - проверяем его существование
            if cashier_id:
                cursor.execute("SELECT * FROM users WHERE phone = ? AND role = 'cashier'", (cashier_id,))
                staff = cursor.fetchone()
                if staff:
                    cursor.execute('''
                INSERT INTO flights 
                (flight_number, departure_city, arrival_city, 
                 departure_time, arrival_time, price, seats_available, 
                 airplane, staff_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            ''', (flight_number, departure_city, arrival_city,
                  departure_time, arrival_time, int(price), 
                  int(seats_available), airplane, staff['id']))
                    
            cursor.execute('''
                INSERT INTO flights 
                (flight_number, departure_city, arrival_city, 
                 departure_time, arrival_time, price, seats_available, 
                 airplane, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            ''', (flight_number, departure_city, arrival_city,
                  departure_time, arrival_time, int(price), 
                  int(seats_available), airplane))
            
            db.commit()
            
            print('Рейс успешно добавлен', 'success')
            return redirect('/admin/flights')
            
        except Exception as e:
            print(f'Ошибка при добавлении рейса: {str(e)}', 'error')
    
    return render_template('admin_flights_edit.html', flight=None, action='add')

@app.route('/admin/flights/edit/<int:flight_id>/', methods=['GET', 'POST'])
def admin_edit_flight(flight_id):
    """Редактирование рейса"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Получаем рейс
    cursor.execute('''
        SELECT f.*, u.phone as cashier_phone 
        FROM flights f 
        LEFT JOIN users u ON f.staff_id = u.id 
        WHERE f.id = ?
    ''', (flight_id,))
    
    flight = cursor.fetchone()
    
    if not flight:
        print('Рейс не найден', 'error')
        return redirect('/admin/flights')
    
    if request.method == 'POST':
        flight_number = request.form.get('flight_number', '').strip()
        departure_city = request.form.get('departure_city', '').strip()
        arrival_city = request.form.get('arrival_city', '').strip()
        departure_time = request.form.get('departure_time', '').strip()
        arrival_time = request.form.get('arrival_time', '').strip()
        price = request.form.get('price', '0').strip()
        seats_available = request.form.get('seats_available', '0').strip()
        airplane = request.form.get('airplane', '').strip()
        status = request.form.get('status', 'active').strip()
        cashier_id = request.form.get('cashier_id', '').strip()
        
        try:
            # Если указан кассир - проверяем его существование
            staff_id = None
            if cashier_id:
                cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'cashier'", (cashier_id,))
                if cursor.fetchone():
                    staff_id = cashier_id
            
            cursor.execute('''
                UPDATE flights SET
                    flight_number = ?,
                    departure_city = ?,
                    arrival_city = ?,
                    departure_time = ?,
                    arrival_time = ?,
                    price = ?,
                    seats_available = ?,
                    airplane = ?,
                    status = ?,
                    created_by = ?
                WHERE id = ?
            ''', (flight_number, departure_city, arrival_city,
                  departure_time, arrival_time, 
                  int(float(price)),
                  int(float(seats_available)),
                  airplane, status, staff_id, flight_id))
            
            db.commit()
            
            print('Рейс успешно обновлен', 'success')
            return redirect('/admin/flights')
            
        except Exception as e:
            print(f'Ошибка при обновлении рейса: {str(e)}', 'error')
    
    # Получаем список кассиров для выбора
    cursor.execute("SELECT id, phone FROM users WHERE role = 'cashier'")
    cashiers = cursor.fetchall()
    
    return render_template('admin_flights_edit.html', 
                         flight=flight, 
                         cashiers=cashiers,
                         action='edit')

@app.route('/admin/flights/delete/<int:flight_id>/')
def admin_delete_flight(flight_id):
    """Удаление рейса"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Проверяем, есть ли активные билеты на этот рейс
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE flight_id = ? AND status = 'active'", (flight_id,))
    active_tickets = cursor.fetchone()[0]
    
    if active_tickets > 0:
        print(f'Нельзя удалить рейс с {active_tickets} активными билетами', 'error')
        return redirect('/admin/flights')
    
    try:
        cursor.execute("DELETE FROM flights WHERE id = ?", (flight_id,))
        db.commit()
        print('Рейс успешно удален', 'success')
    except Exception as e:
        print(f'Ошибка при удалении рейса: {str(e)}', 'error')
    
    return redirect('/admin/flights')

# ==================== УПРАВЛЕНИЕ СОТРУДНИКАМИ ====================

@app.route('/admin/staff/', methods=['GET', 'POST'])
def admin_staff():
    """Управление сотрудниками"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    db = get_db()
    cursor = db.cursor()

    staff = []
    search_performed = False

    role_arg = request.args.get('role')
    
    if role_arg:
        query = "SELECT * FROM users WHERE role = ?"
        params = [role_arg]

        cursor.execute(query, params)
        staff = cursor.fetchall()
        search_performed = True
    
    if request.method == 'POST':
        # Поиск сотрудников
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', '').strip()
        
        query = "SELECT * FROM users WHERE role IN ('cashier', 'admin')"
        params = []
        
        if phone:
            query += " AND phone LIKE ?"
            params.append(f'%{phone}%')
        
        if role:
            query += " AND role = ?"
            params.append(role)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        staff = cursor.fetchall()
        search_performed = True
    
    # Если не было поиска, показываем всех сотрудников
    if not search_performed:
        cursor.execute("SELECT * FROM users WHERE role IN ('cashier', 'admin') ORDER BY created_at DESC")
        staff = cursor.fetchall()
    
    return render_template('admin_staff.html', 
                         staff=staff,
                         search_performed=search_performed)

@app.route('/admin/staff/add/', methods=['GET', 'POST'])
def admin_add_staff():
    """Добавление сотрудника"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'cashier').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        organization_number = request.form.get('organization_number', '').strip()
        
        # Валидация
        errors = []
        if not validate_phone(phone):
            errors.append('Неверный формат телефона')
        if not validate_password(password):
            errors.append('Пароль должен содержать минимум 8 символов, буквы и цифры')
        if role not in ['cashier', 'admin']:
            errors.append('Неверная роль')
        if not validate_passport_series(passport_series):
            errors.append('Серия паспорта должна содержать 4 цифры')
        if not validate_passport_number(passport_number):
            errors.append('Номер паспорта должен содержать 6 цифр')
        if role == 'cashier' and not validate_organization(organization_number):
            errors.append('Номер организации должен содержать 5-15 цифр')
        
        if errors:
            for error in errors:
                print(error, 'error')
            return redirect('/admin/staff/add')
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Проверяем, не существует ли уже пользователь
            cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            if cursor.fetchone():
                print('Пользователь с таким телефоном уже существует', 'error')
                return redirect('/admin/staff/add')
            
            cursor.execute('''
                INSERT INTO users 
                (phone, password, role, passport_series, passport_number, organization_number)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (phone, hash_password(password), role, 
                  passport_series, passport_number, 
                  organization_number if role == 'cashier' else None))
            
            db.commit()
            
            print('Сотрудник успешно добавлен', 'success')
            return redirect('/admin/staff')
            
        except Exception as e:
            print(f'Ошибка при добавлении сотрудника: {str(e)}', 'error')
    
    return render_template('admin_staff_add.html')

@app.route('/admin/staff/edit/<int:staff_id>/', methods=['GET', 'POST'])
def admin_edit_staff(staff_id):
    """Редактирование сотрудника"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    db = get_db()
    cursor = db.cursor()
    
    # Получаем сотрудника
    cursor.execute("SELECT * FROM users WHERE id = ? AND role IN ('cashier', 'admin')", (staff_id,))
    staff = cursor.fetchone()
    
    if not staff:
        print('Сотрудник не найден', 'error')
        return redirect('/admin/staff')
    
    # Нельзя редактировать себя
    if staff['id'] == session['user_id']:
        print('Вы не можете редактировать свой собственный профиль', 'error')
        return redirect('/admin/staff')
    
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'cashier').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        organization_number = request.form.get('organization_number', '').strip()
        status = request.form.get('status', 'active').strip()
        
        # Валидация
        errors = []
        if not validate_phone(phone):
            errors.append('Неверный формат телефона')
        if role not in ['cashier', 'admin']:
            errors.append('Неверная роль')
        if not validate_passport_series(passport_series):
            errors.append('Серия паспорта должна содержать 4 цифры')
        if not validate_passport_number(passport_number):
            errors.append('Номер паспорта должен содержать 6 цифр')
        if role == 'cashier' and not validate_organization(organization_number):
            errors.append('Номер организации должен содержать 5-15 цифр')
        
        if errors:
            for error in errors:
                print(error, 'error')
            return redirect(f'/admin/staff/edit/{staff_id}')
        
        try:
            # Проверяем, не занят ли телефон другим пользователем
            cursor.execute("SELECT id FROM users WHERE phone = ? AND id != ?", (phone, staff_id))
            if cursor.fetchone():
                print('Телефон уже используется другим пользователем', 'error')
                return redirect(f'/admin/staff/edit/{staff_id}')
            
            cursor.execute('''
                UPDATE users SET
                    phone = ?,
                    role = ?,
                    passport_series = ?,
                    passport_number = ?,
                    organization_number = ?
                WHERE id = ?
            ''', (phone, role, passport_series, passport_number,
                  organization_number if role == 'cashier' else None,
                  staff_id))
            
            db.commit()
            
            print('Сотрудник успешно обновлен', 'success')
            return redirect('/admin/staff')
            
        except Exception as e:
            print(f'Ошибка при обновлении сотрудника: {str(e)}', 'error')
    
    return render_template('admin_staff_edit.html', staff=staff)

@app.route('/admin/staff/delete/<int:staff_id>/')
def admin_delete_staff(staff_id):
    """Удаление сотрудника"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    # Нельзя удалить себя
    if staff_id == session['user_id']:
        print('Вы не можете удалить себя', 'error')
        return redirect('/admin/staff')
    
    db = get_db()
    cursor = db.cursor()
    
    # Проверяем, есть ли у кассира созданные рейсы
    cursor.execute("SELECT COUNT(*) FROM flights WHERE staff_id = ?", (staff_id,))
    flights_count = cursor.fetchone()[0]
    
    if flights_count > 0:
        print(f'Нельзя удалить кассира с {flights_count} созданными рейсами', 'error')
        return redirect('/admin/staff')
    
    try:
        cursor.execute("DELETE FROM users WHERE id = ?", (staff_id,))
        db.commit()
        print('Сотрудник успешно удален', 'success')
    except Exception as e:
        print(f'Ошибка при удалении сотрудника: {str(e)}', 'error')
    
    return redirect('/admin/staff')

# ==================== ОБНОВЛЕННЫЙ ЗАПУСК ====================
if __name__ == '__main__':
    # Создаем все таблицы если их нет
    if not os.path.exists('database.db'):
        with app.app_context():
            init_db()  # Создаем таблицу пользователей
            init_flights_table()  # Создаем таблицы рейсов и билетов
            
            # Дополнительные таблицы для кассира
            db = get_db()
            cursor = db.cursor()

            # Проверяем, есть ли пользователи в системе
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
        
            # Если база пустая, создаем администратора по умолчанию
            if user_count == 0:
                print("[SYSTEM] База данных пустая. Создаю администратора по умолчанию...")
            
                # Хэш пароля 'admin123'
                admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
            
                cursor.execute('''
                    INSERT INTO users (phone, password, role, passport_series, passport_number, organization_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('+79990000000', admin_password, 'admin', '0000', '000000', 'ADMIN001'))
            
            # Таблица продаж (для отчетов)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    cashier_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT DEFAULT 'cash',
                    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets (id),
                    FOREIGN KEY (cashier_id) REFERENCES users (id)
                )
            ''')
            
            # Таблица возвратов (для отчетов)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    cashier_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    explanation TEXT,
                    return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets (id),
                    FOREIGN KEY (cashier_id) REFERENCES users (id)
                )
            ''')
            
            db.commit()
    
    app.run(debug=True, port=5000)