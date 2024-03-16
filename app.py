from flask import Flask, render_template, request, redirect, url_for, session
import datetime
import requests
import folium 
from data import clinics
from twilio.rest import Client

my_map = folium.Map(location=[43.6532, -79.3832], zoom_start=14)
sanomed_popup = "<a href='http://127.0.0.1:5000/sanomed/booking' target='_blank'> Sanomed Medical Clinic </a>"
folium.Marker(location=[43.665269,-79.387529], popup=sanomed_popup).add_to(my_map)

hearthealth_popup = "<a href='http://127.0.0.1:5000/hearthealth/booking' target='_blank'> HeartHealth Medical </a>"
folium.Marker(location=[43.6580818742268, -79.40446914492092], popup=hearthealth_popup).add_to(my_map)

familywalkin_popup = "<a href='http://127.0.0.1:5000/familywalkin/booking' target='_blank'> Family Doctors & Walk-In Clinic </a>"
folium.Marker(location=[43.66069937508352, -79.3861229769542], popup=familywalkin_popup).add_to(my_map)

familymedicine_popup = "<a href='http://127.0.0.1:5000/familymedicine/booking' target='_blank'> Family Medicine Clinic </a>"
folium.Marker(location=[43.65588280429575, -79.38671963277586], popup=familymedicine_popup).add_to(my_map)
my_map.save('static/map.html')

app = Flask(__name__)
app.secret_key = 'secret_key'

users = {
    'admin': 'password'
}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        phone_number = request.form['phone_number']
        
        # Check if the username already exists
        if username in users:
            return render_template('register.html', error='Username already exists')

        # Store user details in the users dictionary
        users[username] = {'password': password, 'name': name, 'phone_number': phone_number}

        # Set username in session
        session['username'] = username

        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/home',methods=['GET', 'POST'])
def home():
    # Collect all appointments from all clinics
    all_appointments = []
    matching_clinics = []

    for clinic_name, clinic_info in clinics.items():
        available_slots = clinic_info.get('available_slots', {})
        for date, times in available_slots.items():
            for time in times:
                appointment_datetime = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")
                all_appointments.append({
                    'clinic_name': clinic_info['name'],
                    'date': appointment_datetime.date(),
                    'time': appointment_datetime.time()
                })

    # Sort appointments by date and time
    all_appointments.sort(key=lambda x: (x['date'], x['time']))

    # Filter appointments based on date selector
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date and end_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        all_appointments = [appointment for appointment in all_appointments
                            if start_date <= appointment['date'] <= end_date]

    # Filter appointments based on time preference
    time_filter = request.args.get('time_filter')
    if time_filter in ['morning', 'afternoon', 'evening']:
        all_appointments = [appointment for appointment in all_appointments if get_time_preference(appointment['time']) == time_filter]

    search_word = request.form.get('search_word', '').lower() if request.method == 'POST' else ''
    if search_word:  # Only search if there's a word input by the user
        for clinic_name, clinic_info in clinics.items():
            for review in clinic_info['reviews']:
                if search_word.lower() in review.lower():
                    matching_clinics.append(clinic_info['name'])

    return render_template('homepage.html', appointments=all_appointments, clinics=clinics, clinics_to_show=dict(list(clinics.items())[:4]), matching_clinics=matching_clinics, search_word=search_word)

def get_time_preference(time):
    hour = time.hour
    if hour < 12:
        return 'morning'
    elif hour < 16:
        return 'afternoon'
    else:
        return 'evening'
    
@app.route('/all_clinics')
def all_clinics():
    return render_template('all_clinics.html', clinics=clinics)
    
@app.route('/<clinic>/booking', methods=['GET', 'POST'])
def clinic_booking(clinic):
    clinic_info = clinics.get(clinic)
    if request.method == 'POST':
        if 'username' in session:
            username = session['username']
            user_details = users.get(username)
            if user_details:
                name = user_details.get('name')
                phone_number = user_details.get('phone_number')
                date = request.form['date']
                time = request.form['time']
                
                return render_template("booking_confirmation.html", 
                                       name=name, 
                                       phone_number=phone_number, 
                                       clinic=clinic_info['name'], 
                                       address=clinic_info['address'], 
                                       date=date, 
                                       time=time)
        return redirect(url_for('login'))  # Redirect to login if user not logged in
    return render_template("clinicpage.html", clinic=clinic_info)

@app.route('/booking_confirmation', methods=['POST'])
def booking_confirmation():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect if user not logged in

    # Fetch user details from the users dictionary using the username stored in the session
    username = session['username']
    
    user_details = users[username]

    # Fetch clinic name, date, and time from the form data
    clinic_name = request.form.get('clinic')
    date = request.form.get('date')
    time = request.form.get('time')

    # Fetch clinic details (address) using the clinic name
    clinic_key = None
    for key, clinic_info in clinics.items():
        if clinic_info['name'] == clinic_name:
            clinic_key = key
            break
    
    clinic_info = clinics[clinic_key]


    # Send the booking confirmation here
    client = Client(account_sid, auth_token)

    message = client.messages.create(
    to=user_details.get('phone_number'),
    from_="+15714188985",
    body= f'Hi {user_details["name"]}, \nThis is to notify you that your appointment at {clinic_info["name"]} at {time} on {date} has been successfully booked! \
            \nYou will be sent a reminder 24 hours before your appointment! \
            \nThank you for booking through HealthLink! \
            \nHave a great day!')
    # Render the booking confirmation template with user and clinic details
    return render_template("booking_confirmation.html", 
                           username=username,
                           name=user_details['name'],
                           phone_number=user_details['phone_number'],
                           clinic=clinic_info['name'],
                           address=clinic_info['address'],
                           date=date,
                           time=time)

if __name__ == '__main__':
    app.run(debug=True)