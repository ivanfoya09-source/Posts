import os
from uuid import uuid4
import pickle

from flask import Flask, session, request, redirect, render_template, flash, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_wtf import CSRFProtect
from flask_caching import Cache

from models import db, User, Post
from forms import SignIn, SignUp, Postform


load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_URI")
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 10
app.secret_key = os.getenv("SECRET_KEY")
db.init_app(app)
login_manager = LoginManager()
login_manager.login_message = "Для доступу до сторінки спочатку увійдіть"
login_manager.login_view = "sign_in"
login_manager.init_app(app)
csrf_protect = CSRFProtect(app)
cache = Cache(app)

# ----------------------------------------------- 1.Спосіб
# with app.app_context():
#     db.drop_all()
#     db.create_all()


# @login_manager.user_loader
# def get_current_user(id: int):
#     user = cache.get(id)
#     if user:
#         user = pickle.loads(user)
#         print("Беремо дані з кешу...")
#     else:
#         user = User.query.filter_by(id=id).first()
#         cache.set(id, pickle.dumps(user))
#         print("Робимо запит до бази даних...")

#     return user

# -----------------------------------------------2.Спосіб
@login_manager.user_loader
@cache.cached(timeout=15, key_prefix="posts_")
def get_current_user(id: int):
    print("Робимо запит до бази даних...")
    return User.query.filter_by(id=id).first()


# @csrf_protect.exempt
@app.route("/sign-up/", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        username = request.form.get("username")
        user = User.query.filter_by(username=username).first()
        if user:
            flash (f"Користувач з логіном '{username}' вже існує")
            return redirect(url_for("sign_up"))
        
        print("not user")
        user = User(
            username=username,
            first_name=request.form.get("first_name") or None,
            last_name=request.form.get("last_name") or None,
            password=request.form.get("password")
        )
        db.session.add(user)
        db.session.commit()
        flash(f"Користувача з логіном '{username}' успішно заареєстровано")
        return redirect(url_for("sign_in"))
    return render_template("sign_up.html")


@app.route("/sign-in/", methods=["GET", "POST"])
# @csrf_protect.exempt
def sign_in():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user: User = User.query.filter_by(username=username).first()

        print(user, user.is_verify_password(password), user.is_active)
        if not user or not user.is_verify_password(password) or not user.is_active:
            flash("Логін або пароль невірні")
            return redirect(url_for("sign_in"))
        
        login_user(user)
        return redirect(url_for("index"))
    return render_template("sign_in.html")


@app.get("/logout/")
@login_required
def logout():
    flash(f"Коистувач {current_user.username} успішно вийшов із системи")
    logout_user()
    return redirect(url_for("sign_in"))


@csrf_protect.exempt
@app.route("/add-post/", methods=["GET", "POST"])
@login_required
def add_post():
    form = Postform()
    if form.validate_on_submit():
        image_file = request.files.get("image")
        image = None
        if image_file and image_file.filename:
            image_name = secure_filename(image_file.filename)
            image_name = uuid4().hex + "_" + image_name
            image_file.save("static/" + image_name)
            image = image_name

        post = Post(
            title=form.title.data,
            text=form.text.data,
            user=current_user,
            image=image
        )
        db.session.add(post)
        db.session.commit()
        flash("Нову статтю успішно створено")
        return redirect(url_for("index"))

    return render_template("add_post.html", form=form)


@app.route("/sign-up-form", methods=["GET", "POST"])
def sign_up_form():
    form = SignUp()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,  
            first_name=form.first_name.data or None,
            last_name=form.last_name.data or None,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("sign_n_form"))
    return render_template("sign_up_form.html", form=form)


@app.route("/sign-in-form/", methods=["GET", "POST"])
def sign_in_form():
    form = SignIn()
    if form.validate_on_submit():
        user: User = User.query.filter_by(username=form.username.data).first()
        if user and user.is_verify_password(form.password.data):
            login_user(user)
            return redirect(url_for("index"))
        flash("Логін або пароль не вірні")
    return render_template("sign_in_form.html", form=form)
    

@app.route("/add-post-form/", methods=["GET", "POST"])
def add_post_form():
    form= Postform()
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            text=form.text.data,
            image=None
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("add_post_form.html", form=form)


@app.get("/")
def index():
    posts = Post.query.all()
    return render_template("index.html", posts=posts)


if __name__ == "__main__":
    app.run(debug=True)