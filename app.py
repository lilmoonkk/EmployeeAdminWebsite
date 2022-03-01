from datetime import timedelta
from flask import Flask, flash, render_template, request, redirect, url_for, g, session, jsonify
import sqlite3
from flask_restful import Resource, Api
import requests

#Declare flask
app = Flask(__name__)
app.secret_key = "Hello"
app.permanent_session_lifetime = timedelta(days=1)

#Declare url
url = "http://127.0.0.1:5000"

#Declare api
api = Api(app)

def databaseConn():
    db = g._database = sqlite3.connect("database.db")
    #db.execute('CREATE TABLE admin_auth (username varchar, password varchar)')
    #db.execute("INSERT INTO admin_auth (username, password) VALUES (?,?)",("Admin", "Admin"))
    #db.execute('CREATE TABLE employee_info (employeeId integer PRIMARY KEY autoincrement,employeeName varchar, gender varchar, email varchar, address varchar, academic varchar, username varchar UNIQUE, password varchar)')
    return db

#---------------------REST api------------------------
class loginAPI(Resource):
    def get(self):
        # Get json of params from request
        req = request.get_json()
        username = req['username']
        password = req['password']

        conn = databaseConn()
        auth = conn.execute('SELECT * FROM employee_info WHERE username = ? and password = ?',(username, password)).fetchone()
        conn.commit()
        conn.close()

        return jsonify(auth[0])
        

class profileAPI(Resource):
    def get(self, employeeId):
        conn = databaseConn()
        post = conn.execute('SELECT * FROM employee_info WHERE employeeId = ?',(str(employeeId))).fetchone()
        conn.commit()
        conn.close()

        # If no post with the employeeId found, return None
        if post == None:
            return jsonify(post)

        # else label the data and return the jsonified data
        return jsonify(employeeId=post[0], fullname=post[1], gender=post[2]
        , email=post[3], address=post[4], academic=post[5], username=post[6],
        password=post[7])

    def post(self, employeeId):
        req = request.get_json()
        fullname = req['fullname']
        gender = req['gender']
        email = req['email']
        address = req['address']
        academic = req['academic']
        username = req['username']
        password = req['password']

        try:
            conn = databaseConn()
            conn.execute("INSERT INTO employee_info (employeeName, gender, email, address, academic, username, password) VALUES (?,?,?,?,?,?,?)",
                (fullname, gender, email, address, academic, username, password))
            conn.commit()
            conn.close()
            return jsonify(True)
        
        # Raise exception to rollback the command if error occurs such as duplicate username
        except:
            conn.rollback()
            conn.close()
            return jsonify(False)
    
    def delete(self, employeeId):
        conn = databaseConn()
        conn.execute("DELETE FROM employee_info WHERE employeeId = ? ",
            (str(employeeId)))
        conn.commit()
        conn.close()
        
    def put(self, employeeId):
        req = request.get_json()
        fullname = req['fullname']
        gender = req['gender']
        email = req['email']
        address = req['address']
        academic = req['academic']
        password = req['password']

        conn = databaseConn()
        conn.execute("UPDATE employee_info SET employeeName = ?, gender = ?, email = ?, address = ?, academic = ?, password = ? WHERE employeeId = ? ",
            (fullname, gender, email, address, academic, password, str(employeeId)))
        print("update successfully")
        conn.commit()
        conn.close()

class adminAPI(Resource):
    def get(self):
        req = request.get_json()
        username = req['username']
        password = req['password']

        conn = databaseConn()
        auth = conn.execute('SELECT * FROM admin_auth WHERE username = ? and password = ?',(username, password)).fetchone()
        conn.commit()
        conn.close()

        return jsonify(auth)

class emplistAPI(Resource):
    def get(self):
        conn = databaseConn()
        posts = conn.execute('SELECT * FROM employee_info').fetchall()
        conn.commit()
        conn.close()

        # label each employee profile
        emplist = []
        for post in posts:
            emp = {}
            emp['employeeId'] = post[0]
            emp['fullname'] = post[1]
            emp['gender'] = post[2]
            emp['email'] = post[3]
            emp['address'] = post[4]
            emp['academic'] = post[5]
            emp['username'] = post[6]
            emp['password'] = post[7]
            emplist.append(emp)
        return jsonify(emplist)

# Registers the routes with the framework using the given endpoint
api.add_resource(loginAPI, "/api/login")
api.add_resource(profileAPI, "/api/profile/<int:employeeId>")
api.add_resource(adminAPI, "/api/admin")
api.add_resource(emplistAPI, "/api/emplist")

#---------------------Flask------------------------
@app.route("/")
def employee():
    # Vanish admin's trace
    if "admin" in session:
        if "admin_username" in session:
            session.pop("admin_username")
        session.pop("admin")

    return render_template("base.html")

@app.route("/admin")
def admin():
    # Vanish employee's trace
    if "emp_username" in session:
        session.pop("emp_username")
        session.pop("emp_id")

    # Register admin to session
    session["admin"]=True

    return redirect(url_for('login'))

@app.route("/logout")
def logout():
    # Vanish user's authentication and go back to login page
    if "admin" in session:
        if "admin_username" in session:
            session.pop("admin_username")
        return redirect(url_for('admin'))
    else:
        if "emp_username" in session:
            session.pop("emp_username")
            session.pop("emp_id")
        return redirect(url_for('login'))

@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        try:
            fullname = request.form["fullname"]
            gender = request.form["gender"]
            email = request.form["email"]
            address = request.form["address"]
            academic = request.form["academic"]
            username = request.form["username"]
            username = request.form["username"]
            password = request.form["password"]

            # Send HTTP request through Rest API
            response = requests.post(url+"/api/profile/"+'0', 
            json ={'fullname' : fullname, 'gender' : gender, 'email' : email, 'address' : address, 'academic' : academic,'username' : username, 'password' : password})
            
            # If error occur, go back to the signup page
            if response.json() == False:
                flash("All fields must be filled / Duplicate username")
                return render_template("signup.html")
        except:
            flash("All fields must be filled / Duplicate username")
            return render_template("signup.html")

        # If all go good, redirect user to login page to sign in
        return redirect(url_for('login'))
    else:
        return render_template("signup.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        # Getting params from html form
        username = request.form["username"]
        password = request.form["password"]
        if "admin" in session:
            response = requests.get(url+"/api/admin", json ={'username' : username, 'password' : password})
        else:
            response = requests.get(url+"/api/login", json ={'username' : username, 'password' : password})

        # If HTTP response 500, that means generic error response occurs.
        # In this case, it is most probably because of unmatched username and password.
        if response.status_code == 500 or response.json() == None:
            flash('Unmatched username and password')
            return render_template("login.html")

        # If login at admin portal successfully, save the username to session 
        if "admin" in session:
            session["admin_username"] = username
            return redirect(url_for('employeelist'))

        # # If login at employee portal successfully, save the username and employeeId to session 
        else:
            session['emp_username']=username
            session['emp_id']=response.json()
 
            return redirect(url_for('profile'))

    else:
        return render_template("login.html")

@app.route("/profile")
def profile():
    # Get profile information
    response = requests.get(url+"/api/profile/"+str(session['emp_id']))
    post = response.json()
    
    return render_template("profile.html", post = post)

@app.route("/updateprofile", methods=["POST", "GET"])
def updateprofile():
    if request.method == "POST":
        employeeId = request.form["id"]
        fullname = request.form["fullname"]
        gender = request.form["gender"]
        email = request.form["email"]
        address = request.form["address"]
        academic = request.form["academic"]
        username = request.form["username"]
        password = request.form["password"]
        response = requests.put(url+"/api/profile/"+str(employeeId), 
        json ={'fullname' : fullname, 'gender' : gender, 'email' : email, 'address' : address, 'academic' : academic, 'password' : password})
        
        # If it is at admin portal, go back to employeelist
        if "admin" in session:
            return redirect(url_for('employeelist'))
        # If it is at employee portal, go back to profile
        else:
            return redirect(url_for('profile'))
    else:
        employeeId = request.args['employeeId']
        response = requests.get(url+"/api/profile/"+str(employeeId))
        post = response.json()
        return render_template("updateprofile.html", post = post)

@app.route("/employeelist", methods=["POST", "GET"])
def employeelist():
    #If delete is pressed
    if request.method == "POST":
        employeeId = request.form["id"]
        response = requests.delete(url+"/api/profile/"+str(employeeId))
        return redirect(url_for('employeelist'))
    else:
        response = requests.get(url+"/api/emplist")
        posts = response.json()
        return render_template("employeelist.html", posts = posts)

@app.route("/addemployee", methods=["POST", "GET"])
def addemployee():
    if request.method == "POST":
        try:
            fullname = request.form["fullname"]
            gender = request.form["gender"]
            email = request.form["email"]
            address = request.form["address"]
            academic = request.form["academic"]
            username = request.form["username"]
            password = request.form["password"]

            # Send HTTP request through Rest API
            response = requests.post(url+"/api/profile/"+'0', 
            json ={'fullname' : fullname, 'gender' : gender, 'email' : email, 'address' : address, 'academic' : academic,'username' : username, 'password' : password})
            
            # If error occur, go back to the signup page
            if response.json() == False:
                return render_template("signup.html")
        except:
            flash("All fields must be filled / Invalid inputs")
            return render_template("signup.html")
            
        return redirect(url_for('employeelist'))
    else:
        return render_template("signup.html")

@app.route("/search", methods=["POST", "GET"])
def search():
    if request.method == "POST":
        employeeId = request.form["empId"]
        response = requests.get(url+"/api/profile/"+str(employeeId))
        post = response.json()
        if post == None:
            flash("No such employee. Please try again.")
        return render_template("search.html", post = post)
    else:
        return render_template("search.html", post = "N/A")

app.run(debug=True)