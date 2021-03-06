import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    # Jared's Implementation:
    # Technically the solution, but put Jared's for easy control-f searching.
    # For whatever reason, this line(s) was added for the purpose of checking if a user was already logged in, while trying to create a new account? An odd edge case to cover, but I suppose a good idea. My question is, why was it in the solution, not in the original source code, and why wasn't I prompted to add it, if it was necessary?
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS
    # Jared's implementation (1):
    # Step Two: Fix Logout

    do_logout()
    # do_logout() was already established on line 49, so theoretically all I need to do is call it.
    # I did not require any authentication; theoretically, only a logged in user would be presented with this option. Edge cases are obviously not covered, but at the moment, I'd be happy if this worked at all.

    flash("Successfully Logged Out", 'success')
    # I did decided to include the 'success' argument, though I admit I'm forgetting what exactly that does. I'm assuming that it's a style, possibly through bootstrap? Sucess and danger are styles through that library, but I'm not sure how it would make the connection.

    return redirect("/login")
    # Relying on the code above being correct, I redirected to the login page.


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)
    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/<int:user_id>/likes', methods=["GET"])
def show_likes(user_id):
    # Jared's Implementation:
    # Part Two: Show likes.
    # I had some of this planned out, but honestly thought I would need the logic and queries from 'following_messages' at '/' to implement this. Turns out, this was as simple as I was hoping '/' would be. The logic already existed, I just had to call it.
    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user, likes=user.likes)


@app.route('/messages/<int:message_id>/like', methods=['POST'])
def add_like(message_id):
    """ Toggle a liked message for the currently-logged-in user."""

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    liked_message = Message.query.get_or_404(message_id)
    if liked_message.user_id == g.user.id:
        return abort(403)

    user_likes = g.user.likes

    if liked_message in user_likes:
        g.user.likes = [like for like in user_likes if like != liked_message]
    else:
        g.user.likes.append(liked_message)

    db.session.commit()

    return redirect("/")


@app.route('/users/profile', methods=["GET", "POST"])
def edit_profile():
    """Update profile for current user."""

    # IMPLEMENT THIS
    # Jared's Imp.
    # Step Five: Profile Edit:
    # I admit, on this particular problem, I did reference the solution. I was at a loss as to what direction I should even be going in, and looked over the solution's 'def profile():' just to get an idea of what needed to happen.
    # This is not a copy and paste, but an edit of broken code I had attempted with the blanks filled in here and there.

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    user = g.user
    # I don't know why obj=user needs to be passed into this. And, oddly enough, it seems to work without it. Food for thought, I suppose.
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        # My though process on this block of code:
        # After checking the solution just for the syntax of these lines, it made sense and I was able to fill in the rest by following the pattern.
        # If the user, who is authenticated by the authenticate function, which is checking the already established username and the password being entered in this particular form, returns 'true',
        # Change the user's name, email, etc. from their old values to whatever is in the form now, which is
        # form
        # (blank)
        # .data, to pull the actual data from the form inputs
        if User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or "/static/images/default-pic.png"
            user.header_image_url = form.header_image_url.data or "/static/images/warbler-hero.jpg"
            user.bio = form.bio.data

            db.session.commit()
            return redirect(f"/users/{user.id}")

        # If authenticate doesn't work...
        flash("Password incorrect. Please try again.", 'danger')

    return render_template('users/edit.html', form=form, user_id=user.id)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


# Jared's Implementation
# Odd; this doesn't appear in the solution, at least in this portion of code. Will see if it's implemented somewhere else, or just not needed.
# Edit: Yes, they did use it; just in another spot. Line 237 for reference.
#
#
#
# @app.route('/users/add_like')
# def add_like():
#     """Shows page where liked messages are stored."""

#     if not g.user:
#         flash("Access Unauthorized.", "danger")
#         return redirect("/")


##############################################################################
# Messages routes:
@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access Unauthorized", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


# @app.route('/')
# def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    # Jared's Implementation
    # Step Six: Fix Homepage
    # The homepage for logged-in-users should show the last 100 warbles only from the users that the logged-in user is following, and that user, rather than warbles from all users.
    # I have altered my code further from my last email; (11-11-21 10:36 AM US time), and am now working through the many various 'following' classes, models, attributes, and so on. The base code uses that word a lot; one of them must be what I need. I'm just not sure which one.
    # if g.user:
    #     messages = (Message
    #                 .query
    #                 .filter(g.user.is_following(Message.user))
    #                 .order_by(Message.timestamp.desc())
    #                 .limit(100)
    #                 .all()
    #                 )
    #     return render_template('home.html', messages=messages)

    # else:
    #     return render_template('home-anon.html')

    #
    # This 'returns' a page with no 'warbles' present.

    # Sonia's Implementation:
    # if g.user:
    #     messages = (Message
    #                 .query
    #                 .order_by(Message.timestamp.desc())
    #                 .limit(100)
    #                 .all())
    #     liked_msgs = [msg.id for msg in g.user.likes]
    #     user_id = g.user.id

    #     return render_template('home.html', messages=messages, likes=liked_msgs)

    # else:
    #     return render_template('home-anon.html')
    #
    #
    #
    #
    #
    #
    # This 'returns' a page with all 'warbles' pressent.
    #
    #

# Sonia's Implementation: copy and pasted.
# 11-12-21 (11:16 AM) US Time


# @app.route('/')
# def homepage():
#     """Show homepage:

#     - anon users: no messages
#     - logged in: 100 most recent messages of followed_users
#     """

#     if g.user:
#         messages = (Message
#                     .query
#                     .order_by(Message.timestamp.desc())
#                     .limit(100)
#                     .all())
#         liked_msgs = [msg.id for msg in g.user.likes]
#         user_id = g.user.id

#         return render_template('home.html', messages=messages, likes=liked_msgs, user_id=user_id)

#     else:
#         return render_template('home-anon.html')

@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """
    # Solution's Implementation
    # Cries.
    # Close! I was so close! I tried implementing some kind of array, or dictionary, that contains the messages that meet my criteria! But I placed mine after the .query, and it wasn't done well. So I deleted it...
    if g.user:
        following_ids = [f.id for f in g.user.following] + [g.user.id]

        messages = (Message
                    .query
                    .filter(Message.user_id.in_(following_ids))
                    # I am seriously red-faced upset at how close I was! I had this line! Almost letter for letter, I had this! So close...........
                    # 'Credit' to Stackoverflow for the inspiration for one of my attempts.
                    # https://stackoverflow.com/questions/8603088/sqlalchemy-in-clause
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')
    # In conclusion, I had the .filter() idea. I had the extraction of following_ids idea. Didn't combine them, and trimmed down the failed ideas before submitting or saving any of it.


# Jared's Implementation:
# Interesting note; this block won't run.
# builtins.AttributeError
# AttributeError: 'Flask' object has no attribute 'error_handler'
# Even when importing 'abort' from flask, it wouldn't run. It tried to import error_handler, and threw a whole new error.
# My guess? Outdated code. But I don't know the new reference point, if one exists, so this is getting commented out.
# @app.error_handler(404)
# def page_not_found(e):
#     """404 Not found Page."""

#     return render_template('404.html', 404)


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@ app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
