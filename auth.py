from flask import render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from main import app, db, stocks


def login_required():
    return "user_id" in session


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        con = db()
        cur = con.cursor()
        cur.execute("SELECT User_ID FROM users WHERE Email=%s", (email,))

        if cur.fetchone():
            cur.close()
            con.close()
            return render_template("register.html",
                                   error="Email already registered!")

        cur.execute("""
            INSERT INTO users (Full_Name, Email, Password)
            VALUES (%s,%s,%s)
        """, (name, email, password))

        con.commit()
        cur.close()
        con.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        con = db()
        cur = con.cursor()
        cur.execute("""
            SELECT User_ID, Full_Name, Email, Password
            FROM users WHERE Email=%s
        """, (email,))
        user = cur.fetchone()
        cur.close()
        con.close()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["user_email"] = user[2]
            return redirect("/dashboard")

        return render_template("login.html",
                               error="Invalid email or password!")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")

    uid = session["user_id"]
    con = db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM prediction WHERE User_ID=%s", (uid,))
    total_predictions = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM stock")
    total_stocks = cur.fetchone()[0]

    cur.execute("""
        SELECT AVG(Prediction_Price)
        FROM prediction WHERE User_ID=%s
    """, (uid,))
    average_price = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT s.Stock_Name,s.Symbol,p.Prediction_Price,p.Prediction_Date
        FROM prediction p
        JOIN stock s ON p.Stock_ID=s.Stock_ID
        WHERE p.User_ID=%s
        ORDER BY p.Prediction_ID DESC LIMIT 1
    """, (uid,))
    latest = cur.fetchone()

    cur.close()
    con.close()

    return render_template(
        "dashboard.html",
        total_predictions=total_predictions,
        total_stocks=total_stocks,
        average_price=round(average_price, 2),
        latest=latest
    )


@app.route("/history")
def history():
    if not login_required():
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT p.Prediction_ID,s.Stock_Name,s.Symbol,
               p.Prediction_Price,p.Prediction_Date
        FROM prediction p
        LEFT JOIN stock s ON p.Stock_ID=s.Stock_ID
        WHERE p.User_ID=%s
        ORDER BY p.Prediction_ID ASC
    """, (session["user_id"],))

    data = cur.fetchall()
    cur.close()
    con.close()

    return render_template("history.html", history=data)


@app.route("/analytics")
def analytics():
    if not login_required():
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT s.Symbol,p.Prediction_Price,p.Prediction_Date
        FROM prediction p
        JOIN stock s ON p.Stock_ID=s.Stock_ID
        WHERE p.User_ID=%s
        ORDER BY p.Prediction_Date,p.Prediction_ID
    """, (session["user_id"],))

    data = cur.fetchall()
    cur.close()
    con.close()

    labels = [f"{x[0]} - {x[2]}" for x in data]
    prices = [float(x[1]) for x in data]

    return render_template("analytics.html",
                           labels=labels, prices=prices)


@app.route("/stock-data")
def stock_data():
    if not login_required():
        return redirect("/login")
    return render_template("stock_data.html", stocks=stocks())


@app.route("/visualization")
def visualization():
    if not login_required():
        return redirect("/login")
    return render_template("visualization.html")


@app.route("/reports")
def reports():
    if not login_required():
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT p.Prediction_ID,s.Stock_Name,s.Symbol,
               p.Prediction_Price,p.Prediction_Date
        FROM prediction p
        JOIN stock s ON p.Stock_ID=s.Stock_ID
        WHERE p.User_ID=%s
        ORDER BY p.Prediction_ID DESC
    """, (session["user_id"],))

    data = cur.fetchall()
    cur.close()
    con.close()

    return render_template("reports.html", reports=data)


@app.route("/about")
def about():
    if not login_required():
        return redirect("/login")
    return render_template("about.html")


@app.route("/prediction")
def prediction():
    if not login_required():
        return redirect("/login")
    return render_template("prediction.html", stocks=stocks())


if __name__ == "__main__":
    app.run(debug=True)