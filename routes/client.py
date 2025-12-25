from flask import Blueprint, session, redirect, request, render_template
from models.models import db, User, Ticket, Flight
from sqlalchemy import desc

client_bp = Blueprint('client_bl', __name__)

@client_bp.route('/client/', methods=['GET', 'POST'])
def client():
    if session.get('ticket_process'):
        del session['ticket_process']
    if 'phone' not in session or session.get('role') != 'client':
        return redirect('/login')
    
    if request.method == 'POST':
        del session['phone']
        del session['role']
        return redirect('/login')

    if 'ticket_process' in session:
        return redirect(session['ticket_process'])

    stmt = db.select(User).where(User.phone == session.get('phone'))
    user = db.session.execute(stmt).scalar()
    return render_template('client.html',
                           phone=user.phone,
                           name=user.name,
                           surname=user.surname,
                           patronymic=user.patronymic,
                           passport_series=user.passport_series,
                           passport_number=user.passport_number)

@client_bp.route('/client/my_tickets/')
def client_tickets():
    if session.get('ticket_process'):
        del session['ticket_process']
    if 'phone' not in session or session.get('role') != 'client':
        return redirect('/login')
    
    stmt = db.select(User).where(User.phone == session['phone'])
    user = db.session.execute(stmt).scalar()
    
    tickets = db.session.query(
        Ticket,
        Flight.flight_number,
        Flight.departure_city,
        Flight.arrival_city,
        Flight.departure_time,
        Flight.arrival_time,
        Flight.price
    ).join(
        Flight, Ticket.flight_id == Flight.id
    ).filter(
        Ticket.user_id == user.id,
        Ticket.status == 'active'
    ).order_by(
        desc(Ticket.purchase_date)
    ).all()

    success = request.args.get('success') == 'true'

    return render_template('client_tickets.html', tickets=tickets, success=success)