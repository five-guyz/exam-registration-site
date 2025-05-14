from flask import Flask, session, render_template, request, redirect, url_for, Response
from flask import flash
import mysql.connector
from flask import Response
from datetime import datetime, timedelta



# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # Leave empty if you're using no password
    database="csn_exam_registration"
)

cursor = db.cursor()

# Route: Home - Role selection page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student_portal')
def student_portal():
    return render_template('student_portal.html')

@app.route('/faculty_portal')
def faculty_portal():
    return render_template('faculty_portal.html')

# Route: Student registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip()
        nshe_id = request.form['nshe_id'].strip()
        password = nshe_id

        if not nshe_id.isdigit() or len(nshe_id) != 10:
            return render_template('register.html', error="NSHE ID must be exactly 10 digits.")

        expected_email = f"{nshe_id}@student.csn.edu"
        if email.lower() != expected_email.lower():
            return render_template('register.html', error="Email must match NSHE ID (e.g., NSHE_ID@student.csn.edu).")

        # Check if email already exists
        check_query = "SELECT * FROM Authentication WHERE Email = %s"
        cursor.execute(check_query, (email,))
        if cursor.fetchone():
            return render_template('register.html', error="This email is already registered. Please log in.")

        # Insert into Authentication table
        auth_query = """
            INSERT INTO Authentication (Email, PasswordHash, Role)
            VALUES (%s, %s, 'Student')
        """
        cursor.execute(auth_query, (email, password))
        db.commit()
        auth_id = cursor.lastrowid

        # Insert into Students table
        student_query = """
            INSERT INTO Students (AuthID, FirstName, LastName, Email, NsheID)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(student_query, (auth_id, first_name, last_name, email, nshe_id))
        db.commit()

        # Fetch the correct StudentID using AuthID
        cursor.execute("SELECT StudentID FROM Students WHERE AuthID = %s", (auth_id,))
        student_id = cursor.fetchone()[0]

        # Set session values
        session['student_id'] = student_id
        session['student_name'] = first_name

        return redirect(url_for('confirmation'))

    return render_template('register.html', error=None)

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if role == "Faculty":
        # Try to find existing faculty
        cursor.execute("""
            SELECT Email FROM Authentication
            WHERE Email = %s AND PasswordHash = %s AND Role = 'Faculty'
        """, (email, password))
        result = cursor.fetchone()

        # If not found, auto-create faculty if email ends with @csn.edu
        if not result and email.endswith('@csn.edu'):
            cursor.execute("""
                INSERT INTO Authentication (Email, PasswordHash, Role)
                VALUES (%s, %s, 'Faculty')
            """, (email, password))
            db.commit()
            result = (email,)  # Simulate a successful fetch

        if result:
            session['faculty_name'] = email.split('@')[0].capitalize()
            return redirect(url_for('faculty_dashboard'))
        else:
            flash("Invalid faculty credentials.", "error")
            return redirect(url_for('faculty_portal'))
    else:
        # Student login logic
        query = """
            SELECT s.StudentID, s.FirstName
            FROM Authentication a
            JOIN Students s ON a.Email = s.Email
            WHERE a.Email = %s AND a.PasswordHash = %s AND a.Role = 'Student'
        """
        cursor.execute(query, (email, password))
        result = cursor.fetchone()

        if result:
            student_id, student_name = result

            # Fetch available sessions
            session_query = """
                SELECT cs.SessionID, c.CertName, l.CampusName, cs.SessionDate, cs.SessionTime,
                       f.FirstName, cs.SeatsAvailable
                FROM CertificationSessions cs
                JOIN Certifications c ON cs.CertID = c.CertID
                JOIN Location l ON cs.CampusID = l.CampusID
                JOIN Faculty f ON cs.FacultyID = f.FacultyID
                WHERE cs.SeatsAvailable > 0
                ORDER BY cs.SessionDate, cs.SessionTime
            """
            cursor.execute(session_query)
            session_rows = cursor.fetchall()

            available_sessions = [
                {
                    'session_id': row[0],
                    'exam_name': row[1],
                    'campus': row[2],
                    'date': row[3].strftime('%Y-%m-%d'),
                    'time': str(row[4])[:-3],  # Trims seconds, e.g., "14:30:00" → "14:30"
                    'proctor': row[5],
                    'seats': row[6]
                }
                for row in session_rows
            ]

            session['student_id'] = student_id
            session['student_name'] = student_name
            return redirect(url_for('dashboard'))

        else:
            return render_template('student_portal.html', error="Invalid student login.")

@app.route('/register_exam', methods=['POST'])
def register_exam():
    session_id = request.form['session_id']
    student_id = session.get('student_id')  # Replace with session logic later

    try:
        # 1. Get the CertID of the selected session
        cursor.execute("SELECT CertID FROM CertificationSessions WHERE SessionID = %s", (session_id,))
        cert_row = cursor.fetchone()
        if not cert_row:
            flash("Session not found.", "error")
            return redirect(url_for('dashboard'))

        cert_id = cert_row[0]

        # 2. Check for duplicate booking of this exam type
        cursor.execute("""
            SELECT COUNT(*)
            FROM Registration r
            JOIN CertificationSessions cs ON r.SessionID = cs.SessionID
            WHERE r.StudentID = %s AND cs.CertID = %s
        """, (student_id, cert_id))
        if cursor.fetchone()[0] > 0:
            flash("You've already registered for this exam type.", "error")
            return redirect(url_for('dashboard'))

        # 3. Check if student has already booked 3 different exam types
        cursor.execute("""
            SELECT COUNT(DISTINCT cs.CertID)
            FROM Registration r
            JOIN CertificationSessions cs ON r.SessionID = cs.SessionID
            WHERE r.StudentID = %s
        """, (student_id,))
        if cursor.fetchone()[0] >= 3:
            flash("You can only register for a maximum of 3 different exams.", "error")
            return redirect(url_for('dashboard'))

        # 4. Check if session has available seats (live count)
        cursor.execute("""
            SELECT SeatsAvailable FROM CertificationSessions WHERE SessionID = %s
        """, (session_id,))
        seats_row = cursor.fetchone()
        if not seats_row or seats_row[0] <= 0:
            flash("Sorry, this session is full.", "error")
            return redirect(url_for('dashboard'))

        # Double-check registered count (to prevent race condition)
        cursor.execute("""
            SELECT COUNT(*) FROM Registration WHERE SessionID = %s
        """, (session_id,))
        booked = cursor.fetchone()[0]
        if booked >= seats_row[0]:
            flash("This session has just filled up.", "error")
            return redirect(url_for('dashboard'))

        # 5. Insert registration
        cursor.execute("""
            INSERT INTO Registration (StudentID, SessionID, RegistrationDate)
            VALUES (%s, %s, CURDATE())
        """, (student_id, session_id))

        # 6. Update seat count
        cursor.execute("""
            UPDATE CertificationSessions
            SET SeatsAvailable = SeatsAvailable - 1
            WHERE SessionID = %s
        """, (session_id,))

        db.commit()
        flash("You have successfully registered for the session.", "success")

    except mysql.connector.Error as err:
        flash(f"Registration error: {err}", "error")

    return redirect(url_for('dashboard'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
    student_id = session.get('student_id')
    student_name = session.get('student_name')

    if not student_id:
        return redirect(url_for('student_portal'))

    # Get filters
    selected_cert = request.args.get('cert')
    selected_campus = request.args.get('campus')
    selected_date = request.args.get('date')
    selected_time = request.args.get('time')

    # Clean filter inputs
    try:
        selected_cert = int(selected_cert) if selected_cert else None
        selected_campus = int(selected_campus) if selected_campus else None
    except ValueError:
        selected_cert = selected_campus = None

    # Dropdown options
    cursor.execute("SELECT CertID, CertName FROM Certifications")
    certifications = cursor.fetchall()

    cursor.execute("SELECT CampusID, CampusName FROM Location")
    campuses = cursor.fetchall()

    times = [
        ('morning', 'Morning (08:00 - 11:59)'),
        ('afternoon', 'Afternoon (12:00 - 15:59)'),
        ('evening', 'Evening (16:00 - 17:00)')
    ]

    # Available sessions
    query = """
        SELECT cs.SessionID, c.CertName, l.CampusName, cs.SessionDate, cs.SessionTime,
               cs.ProctorName, cs.SeatsAvailable
        FROM CertificationSessions cs
        JOIN Certifications c ON cs.CertID = c.CertID
        JOIN Location l ON cs.CampusID = l.CampusID
        WHERE cs.SeatsAvailable > 0
    """
    values = []

    if selected_cert:
        query += " AND cs.CertID = %s"
        values.append(selected_cert)
    if selected_campus:
        query += " AND cs.CampusID = %s"
        values.append(selected_campus)
    if selected_date:
        query += " AND cs.SessionDate = %s"
        values.append(selected_date)
    if selected_time:
        if selected_time == 'morning':
            query += " AND HOUR(cs.SessionTime) BETWEEN 8 AND 11"
        elif selected_time == 'afternoon':
            query += " AND HOUR(cs.SessionTime) BETWEEN 12 AND 15"
        elif selected_time == 'evening':
            query += " AND HOUR(cs.SessionTime) BETWEEN 16 AND 17"

    cursor.execute(query, values)
    rows = cursor.fetchall()

    available_sessions = []
    for row in rows:
        session_date = row[3]
        session_time = row[4]

        if isinstance(session_date, timedelta):
            session_date = (datetime.min + session_date).date()
        if isinstance(session_time, timedelta):
            session_time = (datetime.min + session_time).time()

        available_sessions.append({
            'session_id': row[0],
            'exam_name': row[1],
            'campus': row[2],
            'date': session_date.strftime('%Y-%m-%d'),
            'time': session_time.strftime('%H:%M'),
            'proctor': row[5],
            'seats': row[6]
        })

    # Booked sessions
    cursor.execute("""
        SELECT cs.SessionID, c.CertName, l.CampusName, cs.SessionDate, cs.SessionTime, cs.ProctorName
        FROM Registration r
        JOIN CertificationSessions cs ON r.SessionID = cs.SessionID
        JOIN Certifications c ON cs.CertID = c.CertID
        JOIN Location l ON cs.CampusID = l.CampusID
        WHERE r.StudentID = %s
    """, (student_id,))
    booked_rows = cursor.fetchall()

    booked_sessions = []
    for row in booked_rows:
        session_id = row[0]
        exam_name = row[1]
        campus = row[2]
        session_date = row[3]
        session_time = row[4]
        proctor = row[5]

        if isinstance(session_date, timedelta):
            session_date = (datetime.min + session_date).date()
        if isinstance(session_time, timedelta):
            session_time = (datetime.min + session_time).time()

        booked_sessions.append({
            'session_id': session_id,
            'exam_name': exam_name,
            'campus': campus,
            'date': session_date.strftime('%Y-%m-%d'),
            'time': session_time.strftime('%H:%M'),
            'proctor': proctor
        })

    return render_template('dashboard.html',
        name=student_name,
        student_id=student_id,
        available_sessions=available_sessions,
        booked_sessions=booked_sessions,
        certifications=certifications,
        campuses=campuses,
        times=times,
        selected_cert=selected_cert,
        selected_campus=selected_campus,
        selected_date=selected_date,
        selected_time=selected_time
    )

@app.route('/confirmation')
def confirmation():
    return redirect(url_for('dashboard'))


@app.route('/history')
def history():
    cursor.execute("SELECT * FROM Students")
    students = cursor.fetchall()
    return render_template('history.html', registrations=students)

@app.route('/faculty_dashboard')
def faculty_dashboard():
    faculty_name = session.get('faculty_name', 'Faculty')

    # Get filters
    selected_cert = request.args.get('cert')
    selected_campus = request.args.get('campus')
    selected_date = request.args.get('date')

    query = """
        SELECT CONCAT(s.FirstName, ' ', s.LastName), s.Email, c.CertName, l.CampusName, cs.SessionDate, cs.SessionTime
        FROM Registration r
        JOIN Students s ON r.StudentID = s.StudentID
        JOIN CertificationSessions cs ON r.SessionID = cs.SessionID
        JOIN Certifications c ON cs.CertID = c.CertID
        JOIN Location l ON cs.CampusID = l.CampusID
        WHERE 1=1
    """
    values = []

    if selected_cert:
        query += " AND c.CertID = %s"
        values.append(selected_cert)
    if selected_campus:
        query += " AND l.CampusID = %s"
        values.append(selected_campus)
    if selected_date:
        query += " AND cs.SessionDate = %s"
        values.append(selected_date)

    cursor.execute(query, values)
    results = cursor.fetchall()

    # Load filter dropdowns
    cursor.execute("SELECT CertID, CertName FROM Certifications")
    certifications = cursor.fetchall()

    cursor.execute("SELECT CampusID, CampusName FROM Location")
    campuses = cursor.fetchall()

    return render_template('faculty_dashboard.html',
                           name=faculty_name,
                           results=[{
                               'name': row[0],
                               'email': row[1],
                               'certification': row[2],
                               'campus': row[3],
                               'date': row[4].strftime('%Y-%m-%d'),
                               'time': (datetime.min + row[5]).strftime('%H:%M') if isinstance(row[5], timedelta) else row[5].strftime('%H:%M')
                           } for row in results],
                           certifications=certifications,
                           campuses=campuses,
                           selected_cert=selected_cert,
                           selected_campus=selected_campus,
                           selected_date=selected_date)


@app.route('/faculty_dashboard/export')
def faculty_dashboard_export():
    selected_cert = request.args.get('cert')
    selected_campus = request.args.get('campus')
    selected_date = request.args.get('date')

    query = """
        SELECT CONCAT(s.FirstName, ' ', s.LastName) AS name, s.Email, c.CertName, l.CampusName, cs.SessionDate, cs.SessionTime
        FROM Registration r
        JOIN Students s ON r.StudentID = s.StudentID
        JOIN CertificationSessions cs ON r.SessionID = cs.SessionID
        JOIN Certifications c ON cs.CertID = c.CertID
        JOIN Location l ON cs.CampusID = l.CampusID
        WHERE 1=1
    """
    filters = []
    values = []

    if selected_cert:
        query += " AND c.CertID = %s"
        values.append(selected_cert)
    if selected_campus:
        query += " AND l.CampusID = %s"
        values.append(selected_campus)
    if selected_date:
        query += " AND cs.SessionDate = %s"
        values.append(selected_date)

    cursor = db.cursor()
    cursor.execute(query, values)
    data = cursor.fetchall()

    # Generate CSV
    output = "Student Name,Email,Certification,Campus,Date,Time\n"
    for row in data:
        output += ",".join([str(field) for field in row]) + "\n"

    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=faculty_export.csv"}
    )

@app.route('/cancel_exam', methods=['POST'])
def cancel_exam():
    session_id = request.form.get('session_id')
    student_id = request.form.get('student_id')

    if not session_id or not student_id:
        print("Missing session_id or student_id")  # Debug log
        flash("Missing data to cancel reservation.", "error")
        return redirect(url_for('dashboard'))

    try:
        # Delete the reservation
        cursor.execute("""
            DELETE FROM Registration 
            WHERE StudentID = %s AND SessionID = %s
        """, (student_id, session_id))
        print(f"Deleted registration for StudentID: {student_id}, SessionID: {session_id}")  # Debug log

        # Increase seat availability back by 1
        cursor.execute("""
            UPDATE CertificationSessions 
            SET SeatsAvailable = SeatsAvailable + 1 
            WHERE SessionID = %s
        """, (session_id,))
        print(f"Updated seats for SessionID: {session_id}")  # Debug log

        db.commit()
        flash("You have successfully cancelled your reservation.", "success")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")  # Debug log
        flash(f"Cancellation error: {err}", "error")

    return redirect(url_for('dashboard'))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
