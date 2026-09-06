from flask import Flask,render_template,request,session
import mysql.connector,pandas as pd,numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score

app=Flask(__name__)
app.secret_key = "stock_prediction_secret_key"

def db():
    return mysql.connector.connect(
        host="localhost",user="root",
        password="prathuu",database="stock_prediction")

def stocks():
    con=db(); cur=con.cursor()
    cur.execute("SELECT Stock_ID,Stock_Name,Symbol FROM stock")
    x=cur.fetchall(); cur.close(); con.close()
    return x

@app.route("/")
def home():
    return render_template("index.html",stocks=stocks())

@app.route("/predict",methods=["POST"])
def predict():

    # Check login
    if "user_id" not in session:
        return render_template(
            "login.html",
            error="Please login before making a prediction!"
        )

    user_id=session["user_id"]

    sym=request.form["symbol"].upper()
    con=db(); cur=con.cursor()

    cur.execute(
        "SELECT Stock_ID,Stock_Name FROM stock WHERE Symbol=%s",(sym,))
    s=cur.fetchone()

    if not s:
        cur.close(); con.close()
        return render_template("index.html",
                               stocks=stocks(),error="Stock not found!")

    q="""SELECT Date,Open_Price,High_Price,Low_Price,
    Close_Price,Volume FROM stock_history
    WHERE Stock_ID=%s ORDER BY Date"""

    d=pd.read_sql(q,con,params=(s[0],)).dropna().drop_duplicates()
    d["Date"]=pd.to_datetime(d.Date)

    if len(d)<20:
        cur.close(); con.close()
        return render_template("index.html",
                               stocks=stocks(),
                               error="Not enough data!")

    X=d[["Open_Price","High_Price","Low_Price","Volume"]]
    y=d.Close_Price

    Xtr,Xte,ytr,yte=train_test_split(
        X,y,test_size=.2,random_state=42)

    model=LinearRegression().fit(Xtr,ytr)
    pred=model.predict(Xte)

    mse=mean_squared_error(yte,pred)

    # Graph 1
    plt.figure(figsize=(9,4))
    plt.plot(d.Date,d.Close_Price)
    plt.title(s[1]+" Closing Price")
    plt.tight_layout()
    plt.savefig("static/closing.png")
    plt.close()

    # Graph 2
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
        last.Open_Price,
        last.High_Price,
        last.Low_Price,
        last.Volume
    ]])[0]

    # Save prediction with logged-in User_ID
    cur.execute("""INSERT INTO prediction
    (Stock_ID,Prediction_Price,Prediction_Date,User_ID)
    VALUES(%s,%s,CURDATE(),%s)""",
    (s[0],float(price),user_id))

    con.commit()

    metrics={
        "mae":round(mean_absolute_error(yte,pred),2),
        "mse":round(mse,2),
        "rmse":round(np.sqrt(mse),2),
        "r2":round(r2_score(yte,pred),2)
    }

    result={
        "name":s[1],
        "symbol":sym,
        "records":len(d),
        "price":round(price,2)
    }

    cur.close()
    con.close()

    return render_template(
        "index.html",
        stocks=stocks(),
        result=result,
        metrics=metrics
    )

if __name__=="__main__":
    app.run(debug=True)