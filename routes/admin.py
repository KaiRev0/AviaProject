from flask import Blueprint, request, session, redirect, render_template, flash
from models.models import db, User, Flight, Ticket
from sqlalchemy import desc
from libs.libs import *
from datetime import datetime

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/admin/')
def admin_panel():
    """Главная панель администратора"""
    if 'phone' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    # Статистика
    stmt = db.select(func.count()).select_from(User).where(User.role == 'cashier')
    cashiers_count = db.session.execute(stmt).scalar()
    
    stmt = db.select(func.count()).select_from(User).where(User.role == 'client')
    clients_count = db.session.execute(stmt).scalar()
    
    stmt = db.select(func.count()).select_from(Flight)
    flights_count = db.session.execute(stmt).scalar()
    
    stmt = db.select(func.count()).select_from(Ticket).where(Ticket.status == 'active')
    active_tickets = db.session.execute(stmt).scalar()

    stmt = db.select(User).where(User.phone == session.get('phone'))
    user = db.session.execute(stmt).scalar()
    
    return render_template('admin.html',
                         name=user.name,
                         cashiers_count=cashiers_count,
                         clients_count=clients_count,
                         flights_count=flights_count,
                         active_tickets=active_tickets)

# ==================== УПРАВЛЕНИЕ РЕЙСАМИ ====================

@admin_bp.route('/admin/flights', methods=['GET', 'POST'])
def admin_flights():
    """Управление рейсами"""
    if 'phone' not in session or session.get('role') != 'admin':
        return redirect('/login')
    
    search_performed = False

    stmt = db.select(Flight)
    
    if request.method == 'POST':
        # Поиск рейсов
        search_performed = True

        flight_number = request.form.get('flight_number', '').strip()
        departure_city = request.form.get('departure_city', '').strip()
        arrival_city = request.form.get('arrival_city', '').strip()
        status = request.form.get('status', '').strip()
        
        if flight_number:
            stmt = stmt.where(Flight.flight_number.ilike(f"{flight_number}%%"))
        
        if departure_city:
            stmt = stmt.where(Flight.departure_city.ilike(f"{departure_city}%%"))
        
        if arrival_city:
            stmt = stmt.where(Flight.arrival_city.ilike(f"{arrival_city}%%"))
        
        if status:
            stmt = stmt.where(Flight.status == status)
        
    else:
        stmt = stmt.limit(50)

    stmt = stmt.order_by(desc(Flight.departure_time))

    flights = db.session.execute(stmt).scalars()
    stmt = db.select(func.count()).select_from(Flight)
    count = db.session.execute(stmt).scalar()
    stmt = db.select(func.count()).select_from(Flight).where(Flight.status == 'active')
    active_count = db.session.execute(stmt).scalar()
    stmt = db.select(func.count()).select_from(Flight).where(Flight.status == 'disabled')
    cancelled_count = db.session.execute(stmt).scalar()
    
    return render_template('admin_flights.html', 
                         flights=flights,
                         count=count,
                         active_count=active_count,
                         cancelled_count=cancelled_count,
                         search_performed=search_performed)

@admin_bp.route('/admin/flights/add', methods=['GET', 'POST'])
def admin_add_flight():
    """Добавление рейса администратором"""
    if 'phone' not in session or session.get('role') != 'admin':
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
            flash(', '.join(errors), 'error')
            return redirect('/admin/flights/add')
        
        try:
            flight = Flight(
                flight_number = flight_number,
                departure_city = departure_city,
                arrival_city = arrival_city,
                departure_time = datetime.strptime(departure_time[:10], "%Y-%M-%d"),
                arrival_time = datetime.strptime(arrival_time[:10], "%Y-%M-%d"),
                price = price,
                seats_available = seats_available,
                status = 'active',
                airplane = airplane
            )
            
            db.session.add(flight)
            db.session.commit()
            
            flash('Рейс успешно добавлен', 'success')
            return redirect('/admin/flights')
            
        except Exception as e:
            flash(f'Ошибка при добавлении рейса: {str(e)}', 'error')
    
    return render_template('admin_flights_edit.html', flight=None, action='add')

@admin_bp.route('/admin/flights/edit/<int:flight_id>', methods=['GET', 'POST'])
def admin_edit_flight(flight_id):
    """Редактирование рейса"""
    if 'phone' not in session or session.get('role') != 'admin':
        return redirect('/login')

    # Получаем рейс
    stmt = (
        select(Flight, User.phone.label('cashier_phone'))
        .outerjoin(User, Flight.created_by == User.id)
        .where(Flight.id == flight_id)
    )

    result = db.session.execute(stmt).first()

    if not result:
        flash('Рейс не найден', 'error')
        return redirect('/admin/flights')

    flight = result

    if request.method == 'POST':
        try:
            flight.flight_number = request.form.get('flight_number', '').strip()
            flight.departure_city = request.form.get('departure_city', '').strip()
            flight.arrival_city = request.form.get('arrival_city', '').strip()
            flight.departure_time = request.form.get('departure_time')
            flight.arrival_time = request.form.get('arrival_time')
            flight.price = int(request.form.get('price', 0))
            flight.seats_available = int(request.form.get('seats_available', 0))
            flight.airplane = request.form.get('airplane', '').strip()
            flight.status = request.form.get('status', 'active').strip()

            db.session.commit()
            flash('Рейс успешно обновлен', 'success')
            return redirect('/admin/flights')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении рейса: {e}', 'error')


    return render_template(
        'admin_flights_edit.html',
        flight=flight,
        action='edit'
    )

from sqlalchemy import select, func

@admin_bp.route('/admin/flights/delete/<int:flight_id>')
def admin_delete_flight(flight_id):
    """Удаление рейса"""
    if 'phone' not in session or session.get('role') != 'admin':
        return redirect('/login')

    # Проверяем активные билеты
    active_tickets = db.session.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.flight_id == flight_id,
            Ticket.status == 'active'
        )
    )

    if active_tickets > 0:
        flash(f'Нельзя удалить рейс с {active_tickets} активными билетами', 'error')
        return redirect('/admin/flights')

    flight = db.session.get(Flight, flight_id)

    if not flight:
        flash('Рейс не найден', 'error')
        return redirect('/admin/flights')

    try:
        db.session.delete(flight)
        db.session.commit()
        flash('Рейс успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении рейса: {e}', 'error')

    return redirect('/admin/flights')

# ==================== УПРАВЛЕНИЕ СОТРУДНИКАМИ ====================

@admin_bp.route('/admin/staff', methods=['GET', 'POST'])
def admin_staff():
    """Управление сотрудниками"""
    if 'phone' not in session or session.get('role') != 'admin':
        return redirect('/login')

    search_performed = False

    stmt = select(User).where(
        User.role.in_(('cashier', 'admin'))
    )

    if request.method == 'POST':
        search_performed = True

        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', '').strip()

        if phone:
            stmt = stmt.where(User.phone.ilike(f'%{phone}%'))

        if role:
            stmt = stmt.where(User.role == role)

    stmt = stmt.order_by(desc(User.id))

    staff = db.session.scalars(stmt).all()

    return render_template(
        'admin_staff.html',
        staff=staff,
        search_performed=search_performed
    )

@admin_bp.route('/admin/staff/add', methods=['GET', 'POST'])
def admin_add_staff():
    """Добавление сотрудника"""
    if 'phone' not in session or session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        surname = request.form.get('surname', '').strip()
        patronymic = request.form.get('patronymic', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'cashier').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        organization_number = request.form.get('organization_number', '').strip()

        errors = []

        if not validate_phone(phone):
            errors.append('Неверный формат телефона')
        if not validate_password(password):
            errors.append('Пароль должен содержать минимум 8 символов, буквы и цифры')
        if role not in ('cashier', 'admin'):
            errors.append('Неверная роль')
        if not validate_passport_series(passport_series):
            errors.append('Серия паспорта должна содержать 4 цифры')
        if not validate_passport_number(passport_number):
            errors.append('Номер паспорта должен содержать 6 цифр')
        if role == 'cashier' and not validate_organization(organization_number):
            errors.append('Номер организации должен содержать 5–15 цифр')

        if errors:
            for e in errors:
                flash(e, 'error')
            return redirect('/admin/staff/add')

        # Проверка уникальности телефона
        exists = db.session.scalar(
            select(User.id).where(User.phone == phone)
        )

        if exists:
            flash('Пользователь с таким телефоном уже существует', 'error')
            return redirect('/admin/staff/add')

        try:
            user = User(
                name=name,
                surname=surname,
                patronymic=patronymic,
                phone=phone,
                password=hash_password(password),
                role=role,
                passport_series=passport_series,
                passport_number=passport_number,
                organization_number=organization_number if role == 'cashier' else None,
            )

            db.session.add(user)
            db.session.commit()

            flash('Сотрудник успешно добавлен', 'success')
            return redirect('/admin/staff')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении сотрудника: {e}', 'error')

    return render_template('admin_staff_add.html')

@admin_bp.route('/admin/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
def admin_edit_staff(staff_id):
    """Редактирование сотрудника"""
    if 'phone' not in session or session.get('role') != 'admin':
        return redirect('/login')

    staff = db.session.scalar(
        select(User)
        .where(
            User.id == staff_id,
            User.role.in_(('cashier', 'admin'))
        )
    )

    if not staff:
        flash('Сотрудник не найден', 'error')
        return redirect('/admin/staff')
    if staff.id == session['user_id']:
        flash('Вы не можете редактировать свой собственный профиль', 'error')
        return redirect('/admin/staff')

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        surname = request.form.get('surname', '').strip()
        patronymic = request.form.get('patronymic', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'cashier').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        organization_number = request.form.get('organization_number', '').strip()
        status = request.form.get('status', 'active').strip()

        errors = []

        if not validate_phone(phone):
            errors.append('Неверный формат телефона')
        if role not in ('cashier', 'admin'):
            errors.append('Неверная роль')
        if not validate_passport_series(passport_series):
            errors.append('Серия паспорта должна содержать 4 цифры')
        if not validate_passport_number(passport_number):
            errors.append('Номер паспорта должен содержать 6 цифр')
        if role == 'cashier' and not validate_organization(organization_number):
            errors.append('Номер организации должен содержать 5–15 цифр')

        if errors:
            for e in errors:
                flash(e, 'error')
            return redirect(f'/admin/staff/edit/{staff_id}')

        phone_used = db.session.scalar(
            select(User.id)
            .where(User.phone == phone, User.id != staff_id)
        )

        if phone_used:
            flash('Телефон уже используется другим пользователем', 'error')
            return redirect(f'/admin/staff/edit/{staff_id}')

        try:
            staff.name = name
            staff.surname = surname
            staff.patronymic = patronymic
            staff.phone = phone
            staff.role = role
            staff.passport_series = passport_series
            staff.passport_number = passport_number
            staff.organization_number = organization_number if role == 'cashier' else None
            staff.status = status

            db.session.commit()
            flash('Сотрудник успешно обновлен', 'success')
            return redirect('/admin/staff')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении сотрудника: {e}', 'error')

    return render_template('admin_staff_edit.html', staff=staff)

@admin_bp.route('/admin/staff/delete/<int:staff_id>')
def admin_delete_staff(staff_id):
    """Удаление сотрудника"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    if staff_id == session['user_id']:
        flash('Вы не можете удалить себя', 'error')
        return redirect('/admin/staff')

    flights_count = db.session.scalar(
        select(func.count())
        .select_from(Flight)
        .where(Flight.created_by == staff_id)
    )

    if flights_count > 0:
        flash(f'Нельзя удалить кассира с {flights_count} созданными рейсами', 'error')
        return redirect('/admin/staff')

    staff = db.session.get(User, staff_id)

    if not staff:
        flash('Сотрудник не найден', 'error')
        return redirect('/admin/staff')

    try:
        db.session.delete(staff)
        db.session.commit()
        flash('Сотрудник успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении сотрудника: {e}', 'error')

    return redirect('/admin/staff')