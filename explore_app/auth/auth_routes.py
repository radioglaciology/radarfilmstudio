from datetime import datetime

import logging
from flask import Blueprint, request, render_template, flash, session, url_for, redirect
from flask_login import login_required, logout_user, current_user, login_user

from flask import current_app as app

from .user_forms import SignupForm, LoginForm
from .. import db, login_manager
from ..user import User

auth_bp = Blueprint('auth_bp', __name__, template_folder='templates', static_folder='static')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.map_page'))

    login_form = LoginForm()
    if request.method == 'POST':
        if login_form.validate_on_submit():
            email = login_form.email.data
            password = login_form.password.data
            user = User.query.filter_by(email=email).first()  # Validate Login Attempt
            if user and user.check_password(password=password):
                login_user(user)
                user.last_login = datetime.now()
                db.session.commit()
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main_bp.map_page'))
        else:
            app.logger.debug(f"Login form validation failed")
            for fieldName, errorMessages in login_form.errors.items():
                for err in errorMessages:
                    app.logger.warning(f"{fieldName}: {err}")
        flash('Invalid username/password combination')
        return redirect(url_for('auth_bp.login'))

    return render_template('login.html',
                           form=login_form,
                           breadcrumbs=[('Explorer', '/'),
                                        ('Login', url_for('auth_bp.login'))])


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    signup_form = SignupForm()
    if request.method == 'POST':
        if signup_form.validate_on_submit():
            # Check for invite code
            if signup_form.invite_code.data != app.config['INVITE_CODE']:
                flash('Sorry, the invite code was not recognized.')
                return redirect(url_for('auth_bp.signup'))

            first_name = signup_form.first_name.data
            last_name = signup_form.last_name.data
            email = signup_form.email.data
            password = signup_form.password.data
            app.logger.debug(f"Adding user {first_name} {last_name}")
            existing_user = User.query.filter_by(email=email).first()  # Check if user exists
            app.logger.debug(f"Existing user? {existing_user}")
            if existing_user is None:
                user = User(first_name=first_name, last_name=last_name, email=email, created_on=datetime.now())
                user.set_password(password)
                app.logger.debug(f"Ok. Adding {user}")
                db.session.add(user)
                db.session.commit()  # Create new user
                app.logger.debug(f"Comitted. Logging in...")
                login_user(user)  # Log in as newly created user
                return redirect(url_for('main_bp.map_page'))
            else:
                flash('A user already exists with that email address.')
                return redirect(url_for('auth_bp.signup'))
        else:
            for fieldName, errorMessages in signup_form.errors.items():
                print(f"Error in {fieldName}: {errorMessages}")

    return render_template('signup.html',
                           form=signup_form,
                           breadcrumbs=[('Explorer', '/'),
                                        ('Sign Up', url_for('auth_bp.signup'))])

@login_manager.user_loader
def load_user(user_id):
    app.logger.debug(f"Loading user by id: {user_id}")
    if user_id is not None:
        x = User.query.get(user_id)
        return x
    return None

@login_manager.unauthorized_handler
def unauthorized():
    flash('You must be logged in to view this page.')
    return redirect(url_for('auth_bp.login'))

@auth_bp.route("/logout")
@login_required
def logout():
    app.logger.debug(f"Logging out user {current_user}")
    logout_user()
    return redirect(url_for('main_bp.map_page'))