from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    print(f"Username: {username}, Password: {password}")
    
    # For now, redirect to confirmation page
    return redirect(url_for('confirmation'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Grab form data (you can later store this to MySQL)
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        nshe_id = request.form['nshe_id']
        
        # For now, redirect to confirmation
        return redirect(url_for('confirmation'))
    
    return render_template('register.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')


if __name__ == '__main__':
    app.run(debug=True)
