import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType
from datetime import datetime
from database import get_db_connection

# Define Object Types
class User(graphene.ObjectType):
    id = graphene.ID()
    username = graphene.String()
    full_name = graphene.String()
    email = graphene.String()
    phone = graphene.String()
    address = graphene.String()
    created_at = graphene.DateTime()

class Airline(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    code = graphene.String()
    logo_url = graphene.String()
    base_price = graphene.Int()
    created_at = graphene.DateTime()

class Booking(graphene.ObjectType):
    id = graphene.ID()
    userId = graphene.ID()
    airlineId = graphene.ID()
    passengerName = graphene.String()
    departureAirport = graphene.String()
    destinationAirport = graphene.String()
    bookingDate = graphene.Date()
    seatNumber = graphene.String()
    totalPrice = graphene.Int()
    createdAt = graphene.DateTime()

class Payment(graphene.ObjectType):
    id = graphene.ID()
    booking_id = graphene.ID()
    amount = graphene.Int()
    method = graphene.String()
    status = graphene.String()
    payment_date = graphene.Date()
    created_at = graphene.DateTime()

# Define Queries
class Query(graphene.ObjectType):
    # User queries
    user = graphene.Field(User, id=graphene.ID())
    users = graphene.List(User)

    # Airline queries
    airline = graphene.Field(Airline, id=graphene.ID())
    airlines = graphene.List(Airline)

    # Booking queries
    booking = graphene.Field(Booking, id=graphene.ID())
    bookings = graphene.List(Booking, userId=graphene.ID())
    
    # Payment queries
    payment = graphene.Field(Payment, id=graphene.ID())
    payments = graphene.List(Payment, booking_id=graphene.ID())

    def resolve_user(self, info, id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (id,))
        user = cursor.fetchone()
        conn.close()
        return User(**dict(user)) if user else None

    def resolve_users(self, info):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        conn.close()
        return [User(**dict(user)) for user in users]

    def resolve_airline(self, info, id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM airlines WHERE id = ?', (id,))
        airline = cursor.fetchone()
        conn.close()
        return Airline(**dict(airline)) if airline else None

    def resolve_airlines(self, info):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM airlines')
        airlines = cursor.fetchall()
        conn.close()
        return [Airline(**dict(airline)) for airline in airlines]

    def resolve_booking(self, info, id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM bookings WHERE id = ?', (id,))
        booking = cursor.fetchone()
        conn.close()
        return Booking(**dict(booking)) if booking else None

    def resolve_bookings(self, info, userId=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        if userId:
            cursor.execute('SELECT * FROM bookings WHERE user_id = ?', (userId,))
        else:
            cursor.execute('SELECT * FROM bookings')
        bookings = cursor.fetchall()
        conn.close()
        
        result = []
        for booking in bookings:
            booking_dict = dict(booking)
            # Convert snake_case to camelCase
            booking_dict['userId'] = booking_dict.pop('user_id')
            booking_dict['airlineId'] = booking_dict.pop('airline_id')
            booking_dict['passengerName'] = booking_dict.pop('passenger_name')
            booking_dict['departureAirport'] = booking_dict.pop('departure_airport')
            booking_dict['destinationAirport'] = booking_dict.pop('destination_airport')
            
            # Convert date string to datetime object
            booking_date = booking_dict.pop('booking_date')
            if booking_date:
                try:
                    booking_dict['bookingDate'] = datetime.strptime(booking_date, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    booking_dict['bookingDate'] = None
            else:
                booking_dict['bookingDate'] = None
                
            booking_dict['seatNumber'] = booking_dict.pop('seat_number')
            booking_dict['totalPrice'] = booking_dict.pop('total_price')
            booking_dict['createdAt'] = booking_dict.pop('created_at')
            result.append(Booking(**booking_dict))
        return result

    def resolve_payment(self, info, id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM payments WHERE id = ?', (id,))
        payment = cursor.fetchone()
        conn.close()
        return Payment(**dict(payment)) if payment else None

    def resolve_payments(self, info, booking_id=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        if booking_id:
            cursor.execute('SELECT * FROM payments WHERE booking_id = ?', (booking_id,))
        else:
            cursor.execute('SELECT * FROM payments')
        payments = cursor.fetchall()
        conn.close()
        return [Payment(**dict(payment)) for payment in payments]

# Define Mutations
class CreateUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
        full_name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()
        address = graphene.String()

    user = graphene.Field(User)

    def mutate(self, info, username, password, full_name, email, phone=None, address=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, full_name, email, phone, address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password, full_name, email, phone, address))
            conn.commit()
            user_id = cursor.lastrowid
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            return CreateUser(user=User(**dict(user)))
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
        finally:
            conn.close()

class CreateBooking(graphene.Mutation):
    class Arguments:
        userId = graphene.ID(required=True)
        airlineId = graphene.ID(required=True)
        passengerName = graphene.String(required=True)
        departureAirport = graphene.String(required=True)
        destinationAirport = graphene.String(required=True)
        bookingDate = graphene.Date(required=True)
        totalPrice = graphene.Int(required=True)

    booking = graphene.Field(Booking)

    def mutate(self, info, userId, airlineId, passengerName, departureAirport, 
               destinationAirport, bookingDate, totalPrice):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO bookings (user_id, airline_id, passenger_name, departure_airport,
                                    destination_airport, booking_date, total_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (userId, airlineId, passengerName, departureAirport, 
                 destinationAirport, bookingDate, totalPrice))
            conn.commit()
            booking_id = cursor.lastrowid
            cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
            booking = cursor.fetchone()
            booking_dict = dict(booking)
            # Convert snake_case to camelCase
            booking_dict['userId'] = booking_dict.pop('user_id')
            booking_dict['airlineId'] = booking_dict.pop('airline_id')
            booking_dict['passengerName'] = booking_dict.pop('passenger_name')
            booking_dict['departureAirport'] = booking_dict.pop('departure_airport')
            booking_dict['destinationAirport'] = booking_dict.pop('destination_airport')
            booking_dict['bookingDate'] = booking_dict.pop('booking_date')
            booking_dict['seatNumber'] = booking_dict.pop('seat_number')
            booking_dict['totalPrice'] = booking_dict.pop('total_price')
            booking_dict['createdAt'] = booking_dict.pop('created_at')
            return CreateBooking(booking=Booking(**booking_dict))
        except Exception as e:
            print(f"Error creating booking: {e}")
            return None
        finally:
            conn.close()

class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    create_booking = CreateBooking.Field()

# Create Schema
schema = graphene.Schema(query=Query, mutation=Mutation) 