from flask import Blueprint, render_template, session, redirect, request
from models.models import db, User
from libs.libs import *

auth_bp = Blueprint('auth_bl', __name__)

@auth_bp.route('/login/', methods=['GET', 'POST'])
def login():
    if 'phone' in session and session.get('role') == 'client':
        return redirect('/client')
    
    if 'phone' in session and session.get('role') == 'cashier':
        return redirect('/cashier')

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()

        if not validate_phone(phone):
            return render_template('login.html', error="Неверный номер телефона")
        
        stmt = db.select(User).where(User.phone == phone)
        user = db.session.execute(stmt).scalar()

        if user and user.password == hash_password(password):
            session['phone'] = user.phone
            session['role'] = user.role

            if user.role == 'client':
                return redirect('/client')
            if user.role == 'cashier':
                return redirect('/cashier')
            if user.role == 'admin':
                return redirect('/admin')
        
        return render_template('login.html', error='Неверный телефон или пароль')
    
    return render_template('login.html')

@auth_bp.route('/register/client/', methods=['GET', 'POST'])
def register_client():
    if request.method == 'POST':
        surname = request.form.get('surname', '').strip()
        name = request.form.get('name', '').strip()
        patronymic = request.form.get('patronymic', '').strip()
        phone = request.form.get('phone', '').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
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
        
        stmt = db.select(User).where(User.phone == phone)
        user_check = db.session.execute(stmt).scalar()

        if user_check:
            return render_template('register_client.html', errors=['Пользователь с таким номером уже существует'])
        
        try:
            user = User(
                name = name,
                surname = surname,
                patronymic = patronymic,
                passport_series = passport_series,
                passport_number = passport_number,
                phone = phone,
                password = hash_password(password),
                role = 'client'
            )

            db.session.add(user)
            db.session.commit()

            session['phone'] = user.phone
            session['role'] = user.role

            if 'ticket_process' in session:
                return redirect(session['ticket_process'])

            return redirect('/client')
        
        except Exception as e:
            print(f"Ошибка при регистрации: {str(e)}")
        
    return render_template('register_client.html')

@auth_bp.route('/register/cashier/', methods=['GET', 'POST'])
def register_cashier():
    if request.method == 'POST':
        surname = request.form.get('surname', '').strip()
        name = request.form.get('name', '').strip()
        patronymic = request.form.get('patronymic', '').strip()
        phone = request.form.get('phone', '').strip()
        passport_series = request.form.get('passport_series', '').strip()
        passport_number = request.form.get('passport_number', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        organization_number = request.form.get('organization_number', '').strip()
        
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
            return render_template('register_cashier.html', errors=errors)
        
        stmt = db.select(User).where(User.phone == phone)
        user_check = db.session.execute(stmt).scalar()

        if user_check:
            return render_template('register_cashier.html', errors=['Пользователь с таким номером уже существует'])
        
        try:
            user = User(
                name = name,
                surname = surname,
                patronymic = patronymic,
                passport_series = passport_series,
                passport_number = passport_number,
                phone = phone,
                password = hash_password(password),
                role = 'cashier',
                organization_number=organization_number
            )

            db.session.add(user)
            db.session.commit()

            session['phone'] = user.phone
            session['role'] = user.role

            return redirect('/cashier')
        
        except Exception as e:
            print(f"Ошибка при регистрации: {str(e)}")
        
    return render_template('register_cashier.html')
