from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    """ Model for user accounts """

    __tablename__ = 'flasklogin-users'

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String, nullable=False, unique=False)
    last_name = db.Column(db.String, nullable=False, unique=False)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False, unique=False)
    created_on = db.Column(db.DateTime, index=False, nullable=False, unique=False)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    write_permission = db.Column(db.Boolean, nullable=False, unique=False, default=False)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.email}, created on {self.created_on}, write permission: {self.write_permission}>'

    # Manually granting write permissions
    # > from explore_app import db
    # > from explore_app import create_app
    # > app = create_app()
    # > from explore_app.user import User
    # > app.app_context().push()
    # > u = db.session.query(User).get(1)
    # > u.write_permission = True
    # > u
    #   <User teisberg@stanford.edu, created on 2020-04-22 12:14:20.329163, write_permission: True>
    # > db.session.commit()
