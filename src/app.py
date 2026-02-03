"""
Readlog - CS50x 2026's Final Project

Author: Brenda S. M.

app.py
"""

from flask import Flask, render_template, request, redirect, url_for, g
import os
import sqlite3

app = Flask(__name__)
DATABASE = os.path.join(app.instance_path, "library.db")

# Database Functions

def get_database():
    if "db" not in g: # simple namespace object that has the same lifetime as an application context.
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def init_database():
    db = get_database()
    db.executescript("""CREATE TABLE IF NOT EXISTS library (
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
        query += " AND title LIKE ?" # we can add personalized filters
        parameters.append(f"%{title}%")
    if author:
        query += " AND author LIKE ?" 
        parameters.append(f"%{author}%")
    if genre:
        query += " AND genre LIKE ?" 
        parameters.append(f"%{genre}%")
    if year:
        query += " AND year LIKE ?" 
        parameters.append(f"%{year}%")
    if rating:
        query += " AND rating LIKE ?" 
        parameters.append(f"%{rating}%")
    
    query += " ORDER BY date_read DESC NULLS LAST"
    books = db.execute(query, parameters).fetchall()
    genres = [
        row["genre"] for row in db.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre").fetchall()
    ]

    return render_template(
        "index.html", 
        books = books,
        filters = dict(title=title, author=author, genre=genre, year=year, rating=rating),
        genres = genres
    )

@app.route("/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip()
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        publisher = request.form.get("publisher", "").strip() or None
        year = request.form.get("year", "").strip()
        genre = request.form.get("genre", "").strip() or None
        language = request.form.get("language", "").strip() or None
        pages = request.form.get("pages", "").strip()
        date_read = request.form.get("date_read", "").strip() or None
        rating = request.form.get("rating", "").strip()
        review = request.form.get("review", "").strip() or None

        error = None

        # non optional parameters

        if not isbn:
            error = "ISBN is required."
        elif not title:
            error = "Title is required."
        elif not author:
            error = "Author is required."
        
        if error: 
            return render_template("add.html", error=error) # TODO make a error page

        db = get_database()
        isbn_exists = db.execute("SELECT isbn FROM library WHERE isbn = ?", (isbn,)).fetchone()
        title_exists = db.execute("SELECT isbn FROM library WHERE title = ?", (title,)).fetchone()

        if isbn_exists:
            return render_template("add.html", error="A book with this ISBN already exists.")
        if title_exists:
            return render_template("add.html", error="A book with this title already exists.")

        # if no errors, add this new book to the database

        db.execute("""INSERT INTO library (
                   isbn, title, author, publisher, year, genre, language, pages, date_read, rating, review
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        isbn, title, author, publisher,
                        int(year) if year else None,
                        genre, language,
                        int(pages) if pages else None,
                        date_read,
                        int(rating) if rating else None,
                        review,
                        ),
                    )
        db.commit()

        return redirect(url_for("index"))

    return render_template("add.html", error=None)

@app.route("/book/<isbn>")
def book_detail(isbn):
    db = get_database()
    book = db.execute("SELECT * FROM library WHERE isbn = ?", (isbn,)).fetchone()
    
    if book is None:
        return "Book not found", 404
    
    return render_template("detail.html", book=book)

@app.route("/delete/<isbn>", methods=["POST"])
def delete_book(isbn):
    db = get_database()
    db.execute("DELETE FROM library WHERE isbn = ?", (isbn,))
    db.commit()

    return redirect(url_for("index"))

# Bootstrap logic

os. makedirs(app.instance_path, exist_ok=True)

with app.app_context():
    init_database()

if __name__ == "__main__":
    app.run(debug=True)
