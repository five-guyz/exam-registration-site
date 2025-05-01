from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

# Initialize Flask app
app = Flask(__name__)

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
        password = nshe_id  # Still using NSHE as password
        
        

        # Validation for NSHE ID length
        if not nshe_id.isdigit() or len(nshe_id) != 10:
            return render_template('register.html', error="NSHE ID must be exactly 10 digits.")

        expected_email = f"{nshe_id}@student.csn.edu"
        if email.lower() != expected_email.lower():
            return render_template('register.html', error="Email must match NSHE ID (e.g., NSHE_ID@student.csn.edu).")

        # Check if email already exists
        check_query = "SELECT * FROM Authentication WHERE Email = %s"
        cursor.execute(check_query, (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Pass error message to template
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
            VALUES (%s, %s,  %s, %s, %s)
        """
        cursor.execute(student_query, (auth_id, first_name, last_name, email, nshe_id))
        db.commit()

        return redirect(url_for('confirmation'))

    # GET request
    return render_template('register.html', error=None)



@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    available_sessions = []  # with an underscore


    if role == "Faculty":
        # Faculty login logic
        query = """
            SELECT f.FirstName
            FROM Authentication a
            JOIN Faculty f ON a.Email = f.Email
            WHERE a.Email = %s AND a.PasswordHash = %s AND a.Role = 'Faculty'
        """
        cursor.execute(query, (email, password))
        result = cursor.fetchone()

        if result:
            faculty_name = result[0]
            return render_template('faculty_dashboard.html', name=faculty_name)
        else:
            return render_template('faculty_portal.html', error="Invalid faculty login.")
    
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

            # (Session query logic here...)

            return render_template('dashboard.html', name=student_name, available_sessions=available_sessions)
        else:
            return render_template('student_portal.html', error="Invalid student login.")


@app.route('/register_exam', methods=['POST'])
def register_exam():
    session_id = request.form['session_id']
    
    # For now, just use a static student_id (later we can use session-based login)
    # In production, this should come from a session after login
    student_id = 1  # ← Replace with actual logic in future

    # Insert into Registration table
    try:
        insert_query = """
            INSERT INTO Registration (StudentID, SessionID, RegistrationDate)
            VALUES (%s, %s, CURDATE())
        """
        cursor.execute(insert_query, (student_id, session_id))
        db.commit()
        return redirect(url_for('confirmation'))
    except mysql.connector.Error as err:
        return f"Registration error: {err}", 400


@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/history')
def history():
    
    cursor.execute("SELECT * FROM Students")
    students = cursor.fetchall()
    return render_template('history.html', registrations=students)

@app.route('/faculty_dashboard', methods=['GET'])
def faculty_dashboard():
    email = request.args.get('email')  # Optional: or pull from session later
    faculty_name = "Faculty"  # Static placeholder, update if session logic is added

    # Get filters from query string
    selected_cert = request.args.get('cert')
    selected_campus = request.args.get('campus')
    selected_date = request.args.get('date')

    # Build base query
    query = """
        SELECT CONCAT(s.FirstName, ' ', s.LastName) AS name, s.Email, c.CertName AS certification,
               l.CampusName AS campus, cs.SessionDate AS date, cs.SessionTime AS time
        FROM Registration r
        JOIN Students s ON r.StudentID = s.StudentID
        JOIN CertificationSessions cs ON r.SessionID = cs.SessionID
        JOIN Certifications c ON cs.CertID = c.CertID
        JOIN Location l ON cs.CampusID = l.CampusID
        WHERE 1 = 1
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

    cursor.execute(query, values)
    results = cursor.fetchall()

    # Get dropdown options
    cursor.execute("SELECT CertID, CertName FROM Certifications")
    certifications = cursor.fetchall()

    cursor.execute("SELECT CampusID, CampusName FROM Location")
    campuses = cursor.fetchall()

    return render_template('faculty_dashboard.html',
                           name=faculty_name,
                           results=[
                               {
                                   'name': row[0],
                                   'email': row[1],
                                   'certification': row[2],
                                   'campus': row[3],
                                   'date': row[4].strftime('%b %d, %Y'),
                                   'time': row[5].strftime('%I:%M %p')
                               } for row in results
                           ],
                           certifications=certifications,
                           campuses=campuses,
                           selected_cert=selected_cert,
                           selected_campus=selected_campus,
                           selected_date=selected_date)


if __name__ == '__main__':
    app.run(debug=True)
