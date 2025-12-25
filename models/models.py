from sqlalchemy import Integer, Float, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from flask_sqlalchemy import SQLAlchemy

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
    
class User(db.Model):
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    patronymic: Mapped[str] = mapped_column(String(100), nullable=False)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    passport_series: Mapped[str] = mapped_column(String(4), nullable=False)
    passport_number: Mapped[str] = mapped_column(String(6), nullable=False)
    phone: Mapped[str] = mapped_column(String(18), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    organization_number: Mapped[str] = mapped_column(String(100), nullable=True, default=None)

    def __init__(self, id=None, name=None, surname=None, patronymic=None, passport_series=None, passport_number=None, phone=None, password=None, role=None, organization_number=None):
        self.name = name
        self.surname = surname
        self.patronymic = patronymic
        self.passport_series = passport_series
        self.passport_number = passport_number
        self.phone = phone
        self.password = password
        self.role = role
        self.organization_number = organization_number
        super().__init__(id=id)

    def __repr__(self):
        return self.name
    
class Flight(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    departure_city: Mapped[str] = mapped_column(String(100), nullable=False)
    arrival_city: Mapped[str] = mapped_column(String(100), nullable=False)
    departure_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    arrival_time: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Float)
    seats_available: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(100), default='active', nullable=False)
    airplane: Mapped[str] = mapped_column(String(100), nullable=False)

    def __init__(self, id=None, flight_number=None, departure_city=None, arrival_city=None, departure_time=None, arrival_time=None, price=None, seats_available=None, status='active', created_by=None, airplane=None):
        self.flight_number = flight_number
        self.departure_city = departure_city
        self.arrival_city = arrival_city
        self.departure_time = departure_time
        self.arrival_time = arrival_time
        self.price = price
        self.seats_available = seats_available
        self.status = status
        self.created_by = created_by
        self.airplane = airplane

        super().__init__(id=id)

    def __repr__(self):
        return self.flight_number
    
class Ticket(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False)
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey(Flight.id), nullable=False)
    passenger_name: Mapped[str] = mapped_column(String(100), nullable=False)
    passenger_passport: Mapped[str] = mapped_column(String(4), nullable=False)
    purchase_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)

    def __init__(self, id=None, user_id=None, flight_id=None, passenger_name=None, passenger_passport=None, purchase_date='active', status=None):
        self.user_id = user_id
        self.flight_id = flight_id
        self.passenger_name = passenger_name
        self.passenger_passport = passenger_passport
        self.purchase_date = purchase_date
        self.status = status

        super().__init__(id=id)

    def __repr__(self):
        return self.passenger_name
    
class Sale(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey(Ticket.id), nullable=False)
    cashier_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(100), nullable=False)
    sale_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    def __init__(self, id=None, ticket_id=None, cashier_id=None, amount=None, payment_method=None, sale_date=None):
        self.ticket_id=ticket_id,
        self.cashier_id=cashier_id,
        self.amount=amount,
        self.payment_method=payment_method,
        self.sale_date=sale_date

        super().__init__(id=id)

    def __repr__(self):
        return self.passenger_name
    
class Return(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey(Ticket.id), nullable=False)
    cashier_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation: Mapped[str] = mapped_column(String(100), nullable=False)
    return_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    def __init__(self, id=None, ticket_id=None, cashier_id=None, reason=None, explanation=None, return_date=None):
        self.ticket_id=ticket_id,
        self.cashier_id=cashier_id,
        self.reason=reason,
        self.explanation=explanation,
        self.return_date=return_date

        super().__init__(id=id)

    def __repr__(self):
        return self.passenger_name