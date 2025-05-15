
# place in where the libraries are at
from flask_login import current_user, LoginManager, UserMixin, current_user, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from email.utils import formataddr
from dotenv import load_dotenv


# place right after importing libraires but before the index - appleis to everything until the next "insert into" comment
PORT = 587
EMAIL_SERVER = "smtp.gmail.com"


load_dotenv()

sender_email   = os.getenv("EMAIL")
password_email = os.getenv("PASSWORD")
# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # redirect to the login page if not logged in

# Example User class
class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

# User loader function
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Ensure that these are loaded correctly before trying to log in
if sender_email and password_email:
    try:
        # Login with the loaded credentials
        with smtplib.SMTP(EMAIL_SERVER, PORT) as server:
            server.starttls()  # Start TLS encryption for security
            server.login(sender_email, password_email)  # Login using the loaded email and password
            print("Login success!")
    except Exception as e:
        print(f"Error during email login: {e}")
else:
    print("Error: EMAIL or PASSWORD is not set in the .env file.")

def send_email_account_confirmation(subject, receiver_email, name):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = formataddr(("College of Southern Nevada", f"{sender_email}"))
    msg["To"]      = receiver_email
    msg["BCC"]     = sender_email



    msg.set_content(
        f"""\
        Hello {name},
	        This is your confirmation email for your successful account creation!
            We wish the best on all your certification tests! Good luck Coyote!
        """
    )

    msg.add_alternative (
        f"""
    <html>
        <body> 
          <p>Hello {name},</p>
          <p>This is your confirmation email for your successful account creation!</p>
          <p>We wish the best on all your certification tests! Good luck Coyote!</p>
        </body>
    </html>
    """,
          subtype="html",
        )
    try:
        with smtplib.SMTP(EMAIL_SERVER, PORT)  as server:
          server.starttls()
          server.login(sender_email, password_email)
          server.sendmail(sender_email, receiver_email, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")

def send_email_exam_confirmation(subject, receiver_email, name):
    if not receiver_email:
        print("Error: receiver_email is None.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = formataddr(("College of Southern Nevada", f"{sender_email}"))
    msg["To"]      = receiver_email
    msg["BCC"]     = sender_email



    msg.set_content(
        f"""\
       Hello {name} 
            You have successfully registered for your certification test.
            We wish you the best on your test Coyote!
 

        """
    )

    msg.add_alternative (
        f"""
    <html>
        <body> 
          <p>Hello {name},</p>
          <p>You have successfully registered  for your certification test.</p>
          <p>We wish you the best on your test Coyote!</p>
        </body>
    </html>
    """,
          subtype="html",
        )
    try:
        with smtplib.SMTP(EMAIL_SERVER, PORT)  as server:
          server.starttls()
          server.login(sender_email, password_email)
          server.sendmail(sender_email, receiver_email, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")




        # insert in account registration function right below the db.commit()  "  session['student_name']  = first_name "


        session['student_email'] = email


        send_email_account_confirmation(
            subject="Successful Account Creation",
            name=first_name,
            receiver_email=email,

        )



        # insert in exam registration function right below the db.commit() 
        student_name= session.get('student_name')
        student_email= session.get('student_email')

        send_email_exam_confirmation(
            subject="Successful Exam Registration",
            name=student_name,
            receiver_email=student_email,
    
        )
