from flask import Blueprint, redirect, url_for, flash, render_template, request
from flaskblog import db, bcrypt
from flask_login import current_user, login_user, login_required, logout_user
from flaskblog.models import User, Post
from flaskblog.users.forms import RegistrationForm, LoginForm, UpdateForm, RequestResetForm, PasswordResetForm
from flaskblog.users.utils import save_picture, send_reset_mail

users = Blueprint('users', __name__)


@users.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hash_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hash_pw)
        db.session.add(user)
        db.session.commit()
        flash('Başarılı üyelik', 'success')
        return redirect(url_for('users.login'))
    return render_template("register.html", title="Üye Ol", form=form)


@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if next_page:
                next_page = next_page[1:]
            return redirect(url_for(next_page)) if next_page else redirect(url_for('main.home'))
        else:
            flash('Hatalı giriş. E-mail ya da şifrenizi kontrol edin.', 'danger')
    return render_template("login.html", title="Giriş", form=form)


@users.route('/logout')
def log_out():
    logout_user()
    return redirect(url_for('main.home'))


@users.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateForm()
    if form.validate_on_submit():
        if form.file:
            new_image = save_picture(form.file.data)
            current_user.image_file = new_image
            db.session.commit()
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Bilgiler güncellendi.', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Hesabım', image_file=image_file, form=form)


@users.route('/user/<string:username>')
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=3)
    return render_template("user_posts.html", posts=posts, title=f"{username}", user=user)


@users.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_mail(user)
        flash('Şifre yenileme talebiniz için e-posta adresinize link gönderildi.', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', form=form, legend='Şifre Yenileme')


@users.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Böyle bir kullanıcı yok veya talebin süresi bitmiş', 'warning')
        return redirect(url_for('users.reset_request'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        hash_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hash_pw
        db.session.commit()
        flash('Şifre başarılı bir şekilde değiştirildi', 'success')
        return redirect(url_for('users.login'))
    return render_template('request_password.html', form=form, legend='Şifre Yenileme')