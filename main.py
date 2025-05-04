from markupsafe import Markup
from flask import Flask, render_template, url_for, redirect, session, abort, jsonify, request
from wtforms import StringField, TextAreaField, URLField, SubmitField, PasswordField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, ValidationError, URL
from flask_bootstrap5 import Bootstrap
import os
from dotenv import load_dotenv
import json
from functools import wraps
import uuid
import hmac
import hashlib
import smtplib
from email.mime.multipart import  MIMEMultipart
from email.mime.text import MIMEText
from flask_ckeditor import CKEditorField, CKEditor

app = Flask(__name__, static_url_path='/static')

app.config["SECRET_KEY"] = os.environ.get("FLASK_KEY")
bootstrap = Bootstrap(app)
load_dotenv()
ckeditor = CKEditor(app)


class Project(FlaskForm):
    def max_length(self, field):
        """"
        This method ensures Titles dont get to long """
        if len(field.data) > 50:
            raise ValidationError("Should be less than 20 chars.")

    title = StringField(label="Project Title", validators=[DataRequired(), max_length])
    overview = TextAreaField(label="Project Overview", validators=[DataRequired()])
    description = CKEditorField(label="Details of Project", validators=[DataRequired()])
    link = URLField(label="Link", validators=[DataRequired(), URL()])
    submit = SubmitField("Upload")


class Login(FlaskForm):
    user_name = StringField(label='username')
    password = PasswordField(label="password")
    submit = SubmitField("login")


meta_data = {
    "page_title": "My Portfolio - Galabe Oryn",
    "page_description": "Full-Stack dev (Python, Flask) showcasing my projects",
    "og_image": "/images/metaimage.jpeg",
}


def save(data: dict):
    """
    Receives the project data from the backend, which is rendered on the site,
    Saves data in a JSON file.
    The try block contains code that might raise an exception.
    The except block contains code which is executed if this exception is raised.
    :param data: JSON data uploaded from backend
    :return: None
    """
    try:
        with open("data.json", "r") as data_file:
            file = json.load(data_file)
            # json.load() converts json into a python object (dictionary)
    except FileNotFoundError:
        with open("data.json", "w") as data_file:
            # if file not found, we create a new file in write mode.
            json.dump(data, data_file, indent=4)
            # json.dump() converts python object data into json data, and pretty-prints it with and indentation of 4
    except json.JSONDecodeError:
        print("Error decoding JSON")
    except Exception as e:
        print(f"An error occurred: {e}")
    else:
        file.update(data)
        # If no exception occurred during loading of the json, the code updates the file dictionary with new data
        # using the update() method

        with open("data.json", "w") as data_file:
            # The updated file dictionary is then written back to the data.json file using the json.dump()
            json.dump(file, data_file, indent=4)

# def save(data: dict):
#     try:
#         with open("data.json", "w") as data_file:
#             json.dump(data, data_file, indent=4)
#     except Exception as e:
#         print(f"An error occurred: {e}")
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


@app.route("/add-project", methods=["POST", "GET"])
@requires_auth
def add_project():
    form = Project()
    project_id = str(uuid.uuid4())
    signed_id = generate_signed_id(str(project_id))
    if form.validate_on_submit():
        data = {
            f"{form.title.data}": {
                "project_id": project_id,
                "signed_id": signed_id,
                "title": form.title.data,
                "overview": form.overview.data,
                "description": form.description.data,
                "link": form.link.data,
                "gradient": f"aurora-{project_id}"
            }
        }
        save(data)
        return redirect(url_for("home"))
    return render_template("addproject.html", form=form)


@app.route("/")
def home():
    show_login = request.args.get("auth") == os.environ.get("AUTH")
    projects = {}  # Initialize with and empty dictionary
    try:
        with open("data.json") as data_file:
            projects = json.load(data_file)
    except FileNotFoundError:
        # If no project is found we stay with and empty dict, to avoid template errors.
        projects = {}

    return render_template("index.html", projects=projects, show_login=show_login, **meta_data)

#
# @app.route("/edit-project/<string:signed_id>", methods=["POST", "GET"])
# @requires_auth
# def edit_project(signed_id):
#     form = Project()
#     data_dict = load_data("data.json")
#     found_key = None
#     found_details = None
#
#     for project_title, details in data_dict.items():
#         if details["signed_id"] == signed_id:
#             if verify_signed_id(signed_id=signed_id, project_id=str(details["project_id"])):
#                 found_key = project_title
#                 found_details = details
#
#                 form.title.data = details["title"]
#                 form.overview.data = details["overview"]
#                 form.description.data = details["description"]
#                 form.link.data = details["link"]
#                 break  # Stop after getting the correct project.
#             else:
#                return "The sign ID is invalid", 403
#
#     if not found_key:
#         return "Project Not found", 404
#
#     if form.validate_on_submit():
#         try:
#             with open("data.json", "r") as file:
#                 data = json.load(file)
#             for project_title, details in data.items():
#                 if details["signed_id"] == signed_id:
#                     details["overview"] = form.overview.data
#                     details["description"] = form.description.data
#                     details["link"] = form.link.data
#                     break
#
#             with open("data.json", "w") as file:
#                 json.dump(data, file, indent=4)
#             print("Data in data.json updated successfully")
#         except FileNotFoundError:
#             print("Error file not found")
#         except json.JSONDecodeError:
#             print("Error could not decode json")
#         except Exception as e:
#             print(f"Exception occurred: {e}")
#         # new_key = form.title.data
#         # updated_project_data = {
#         #         "project_id": found_details['project_id'],
#         #         "signed_id": signed_id,
#         #         "title": form.title.data,
#         #         "overview": form.overview.data,
#         #         "description": form.description.data,
#         #         "link": form.link.data,
#         #         "gradient": f"aurora-{found_details['project_id']}"
#         # }
#         # if found_key != new_key:
#         #     data_dict.pop(found_key, None)
#         # data_dict[new_key] = updated_project_data
#         # save(data_dict)
#         return redirect(url_for("home"))
#
#     return render_template("addproject.html", form=form)


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


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form["name"]
    sender_email = request.form["email"]
    message = request.form["message"]
    if send_email(name, sender_email, message):
        return redirect(url_for("home"))
    else:
        return "Error sending message", 500


if __name__ == "__main__":
    app.run(debug=False)
