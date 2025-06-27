from markupsafe import Markup
from flask import Flask, render_template, url_for, redirect, session, abort, jsonify, request, send_file
from wtforms import StringField, SubmitField, PasswordField
from flask_wtf import FlaskForm
from flask_bootstrap5 import Bootstrap
import os
from dotenv import load_dotenv
import json
from functools import wraps
import hmac
import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__, static_url_path='/static')

app.config["SECRET_KEY"] = os.environ.get("FLASK_KEY")
bootstrap = Bootstrap(app)
load_dotenv()

# _____________ FORMS _____________#


class Login(FlaskForm):
    user_name = StringField(label='username')
    password = PasswordField(label="password")
    submit = SubmitField("login")


# --------- Functions -------#

def load_data(filepath):
    """
    Loads the content of the data.json and arranges them based on id
    :param filepath: The path to the data.json
    :return: a dictionary
    """
    with open(filepath) as f:
        data = json.load(f)
    return data


def requires_auth(f):
    """
    A function decorator which checks if a user is authenticated before the access protected routes.
    :param f: Function input.
    :return: the function out.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "authenticated" not in session:
            return abort(404)
        return f(*args, **kwargs)
    return decorated_function


def generate_signed_id(project_id):
    return hmac.new(app.config["SECRET_KEY"].encode(), project_id.encode(), hashlib.sha256).hexdigest()


def verify_signed_id(signed_id, project_id):
    expected_signed_id = generate_signed_id(project_id)
    return hmac.compare_digest(signed_id, expected_signed_id)


def send_email(name: str, sender_email: str, message: str) -> bool:
    """
    Uses the MIMEMultipart library to create a message object, allowing multiple file types.
    It then uses this instance to set the sender, recipient, and subject of the email.
    Use the smtplib, which authenticates and sends the email.
    Any errors are catch and print to the terminal.
    :param name: Name of the Sender.
    :param sender_email: The email address of the sender.
    :param message: The message sent by the user.
    :return: A boolean if email sent was successful or not.
    """
    # Email parameters
    receiver_email = os.environ.get("EMAIL")
    subject = f"Message from {name}"

    # Message
    msg = MIMEMultipart()
    msg["From"] = sender_email.strip()
    msg["To"] = receiver_email.strip()
    msg["Subject"] = subject
    body = f"Name: {name}\nEmail: {sender_email}\nMessage: {message}"
    msg.attach(MIMEText(body, "plain"))

    # Send eamail
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(receiver_email, os.environ.get("EMAIL_PASSWORD2"))
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def load_resume():
    resume_path = os.path.join(os.path.dirname(__file__), "resume.json")
    with open(resume_path, encoding="utf-8") as f:
        return json.load(f)


# --------- Routes ---------#
@app.route('/')
def home():

    try:
        with open("data.json") as data_file:
            data = json.load(data_file)
    except FileNotFoundError:
        # If no project is found we stay with and empty dict, to avoid template errors.
        data = {}

    return render_template('index2.html',
                           page_title="Galabe Oryn - Portfolio",
                           page_description="Portfolio of a Full Stack Developer and Python Enthusiast.",
                           og_image="images/logo2.jpg",
                           show_login=not session.get('authenticated'),
                           **data)


@app.route("/resume")
def resume():
    data = load_resume()
    return render_template("resume.html",
                           page_title="Galabe Oryn - Resume",
                           page_description="My Resume",
                           og_image="images/logo2.jpg",
                           **data)

#
# @app.route("/resume/download")
# def download_resume():
#     data = load_resume()
#     # template
#     resume_html = render_template("resume.html", **data)
#
#     # convert to pdf
#     pdf = HTML(string=resume_html).write_pdf()
#
#     # Serve downloadable pdf
#     return send_file(
#         io.BytesIO(pdf),
#         mimetype="application/pdf",
#         download_name="Galabe_Oryn_Resume.pdf"
#     )

@app.route("/contact", methods=["POST"])
def contact():
    name = request.form["name"]
    sender_email = request.form["email"]
    message = request.form["message"]
    if send_email(name, sender_email, message):
        return redirect(url_for("home"))
    else:
        return "Error sending message", 500



@app.route("/login", methods=["GET", "POST"])
def login():
    form = Login()
    if form.validate_on_submit():
        username = form.user_name.data
        password = form.password.data
        if username == os.environ.get('USER_NAME') and password == os.environ.get("PASSWORD"):
            session["authenticated"] = True
            return redirect(url_for("home"))
        else:
            abort(404)
    return render_template("login.html", form=form)


@app.route("/projects")
@requires_auth
def get_projects():
    projects = load_data("data.json")
    return jsonify(projects)


@app.route("/delete-project/<string:signed_id>")
@requires_auth
def delete_project(signed_id: str):
    data_dict = load_data("data.json")
    for title, details in list(data_dict.items()):
        if details["signed_id"] == signed_id:
            if verify_signed_id(signed_id=signed_id, project_id=str(details["project_id"])):
                del data_dict[title]
                break
    with open('data.json', "w") as file:
        json.dump(data_dict, file, indent=4)
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    if "authenticated" in session:
        session.clear()
    return redirect(url_for("home"))

#
# @app.route("/download", methods=["POST", "GET"])
# def download_resume2():
#     try:
#         client = pdfcrowd.HtmlToPdfClient("demo", "ce544b6ea52a5621fb9d55f8b542d14d")
#         client.setContentViewportWidth("balanced")
#         client.convertUrlToFile("http://127.0.0.1:5000/resume", "name.pdf")
#     except pdfcrowd.Error as why:
#         sys.stderr.write("PDFCrowd Error: {}\n".format(why))
#         print(why)
#     return redirect(request.url)


@app.route("/pdf-resume")
def serve_resume():
    return send_file("static/certifications/resume.pdf", as_attachment=False)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")

