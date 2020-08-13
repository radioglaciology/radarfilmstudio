from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class SignupForm(FlaskForm):
    invite_code = StringField('Invite Code', validators=[DataRequired()])

    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])

    email = StringField('Email', validators=[Length(min=6), Email(message="Enter a valid email."), DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message="Please select a longer password.")])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match.")])

    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message="Enter a valid email.")])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')