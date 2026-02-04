"""
Readlog - CS50x 2026's Final Project

Author: Brenda S. M.

app.py
"""

from flask import Flask, render_template, request, redirect, url_for, g, make_response
from io import StringIO
import csv
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
    db.commit()

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
        row["genre"] for row in db.execute("SELECT DISTINCT genre FROM library WHERE genre IS NOT NULL ORDER BY genre").fetchall()
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

@app.route("/edit/<isbn>", methods=["GET", "POST"])
def edit_book(isbn):
    db = get_database()
    book = db.execute("SELECT * FROM library where isbn = ?", (isbn,)).fetchone()

    if book is None:
        return "Book not found", 404
    
    if request.method == "POST":
        new_isbn    = request.form.get("isbn", "").strip()
        new_title       = request.form.get("title", "").strip()
        new_author      = request.form.get("author", "").strip()
        new_publisher   = request.form.get("publisher", "").strip() or None
        new_year        = request.form.get("year", "").strip()
        new_genre       = request.form.get("genre", "").strip() or None
        new_language    = request.form.get("language", "").strip() or None
        new_pages       = request.form.get("pages", "").strip()
        new_date_read   = request.form.get("date_read", "").strip() or None
        new_rating      = request.form.get("rating", "").strip()
        new_review      = request.form.get("review", "").strip()

        error = None

        if not new_isbn:
            error = "ISBN is required."
        elif not new_title:
            error = "Title is required."
        elif not new_author:
            error = "Author is required."
        
        if error:
            return render_template("edit.html", book=book, error=error)

        if new_isbn != isbn:
            isbn_exists = db.execute("SELECT isbn FROM library WHERE isbn = ?", (new_isbn,)).fetchone()

            if isbn_exists:
                return render_template("edit.html", book=book, error="A book with this ISBN already exists.")
        
            db.execute("DELETE FROM library WHERE isbn = ?", (isbn,))
            db.execute(
                """INSERT INTO library
                   (isbn, title, author, publisher, year, genre, language, pages, date_read, rating, review)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    new_isbn, new_title, new_author, new_publisher,
                    int(new_year) if new_year else None,
                    new_genre, new_language,
                    int(new_pages) if new_pages else None,
                    new_date_read,
                    int(new_rating) if new_rating else None,
                    new_review,
                ),
            )
        else:
            db.execute(
                """UPDATE library SET
                   title = ?, author = ?, publisher = ?, year = ?, genre = ?,
                   language = ?, pages = ?, date_read = ?, rating = ?, review = ?
                   WHERE isbn = ?""",
                (
                    new_title, new_author, new_publisher,
                    int(new_year) if new_year else None,
                    new_genre, new_language,
                    int(new_pages) if new_pages else None,
                    new_date_read,
                    int(new_rating) if new_rating else None,
                    new_review,
                    isbn,
                ),
            )
        
        db.commit()
        return redirect(url_for("book_detail", isbn=new_isbn))
        
    return render_template("edit.html", book=book, error=None)

@app.route("/export")
def export_csv():
    db = get_database()
    books = db.execute("SELECT * FROM library ORDER BY date_read DESC NULLS LAST").fetchall()
    
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['ISBN', 'Title', 'Author', 'Publisher', 'Year', 'Genre', 
                     'Language', 'Pages', 'Date Read', 'Rating', 'Review'])
    
    for book in books:
        review = book['review'] or ''
        review = review.replace('\n', ' ').replace('\r', ' ').strip()

        writer.writerow([
            book['isbn'],
            book['title'],
            book['author'],
            book['publisher'] or '',
            book['year'] or '',
            book['genre'] or '',
            book['language'] or '',
            book['pages'] or '',
            book['date_read'] or '',
            book['rating'] or '',
            review
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=readlog_library.csv'
    
    return response

# Bootstrap logic

os. makedirs(app.instance_path, exist_ok=True)

with app.app_context():
    init_database()

if __name__ == "__main__":
    app.run(debug=True)
