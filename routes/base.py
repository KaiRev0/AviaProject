from flask import Blueprint, render_template, request, redirect, session
from sqlalchemy import func
from models.models import Flight, User, Ticket, db
from datetime import datetime

base_bp = Blueprint('base', __name__)

@base_bp.route('/', methods=['GET', 'POST'])
def index():
    if session.get('ticket_process'):
        del session['ticket_process']

    flights = []
    count = 0

    if request.method == 'POST':
        departure = request.form.get('departure', '').strip()
        arrival = request.form.get('arrival', '').strip()
        date = request.form.get('date', '').strip()

        stmt = db.select(Flight).where(Flight.status=='active')
        counter = db.select(func.count()).select_from(Flight).where(Flight.status=='active')

        if departure:
            stmt = stmt.where(Flight.departure_city==departure)
            counter = counter.where(Flight.departure_city==departure)
        if arrival:
            stmt = stmt.where(Flight.arrival_city==arrival)
            counter = counter.where(Flight.arrival_city==arrival)
        if date:
            stmt = stmt.where(Flight.departure_time==date)
            counter = counter.where(Flight.departure_time==date)

        flights = db.session.execute(stmt).scalars()
        count = db.session.execute(counter).scalar()

    return render_template('search_flights.html', flights=flights, count=count)

@base_bp.route('/buy/<int:flight_id>/', methods=['GET', 'POST'])
def buy_ticket(flight_id: int):
    stmt = db.select(Flight).where(Flight.id==flight_id)
    flight = db.session.execute(stmt).scalar()

    if not flight:
        return redirect('/')

    if request.method == 'POST':
        if 'phone' not in session or session.get('role') != 'client':
            session['ticket_process'] = f'/buy/{flight_id}'
            return redirect('/register/client/')
        
        stmt = db.select(User).where(User.phone == session.get('phone'))
        user = db.session.execute(stmt).scalar()
        try:
            flight = Flight.query.filter_by(id=flight_id).first()

            if not flight or flight.seats_available <= 0:
                return render_template('buy_ticket.html', flight=flight, error="Нет доступных мест!")
            
            ticket = Ticket(
                user_id=user.id,
                flight_id=flight_id,
                passenger_name=user.name,
                passenger_passport=user.passport_series+' '+user.passport_number,
                purchase_date=datetime.now(),
                status='active'
            )

            flight.seats_available -= 1

            db.session.add(ticket)
            db.session.commit()

            if session.get('ticket_process'):
                del session['ticket_process']
            return redirect('/client/my_tickets?success=true')
        
        except Exception as e:
            db.session.rollback()
            return render_template('buy_ticket.html', flight=flight, error=f"Ошибка при бронировании: {str(e)}")
            
    return render_template('buy_ticket.html', flight=flight)

@base_bp.route('/logout/')
def logout():
    session.clear()
    return redirect('/login')