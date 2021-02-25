from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    """ Model for user accounts """

    __tablename__ = 'flasklogin-users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    first_name = db.Column(db.String, nullable=False, unique=False)
    last_name = db.Column(db.String, nullable=False, unique=False)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False, unique=False)
    created_on = db.Column(db.DateTime, index=False, nullable=False, unique=False)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    write_permission = db.Column(db.Boolean, nullable=False, unique=False, default=False) # Permission to change metadata
    view_greenland = db.Column(db.Boolean, nullable=False, unique=False, default=False) # Permission to view greenland data

    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.email}, created on {self.created_on}, write permission: {self.write_permission}>'

