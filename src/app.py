"""
My Books App - CS50 Final Project

Author: Brenda S. M.

app.py
"""

from flask import Flask, render_template, request, redirect, url_for, g
import os
import sqlite3

app = Flask(__name__)
DATABASE = os.path.join(app.instance_path, "library.db")

# Database Funcitions

def get_database():
    if "db" not in g: # simple namespace object that has the same lifetime as an application context.
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def init_database():
    db = get_database()
    db.executescript("""CREATE TABLE IF NOT EXISTS books (
            isbn        TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            author      TEXT NOT NULL,
            publisher   TEXT,
            year        INTEGER,
            genre       TEXT,
            language    TEXT,
            pages       INTEGER,
            date_read   TEXT,
            rating      INTEGER CHECK (rating BETWEEN 1 AND 5),
            review      TEXT
        ); """)

@app.cli.command("init-database")
def init_database_command():
    init_database()

@app.teardown_appcontext
def close_database(exception):
    db = g.pop("db", None) # closes the conexion at the end of requisition
    if db is not None:
        db.close()


# APP Endpoints

@app.route("/")
def index():
    db = get_database()

    # filter params, which are optional
    title = request.args.get("title", "").strip()
    author = request.args.get("author", "").strip()
    genre = request.args.get("genre", "").strip()
    year = request.args.get("year", "").strip()
    rating = request.args.get("rating", "").strip()

    query = "SELECT * FROM library WHERE 1=1"
    parameters = []

    if title:
        query += "AND title LIKE ?" # we can add personalized filters
        parameters.append(f"%{title}%")
    if author:
        query += "AND author LIKE ?" 
        parameters.append(f"%{author}%")
    if genre:
        query += "AND genre LIKE ?" 
        parameters.append(f"%{genre}%")
    if year:
        query += "AND year LIKE ?" 
        parameters.append(f"%{year}%")
    if rating:
        query += "AND rating LIKE ?" 
        parameters.append(f"%{rating}%")
    
    query += "ORDER BY data_read DESC NULLS LAST"
    books = db.execute(query, parameters).fetchall()

    return render_template(
        "index.html", #TODO create a better page
        books = books,
        filters = dict(title=title, author=author, genre=genre, year=year, rating=rating)
    )