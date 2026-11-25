
from flask import Flask,render_template,request,session,redirect
import mysql.connector,pandas as pd,numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score

app=Flask(__name__)
app.secret_key="stock_prediction_secret_key"

# ================= DATABASE CONNECTION =================

def db():
    return mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="prathuu",
        database="stock_prediction"
    )

def stocks():
    con=db()
    cur=con.cursor()
    cur.execute("SELECT Stock_ID,Stock_Name,Symbol FROM stock")
    x=cur.fetchall()
    cur.close()
    con.close()
    return x


# ================= HOME =================

@app.route("/")
def home():
    return render_template("index.html",stocks=stocks())


# ================= PREDICTION =================

@app.route("/predict",methods=["POST"])
def predict():

    if "user_id" not in session:
        return render_template("login.html",
                               error="Please login before making a prediction!")

    sym=request.form["symbol"].upper()
    con=db()
    cur=con.cursor()

    cur.execute("SELECT Stock_ID,Stock_Name FROM stock WHERE Symbol=%s",(sym,))
    s=cur.fetchone()

    if not s:
        cur.close()
        con.close()
        return render_template("index.html",
                               stocks=stocks(),error="Stock not found!")

    q="""SELECT Date,Open_Price,High_Price,Low_Price,
    Close_Price,Volume FROM stock_history
    WHERE Stock_ID=%s ORDER BY Date"""

    d=pd.read_sql(q,con,params=(s[0],)).dropna().drop_duplicates()
    d["Date"]=pd.to_datetime(d.Date)

    if len(d)<20:
        cur.close()
        con.close()
        return render_template("index.html",
                               stocks=stocks(),error="Not enough data!")

    X=d[["Open_Price","High_Price","Low_Price","Volume"]]
    y=d.Close_Price

    Xtr,Xte,ytr,yte=train_test_split(
        X,y,test_size=.2,random_state=42)

    model=LinearRegression().fit(Xtr,ytr)
    pred=model.predict(Xte)
    mse=mean_squared_error(yte,pred)

    plt.figure(figsize=(9,4))
    plt.plot(d.Date,d.Close_Price)
    plt.title(s[1]+" Closing Price")
    plt.tight_layout()
    plt.savefig("static/closing.png")
    plt.close()

    plt.figure(figsize=(9,4))
    plt.plot(yte.values,label="Actual")
    plt.plot(pred,label="Predicted")
    plt.title("Actual vs Predicted")
    plt.legend()
    plt.tight_layout()
    plt.savefig("static/predicted.png")
    plt.close()

    last=d.iloc[-1]
    price=model.predict([[
        last.Open_Price,last.High_Price,
        last.Low_Price,last.Volume]])[0]

    cur.execute("""INSERT INTO prediction
    (Stock_ID,Prediction_Price,Prediction_Date,User_ID)
    VALUES(%s,%s,CURDATE(),%s)""",
    (s[0],float(price),session["user_id"]))

    con.commit()

    metrics={
        "mae":round(mean_absolute_error(yte,pred),2),
        "mse":round(mse,2),
        "rmse":round(np.sqrt(mse),2),
        "r2":round(r2_score(yte,pred),2)}

    result={
        "name":s[1],"symbol":sym,
        "records":len(d),"price":round(price,2)}

    cur.close()
    con.close()

    return render_template("index.html",
                           stocks=stocks(),
                           result=result,metrics=metrics)


# ================= ADMIN LOGIN =================

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():

    if request.method=="POST":
        con=db()
        cur=con.cursor()
        cur.execute(
            "SELECT Admin_ID,Username FROM admin WHERE Username=%s AND Password=%s",
            (request.form["username"],request.form["password"]))
        a=cur.fetchone()
        cur.close()
        con.close()

        if a:
            session["admin_id"]=a[0]
            session["admin_username"]=a[1]
            return redirect("/admin/dashboard")

        return render_template("admin_login.html",
                               error="Invalid username or password!")

    return render_template("admin_login.html")


# ================= ADMIN DASHBOARD =================

@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect("/admin/login")

    con=db()
    cur=con.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users=cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM stock")
    stock_count=cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM prediction")
    predictions=cur.fetchone()[0]

    cur.close()
    con.close()

    return render_template("admin_dashboard.html",
                           users=users,
                           stocks=stock_count,
                           predictions=predictions)


# ================= STOCKS =================

@app.route("/admin/stocks")
def admin_stocks():

    if "admin_id" not in session:
        return redirect("/admin/login")

    con=db()
    cur=con.cursor()

    cur.execute("""
    SELECT s.Stock_ID,s.Stock_Name,s.Company_Name,s.Symbol,
    COUNT(h.Stock_ID)
    FROM stock s
    LEFT JOIN stock_history h ON s.Stock_ID=h.Stock_ID
    GROUP BY s.Stock_ID,s.Stock_Name,s.Company_Name,s.Symbol
    """)

    data=cur.fetchall()
    cur.close()
    con.close()

    return render_template("admin_stocks.html",stocks=data)


# ================= ADD STOCK =================

@app.route("/admin/stocks/add",methods=["POST"])
def admin_add_stock():

    if "admin_id" not in session:
        return redirect("/admin/login")

    con=db()
    cur=con.cursor()

    cur.execute("""
    INSERT INTO stock(Stock_Name,Company_Name,Symbol)
    VALUES(%s,%s,%s)
    """,(
        request.form["name"],
        request.form["company"],
        request.form["symbol"].upper()))

    con.commit()
    cur.close()
    con.close()

    return redirect("/admin/stocks")


# ================= DELETE STOCK =================

@app.route("/admin/stocks/delete/<int:id>")
def admin_delete_stock(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    con=db()
    cur=con.cursor()

    cur.execute("DELETE FROM prediction WHERE Stock_ID=%s",(id,))
    cur.execute("DELETE FROM stock_history WHERE Stock_ID=%s",(id,))
    cur.execute("DELETE FROM stock WHERE Stock_ID=%s",(id,))

    con.commit()
    cur.close()
    con.close()

    return redirect("/admin/stocks")


# ================= USERS =================

@app.route("/admin/users")
def admin_users():

    if "admin_id" not in session:
        return redirect("/admin/login")

    con=db()
    cur=con.cursor()

    cur.execute("SELECT User_ID,Full_Name,Email FROM users")
    data=cur.fetchall()

    cur.close()
    con.close()

    return render_template("admin_users.html",users=data)


# ================= PREDICTIONS =================

@app.route("/admin/predictions")
def admin_predictions():

    if "admin_id" not in session:
        return redirect("/admin/login")

    con=db()
    cur=con.cursor()

    cur.execute("""
    SELECT u.Full_Name,s.Stock_Name,
    p.Prediction_Price,p.Prediction_Date
    FROM prediction p
    JOIN users u ON p.User_ID=u.User_ID
    JOIN stock s ON p.Stock_ID=s.Stock_ID
    ORDER BY p.Prediction_Date DESC
    """)

    data=cur.fetchall()

    cur.close()
    con.close()

    return render_template("admin_predictions.html",
                           predictions=data)


# ================= LOGOUT =================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_id",None)
    session.pop("admin_username",None)

    return redirect("/admin/login")


import auth

if __name__=="__main__":
    app.run(debug=True)
