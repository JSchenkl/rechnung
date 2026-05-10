import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, UserMixin
from app import login_manager

auth_bp = Blueprint('auth', __name__)


class AdminUser(UserMixin):
    id = 'admin'
    name = 'Julius Schenkl'


_admin = AdminUser()


@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return _admin
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        stored = current_app.config['ADMIN_PASSWORD']
        if secrets.compare_digest(password, stored):
            login_user(_admin, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        flash('Falsches Passwort.', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
