#===========================================================
# YOUR PROJECT TITLE HERE
# YOUR NAME HERE
#-----------------------------------------------------------
# BRIEF DESCRIPTION OF YOUR PROJECT HERE
#===========================================================


from flask import Flask, render_template, request, flash, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import html

from app.helpers.session import init_session
from app.helpers.db      import connect_db
from app.helpers.errors  import init_error, not_found_error
from app.helpers.logging import init_logging
from app.helpers.auth    import login_required
from app.helpers.time    import init_datetime, utc_timestamp, utc_timestamp_now


# Create the app
app = Flask(__name__)

# Configure app
init_session(app)   # Setup a session for messages, etc.
init_logging(app)   # Log requests
init_error(app)     # Handle errors and exceptions
init_datetime(app)  # Handle UTC dates in timestamps


#-----------------------------------------------------------
# Home page route
#-----------------------------------------------------------
@app.get("/")
def index():
    if session.get("logged_in"):
        with connect_db() as client:
            # Get the 10 most recently added games from the DB
            sql = """
                SELECT games.id,
                       games.name,
                       games.added_by,
                       games.header_img

                FROM games

                ORDER BY games.id DESC
                LIMIT 10
                """
            params=[]
            result = client.execute(sql, params)
            games = result.rows

            # And show them on the page
            return render_template("pages/game-list.jinja", games=games)
    else:
        return render_template("pages/home.jinja")


#-----------------------------------------------------------
# About page route
#-----------------------------------------------------------
@app.get("/about/")
def about():
    return render_template("pages/about.jinja")


#-----------------------------------------------------------
# Things page route - Show all the things, and new thing form
#-----------------------------------------------------------
@app.get("/things/")
def show_all_things():
    with connect_db() as client:
        # Get all the things from the DB
        sql = """
            SELECT things.id,
                   things.name,
                   users.name AS owner

            FROM things
            JOIN users ON things.username = users.username

            ORDER BY things.name ASC
        """
        params=[]
        result = client.execute(sql, params)
        things = result.rows

        # And show them on the page
        return render_template("pages/things.jinja", things=things)


#-----------------------------------------------------------
# Things page route - Show all the things, and new thing form
#-----------------------------------------------------------
@app.post("/search-games/")
def search_things():
    with connect_db() as client:
        # Get the search term from the form
        search = request.form.get("search")
        
        # Get all the things from the DB
        sql = """
            SELECT  id,
                    name,
                    added_by,
                    header_img

            FROM games
            WHERE games.name LIKE '%' || ? || '%'
            LIMIT 20
            """
        params=[search]
        result = client.execute(sql, params)
        games = result.rows

        # And show them on the page
        return render_template("pages/search-list.jinja", games=games, search=search)

#-----------------------------------------------------------
# Thing page route - Show details of a single thing
#-----------------------------------------------------------
@app.get("/game/<int:id>")
def show_game(id):
    with connect_db() as client:
        # Get the thing details from the DB, including the owner info
        sql = """
            SELECT id,
                   name,
                   added_by,
                   header_img

            FROM games
            WHERE id=?
        """
        params = [id]
        result = client.execute(sql, params)
        game = result.rows[0]

        sql = """
            SELECT achievements.id,
                   achievements.name,
                   achievements.game_id,
                   achievements.added_by,
                   achievements.icon_img,
                   earned.username,
                   earned.date

            FROM achievements
            LEFT JOIN earned ON achievements.id = earned.a_id

            WHERE achievements.game_id=? AND (earned.username=? or earned.username IS NULL)
        """
        params = [id, session["user_username"]]
        result = client.execute(sql, params)
        achievements = result.rows
        return render_template("pages/game.jinja", game=game, achievements=achievements)


#-----------------------------------------------------------
# Add achievement form route
#-----------------------------------------------------------
@app.get("/form/achievement/<int:game>")
def achievement_form(game):
    return render_template("pages/form-achievement.jinja", game=game)

#-----------------------------------------------------------
# Add game form route
#-----------------------------------------------------------
@app.get("/form/game/")
def game_form():
    return render_template("pages/form-game.jinja")

#-----------------------------------------------------------
# Route for adding a thing, using data posted from a form
# - Restricted to logged in users
#-----------------------------------------------------------
@app.post("/add/achievement/<int:id>")
@login_required
def add_an_acheivement(id):
    # Get the data from the form
    name  = request.form.get("name")
    desc  = request.form.get("description")
    image = request.form.get("image")

    # Sanitise the text inputs
    name  = html.escape(name)  if name else None
    desc  = html.escape(desc)  if desc else None
    image = html.escape(image) if image else None

    # Get the username from the session
    username = session["user_username"]

    with connect_db() as client:
        # Add the thing to the DB
        sql = "INSERT INTO achievements (name, description, icon_img, game_id, added_by) VALUES (?, ?, ?, ?, ?)"
        params = [name, desc, image, id, username]
        client.execute(sql, params)

        # Go back to the home page
        flash(f"Acheivement '{name}' added", "success")
        return redirect("/game/" + str(id))
    
#-----------------------------------------------------------
# Route for adding a thing, using data posted from a form
# - Restricted to logged in users
#-----------------------------------------------------------
@app.post("/add/game/")
@login_required
def add_a_game():
    # Get the data from the form
    name  = request.form.get("name")
    image = request.form.get("image")

    # Sanitise the text inputs
    name  = html.escape(name)
    image = html.escape(image)

    # Get the username from the session
    username = session["user_username"]

    with connect_db() as client:
        # Add the thing to the DB
        sql = "INSERT INTO games (name, added_by, header_img) VALUES (?, ?, ?)"
        params = [name, username, image]
        client.execute(sql, params)

        # Get the id of the game we just added
        sql = "SELECT Max(id) FROM games"
        params = []
        id = client.execute(sql, params).rows[0][0]

        # Go back to the home page
        flash(f"Game '{name}' added", "success")
        return redirect("/game/" + str(id))

#-----------------------------------------------------------
# Route for completing an achievement
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/complete/<int:game>/<int:id>")
@login_required
def complete(game, id):
    # Get the username from the session
    username = session["user_username"]

    with connect_db() as client:
        # Add the achievement to the earned table
        sql = "INSERT INTO earned (a_id, username) VALUES (?, ?)"
        params = [id, username]
        client.execute(sql, params)

        # Go back to the home page
        flash(f"Achievement Completed", "success")
        return redirect("/game/" + str(game))

#-----------------------------------------------------------
# Route for uncompleting an achievement
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/uncomplete/<int:game>/<int:id>")
@login_required
def uncomplete(game, id):
    # Get the username from the session
    username = session["user_username"]

    with connect_db() as client:
        # Remove the achievement from the earned table
        sql = "DELETE FROM earned WHERE a_id=? AND username=?"
        params = [id, username]
        client.execute(sql, params)

        # Go back to the home page
        flash(f"Achievement not Completed", "success")
        return redirect("/game/" + str(game))

#-----------------------------------------------------------
# Route for deleting a game, Id given in the route
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/delete/game/<int:id>")
@login_required
def delete_a_game(id):
    # Get the user id from the session
    username = session["user_username"]

    with connect_db() as client:
        # Delete the thing from the DB only if we own it
        sql = "DELETE FROM games WHERE id=? AND added_by=?"
        params = [id, username]
        client.execute(sql, params)

        # Go back to the home page
        flash("Game deleted", "success")
        return redirect("/")
    
#-----------------------------------------------------------
# Route for deleting an achievement, Id given in the route
# - Restricted to logged in users
#-----------------------------------------------------------    
@app.get("/delete/achievement/<int:game>/<int:id>")
@login_required
def delete_an_achievment(game, id):
    # Get the user id from the session
    username = session["user_username"]

    with connect_db() as client:
        # Delete the thing from the DB only if we own it
        sql = "DELETE FROM achievements WHERE id=? AND added_by=?"
        params = [id, username]
        client.execute(sql, params)

        # Go back to the home page
        flash("Achievement deleted", "success")
        return redirect("/game/" + str(game))

#-----------------------------------------------------------
# User registration form route
#-----------------------------------------------------------
@app.get("/register")
def register_form():
    return render_template("pages/register.jinja")


#-----------------------------------------------------------
# User login form route
#-----------------------------------------------------------
@app.get("/login")
def login_form():
    return render_template("pages/login.jinja")


#-----------------------------------------------------------
# Route for adding a user when registration form submitted
#-----------------------------------------------------------
@app.post("/add-user")
def add_user():
    # Get the data from the form
    name = request.form.get("name")
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find an existing record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        params = [username]
        result = client.execute(sql, params)

        # No existing record found, so safe to add the user
        if not result.rows:
            # Sanitise the name
            name = html.escape(name)

            # Salt and hash the password
            hash = generate_password_hash(password)

            # Add the user to the users table
            sql = "INSERT INTO users (name, username, password_hash) VALUES (?, ?, ?)"
            params = [name, username, hash]
            client.execute(sql, params)

            # And let them know it was successful and they can login
            flash("Registration successful", "success")
            return redirect("/login")

        # Found an existing record, so prompt to try again
        flash("Username already exists. Try again...", "error")
        return redirect("/register")


#-----------------------------------------------------------
# Route for processing a user login
#-----------------------------------------------------------
@app.post("/login-user")
def login_user():
    # Get the login form data
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find a record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        params = [username]
        result = client.execute(sql, params)

        # Did we find a record?
        if result.rows:
            # Yes, so check password
            user = result.rows[0]
            hash = user["password_hash"]

            # Hash matches?
            if check_password_hash(hash, password):
                # Yes, so save info in the session
                session["user_name"] = user["name"]
                session["user_username"] = user["username"]
                session["logged_in"] = True

                # And head back to the home page
                flash("Login successful", "success")
                return redirect("/")

        # Either username not found, or password was wrong
        flash("Invalid credentials", "error")
        return redirect("/login")


#-----------------------------------------------------------
# Route for processing a user logout
#-----------------------------------------------------------
@app.get("/logout")
def logout():
    # Clear the details from the session
    session.pop("user_name", None)
    session.pop("logged_in", None)

    # And head back to the home page
    flash("Logged out successfully", "success")
    return redirect("/")

