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
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        nshe_id = request.form['nshe_id']
        password = nshe_id  # Still using NSHE as password

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



# Route: Login handler (can be expanded later)
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    # Lookup student by email and password
    query = """
        SELECT s.FirstName
        FROM Authentication a
        JOIN Students s ON a.Email = s.Email
        WHERE a.Email = %s AND a.PasswordHash = %s AND a.Role = 'Student'
    """
    cursor.execute(query, (email, password))
    result = cursor.fetchone()

    if result:
        student_name = result[0]
        return render_template('dashboard.html', name=student_name)
    else:
        return render_template('student_portal.html', error="Invalid email or password.")


@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/history')
def history():
    
    cursor.execute("SELECT * FROM Students")
    students = cursor.fetchall()
    return render_template('history.html', registrations=students)

@app.route('/faculty_dashboard')
def faculty_dashboard():
    return "Welcome to Faculty Dashboard (To be built)"

if __name__ == '__main__':
    app.run(debug=True)
