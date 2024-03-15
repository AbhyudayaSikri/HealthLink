from flask import Flask, render_template, request, redirect, url_for, session
import datetime

clinics = {"sanomed":
            {
            "name": "Sanomed Medical Clinic", 
            "picture": "https://sanomedclinic.ca/wp-content/uploads/2021/10/Pharmasave-SanoMed-Medical-Walk-in-Clinic-Toronto.jpg.webp",
            "address": "1000 Bay St. Unit 2, Toronto, ON M5S 3A8",
            "available_slots": {
                                "2024-03-15": ["10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM"],
                                "2024-03-16": ["9:00 AM", "10:00 AM", "11:00 AM", "1:00 PM"],
                                "2024-03-17": ["9:30 AM", "10:30 AM", "11:30 AM", "2:00 PM"],
                                },   
            "reviews": ["best clinic ever!!!", "jeff is helping build this"],
            },

            "hearthealth":
            {
            "name": "HeartHealth Medical",
            "picture": "https://lh3.googleusercontent.com/p/AF1QipMzpb9lDKTh4sUsIj-M3TYa3S5OwI0RDgw4iZ9p=s1360-w1360-h1020",
            "address": "360 College St Unit 103, Toronto, ON M5T 1S6",
            "available_slots": {
                                "2024-03-15": ["9:00 AM", "10:00 AM", "1:00 PM", "2:00 PM"],
                                "2024-03-16": ["10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM"],
                                "2024-03-17": ["9:30 AM", "10:30 AM", "11:30 AM", "1:00 PM"],
                                },
            "reviews": ["worst clinic ever!!!", "nivedha is doing this herself"],
            },
           }

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

@app.route('/home')
def home():
    # Collect all appointments from all clinics
    all_appointments = []

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

    return render_template('homepage.html', appointments=all_appointments, clinics=clinics)

def get_time_preference(time):
    hour = time.hour
    if hour < 12:
        return 'morning'
    elif hour < 17:
        return 'afternoon'
    else:
        return 'evening'
    
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