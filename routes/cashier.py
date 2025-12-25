from flask import Blueprint, render_template, session, redirect, flash, request
from sqlalchemy import select, func
from datetime import datetime
from models.models import db, Flight, Ticket, User, Sale, Return

cashier_bp = Blueprint('cashier_bp', __name__)

@cashier_bp.route('/cashier/')
def cashier_page():
    """Личный кабинет кассира"""
    if 'phone' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    return render_template('cashier.html', phone=session.get('phone'))

@cashier_bp.route('/cashier/sell/<int:flight_id>/', methods=['GET', 'POST'])
def cashier_sell(flight_id):
    """Продажа билета через кассу (ПРОСТАЯ ВЕРСИЯ)"""
    if 'phone' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    # Получаем рейс
    flight = db.session.get(Flight, flight_id)
    
    if not flight:
        flash('Рейс не найден', 'error')
        return redirect('/cashier/search')
    
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        passenger_name = request.form.get('passenger_name', '').strip()
        payment_method = request.form.get('payment_method', 'cash')
        
        if not phone or not passenger_name:
            flash('Заполните все поля', 'error')
            return render_template('cashier_sell.html', flight=flight)
        
        try:
            # Ищем клиента
            user = db.session.scalar(
                select(User).where(User.phone == phone)
            )
            
            if not user:
                flash('Клиент не найден', 'error')
                return render_template('cashier_sell.html', flight=flight)
            
            # Уменьшаем места (с проверкой доступности)
            if flight.seats_available <= 0:
                flash('Нет доступных мест', 'error')
                return render_template('cashier_sell.html', flight=flight)
            
            flight.seats_available -= 1
            
            # Создаем билет
            ticket = Ticket(
                user_id=user.id,
                flight_id=flight_id,
                passenger_name=passenger_name,
                passenger_passport="из регистрации",
                status='active'
            )
            db.session.add(ticket)
            db.session.flush()  # Получаем ID билета

            stmt = db.select(User).where(User.phone == session.get('phone'))
            user = db.session.execute(stmt).scalar()
            
            # Записываем продажу в таблицу sales
            sale = Sale(
                ticket_id=ticket.id,
                cashier_id=user.id,
                amount=flight.price,
                payment_method=payment_method,
                sale_date=datetime.now()
            )
            db.session.add(sale)
            
            db.session.commit()
            stmt = db.select(User).where(User.phone == session.get('phone'))
            user = db.session.execute(stmt).scalar()
            print(f"✅ Продажа записана! Билет: {ticket.id}, Кассир: {user.id}, Сумма: {flight.price}")
            
            flash('Билет продан!', 'success')
            return redirect(f'/cashier/receipt/{ticket.id}')
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Ошибка при продаже: {e}")
            flash(f'Ошибка: {str(e)}', 'error')
            return render_template('cashier_sell.html', flight=flight)
    
    return render_template('cashier_sell.html', flight=flight)

@cashier_bp.route('/cashier/daily_report/', methods=['GET', 'POST'])
def daily_report():
    """Отчет по дневной выручке (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
    if 'phone' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    report_date = request.form.get('date', '')
    
    if not report_date:
        report_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        stmt = db.select(User).where(User.phone == session.get('phone'))
        user = db.session.execute(stmt).scalar()
        cashier_id = user.id
        
        # 1. Продажи за день
        sales_data = db.session.execute(
            select(
                func.count(Sale.id).label('sales_count'),
                func.coalesce(func.sum(Sale.amount), 0).label('total_sales'),
                func.coalesce(func.sum(Sale.amount) * 0.1, 0).label('commission')
            ).where(
                func.date(Sale.sale_date) == report_date,
                Sale.cashier_id == cashier_id
            )
        ).first()
        
        # 2. Возвраты за день
        returns_data = db.session.execute(
            select(
                func.count(Return.id).label('returns_count'),
                func.coalesce(
                    select(func.sum(Flight.price))
                    .join(Ticket, Return.ticket_id == Ticket.id)
                    .join(Flight, Ticket.flight_id == Flight.id)
                    .where(
                        func.date(Return.return_date) == report_date,
                        Return.cashier_id == cashier_id
                    ),
                    0
                ).label('total_returns')
            ).where(
                func.date(Return.return_date) == report_date,
                Return.cashier_id == cashier_id
            )
        ).first()
        
        # 3. Детализация продаж
        sales_details = db.session.execute(
            select(
                Sale,
                Flight.flight_number,
                Ticket.passenger_name,
                Flight.price.label('ticket_price'),
                Flight.airplane
            )
            .join(Ticket, Sale.ticket_id == Ticket.id)
            .join(Flight, Ticket.flight_id == Flight.id)
            .where(
                func.date(Sale.sale_date) == report_date,
                Sale.cashier_id == cashier_id
            )
            .order_by(Sale.sale_date.desc())
        ).all()
        
        # 4. Детализация возвратов
        returns_details = db.session.execute(
            select(
                Return,
                Flight.flight_number,
                Ticket.passenger_name,
                Flight.price.label('ticket_price'),
                Flight.airplane
            )
            .join(Ticket, Return.ticket_id == Ticket.id)
            .join(Flight, Ticket.flight_id == Flight.id)
            .where(
                func.date(Return.return_date) == report_date,
                Return.cashier_id == cashier_id
            )
            .order_by(Return.return_date.desc())
        ).all()
        
        # 5. Статистика по созданным рейсам
        flights_stats = db.session.execute(
            select(
                func.count(Flight.id).label('flights_created'),
                func.coalesce(func.sum(Flight.seats_available), 0).label('total_seats'),
                func.coalesce(func.sum(Flight.price * Flight.seats_available), 0).label('potential_revenue')
            )
            .where(
                Flight.created_by == cashier_id,
                func.date(Flight.departure_time) == report_date
            )
        ).first()
        
        # Формируем единый отчет
        report = {
            'sales_count': sales_data.sales_count if sales_data else 0,
            'total_sales': float(sales_data.total_sales) if sales_data else 0,
            'commission': float(sales_data.commission) if sales_data else 0,
            'returns_count': returns_data.returns_count if returns_data else 0,
            'total_returns': float(returns_data.total_returns) if returns_data else 0,
            'commission_loss': (float(returns_data.total_returns) * 0.1) if returns_data else 0
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
        flash(f'Ошибка при формировании отчета: {str(e)}', 'error')
        return redirect('/cashier')

@cashier_bp.route('/cashier/search/', methods=['GET', 'POST'])
def cashier_search():
    """Поиск рейсов для кассира"""
    if 'phone' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    flights = []
    
    if request.method == 'POST':
        departure = request.form.get('departure', '').strip()
        arrival = request.form.get('arrival', '').strip()
        date = request.form.get('date', '').strip()
        flight_number = request.form.get('flight_number', '').strip()
        
        query = select(Flight).where(Flight.status == 'active')
        
        if departure:
            query = query.where(Flight.departure_city.ilike(f'%{departure}%'))
        
        if arrival:
            query = query.where(Flight.arrival_city.ilike(f'%{arrival}%'))
        
        if date:
            query = query.where(Flight.departure_time.ilike(f'{date}%'))
        
        if flight_number:
            query = query.where(Flight.flight_number.ilike(f'%{flight_number}%'))
        
        flights = db.session.scalars(query).all()
    
    return render_template('cashier_search.html', flights=flights)

@cashier_bp.route('/cashier/receipt/<int:ticket_id>/')
def cashier_receipt(ticket_id):
    """Чек продажи"""
    if 'phone' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    ticket_data = db.session.execute(
        select(
            Ticket,
            Flight.flight_number,
            Flight.departure_city,
            Flight.arrival_city,
            Flight.departure_time,
            Flight.arrival_time,
            Flight.price,
            User.phone.label('customer_phone'),
            Sale.payment_method
        )
        .join(Flight, Ticket.flight_id == Flight.id)
        .join(User, Ticket.user_id == User.id)
        .outerjoin(Sale, Ticket.id == Sale.ticket_id)
        .where(Ticket.id == ticket_id)
    ).first()
    
    if not ticket_data:
        flash('Билет не найден', 'error')
        return redirect('/cashier/search')
    
    return render_template('cashier_receipt.html', ticket=ticket_data)

@cashier_bp.route('/cashier/return/', methods=['GET', 'POST'])
def cashier_return():
    """Возврат билета через кассу"""
    if 'phone' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
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
        
        query = select(
            Ticket,
            Flight.flight_number,
            Flight.departure_city,
            Flight.arrival_city,
            Flight.departure_time,
            Flight.price,
            User.phone
        ).join(
            Flight, Ticket.flight_id == Flight.id
        ).join(
            User, Ticket.user_id == User.id
        ).where(
            Ticket.status == 'active'
        )
        
        if ticket_number:
            query = query.where(Ticket.id == int(ticket_number))
        
        if passenger_passport:
            query = query.where(Ticket.passenger_passport.ilike(f'%{passenger_passport}%'))
        
        if phone:
            query = query.where(User.phone.ilike(f'%{phone}%'))
        
        ticket = db.session.execute(query).first()
    
    elif request.method == 'POST' and 'return' in request.form:
        # Возврат билета
        ticket_id = request.form.get('ticket_id')
        reason = request.form.get('reason', 'passenger_request')
        explanation = request.form.get('explanation', '').strip()
        
        ticket = db.session.execute(
            select(Ticket, Flight.id.label('flight_id'))
            .join(Flight, Ticket.flight_id == Flight.id)
            .where(Ticket.id == ticket_id, Ticket.status == 'active')
        ).first()
        
        if ticket:
            try:
                # Возвращаем билет
                ticket.Ticket.status = 'returned'
                
                # Увеличиваем количество доступных мест
                flight = db.session.get(Flight, ticket.flight_id)
                if flight:
                    flight.seats_available += 1
                
                stmt = db.select(User).where(User.phone == session.get('phone'))
                user = db.session.execute(stmt).scalar()
                # Регистрируем возврат
                return_record = Return(
                    ticket_id=ticket_id,
                    cashier_id=user.id,
                    reason=reason,
                    explanation=explanation,
                    return_date=datetime.now()
                )
                db.session.add(return_record)
                
                db.session.commit()
                
                flash('Билет успешно возвращен!', 'success')
                return redirect(f'/cashier/return_success/{ticket_id}')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при возврате билета: {str(e)}', 'error')
    
    return render_template('cashier_return.html', 
                         ticket=ticket, 
                         reason_options=reason_options)

@cashier_bp.route('/cashier/return_success/<int:ticket_id>/')
def return_success(ticket_id):
    """Успешный возврат"""
    if 'phone' not in session or session.get('role') != 'cashier':
        return redirect('/login')
    
    ticket_data = db.session.execute(
        select(
            Ticket,
            Flight.flight_number,
            Flight.price,
            Return.reason,
            Return.explanation
        )
        .join(Flight, Ticket.flight_id == Flight.id)
        .join(Return, Ticket.id == Return.ticket_id)
        .where(Ticket.id == ticket_id)
    ).first()
    
    if not ticket_data:
        flash('Информация о возврате не найдена', 'error')
        return redirect('/cashier/return')
    
    return render_template('cashier_return_success.html', ticket=ticket_data)