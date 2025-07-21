from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
import calendar

# --------------------------------------------------------- Adhish Biju------------------

app = Flask(__name__)
app.secret_key = "your_secret_key"

# ------ Database setup ------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.String(10), nullable=False)  # format: YYYY-MM-DD

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.String(10), nullable=False)  # format: YYYY-MM-DD
    amount = db.Column(db.Float, nullable=True)

# Create tables
with app.app_context():
    db.create_all()

# -------- Routes ---------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("index.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome, {user.username}!")
            return redirect("/dashboard")
        else:
            flash("Invalid email or password.")
            return redirect("/login")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered!")
            return redirect("/signup")

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.")
        return redirect("/login")
    return render_template("signup.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.")
        return redirect("/login")

    user_id = session["user_id"]

    # Handle income update
    if request.method == "POST" and "income" in request.form:
        try:
            amount = float(request.form["income"])
        except ValueError:
            flash("Please enter a valid number for income.")
            return redirect("/dashboard")

        income = Income.query.filter_by(user_id=user_id).first()
        if income:
            income.amount = amount
        else:
            new_income = Income(user_id=user_id, amount=amount)
            db.session.add(new_income)
        db.session.commit()
        flash("Income updated successfully!")
        return redirect("/dashboard")

    # Get income for the user
    income_obj = Income.query.filter_by(user_id=user_id).first()
    total_income = income_obj.amount if income_obj else 0.0

    # Get all expenses for the user
    expenses = Expense.query.filter_by(user_id=user_id).all()
    total_expense = sum(exp.amount for exp in expenses)
    balance = total_income - total_expense

    # Find top category
    if expenses:
        category_totals = {}
        for exp in expenses:
            category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount
        top_category = max(category_totals, key=category_totals.get)
    else:
        top_category = "N/A"

    categories = ["Meal", "Transport", "Fees", "Shopping"]

    return render_template(
        "dashboard.html",
        username=session["username"],
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        top_category=top_category,
        balance=balance,
        categories=categories
    )

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        flash("Please log in to add expenses.")
        return redirect("/login")

    try:
        amount = float(request.form["amount"])
    except ValueError:
        flash("Please enter a valid amount.")
        return redirect("/dashboard")

    category = request.form["category"]
    description = request.form.get("description", "")
    date = request.form["date"]

    new_expense = Expense(
        user_id=session["user_id"],
        amount=amount,
        category=category,
        description=description,
        date=date
    )
    db.session.add(new_expense)
    db.session.commit()
    flash("Expense added successfully!")
    return redirect("/dashboard")

@app.route("/delete_expense/<int:id>", methods=["POST"])
def delete_expense(id):
    if "user_id" not in session:
        flash("Please log in to delete expenses.")
        return redirect("/login")

    expense = Expense.query.get_or_404(id)
    if expense.user_id != session["user_id"]:
        flash("You are not authorized to delete this expense.")
        return redirect("/dashboard")

    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted successfully!")
    return redirect("/dashboard")

@app.route("/monthly", methods=["GET", "POST"])
def monthly():
    if "user_id" not in session:
        flash("Please log in to access monthly reports.")
        return redirect("/login")

    user_id = session["user_id"]
    expenses = Expense.query.filter_by(user_id=user_id).all()

    month_expenses_dict = {}
    for exp in expenses:
        month_num = int(exp.date.split("-")[1])
        month_name = calendar.month_name[month_num]
        if month_name not in month_expenses_dict:
            month_expenses_dict[month_name] = []
        month_expenses_dict[month_name].append(exp)

    all_months = sorted(month_expenses_dict.keys(),
                        key=lambda m: list(calendar.month_name).index(m))

    if not all_months:
        return render_template("monthly.html", all_months=[], selected_month=None, month_expenses=[], total_for_selected_month=0, top_category="N/A")

    selected_month = request.args.get("month") or all_months[0]
    month_expenses = month_expenses_dict.get(selected_month, [])

    total_for_selected_month = sum(exp.amount for exp in month_expenses)
    if month_expenses:
        category_totals = {}
        for exp in month_expenses:
            category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount
        top_category = max(category_totals, key=category_totals.get)
    else:
        top_category = "N/A"

    return render_template(
        'monthly.html',
        all_months=all_months,
        selected_month=selected_month,
        month_expenses=month_expenses,
        total_for_selected_month=total_for_selected_month,
        top_category=top_category
    )

@app.route("/delete_monthly_expense/<int:id>", methods=["POST"])
def delete_monthly_expense(id):
    if "user_id" not in session:
        flash("Please log in to delete expenses.")
        return redirect("/login")

    expense = Expense.query.get_or_404(id)
    if expense.user_id != session["user_id"]:
        flash("You are not authorized to delete this expense.")
        return redirect("/monthly")

    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted successfully!")
    return redirect("/monthly")

@app.route('/alerts', methods=['GET', 'POST'])
def alerts():
    if "user_id" not in session:
        flash("Please log in to access alerts.")
        return redirect("/login")

    user_id = session["user_id"]

    if request.method == "POST":
        title = request.form.get("title")
        due_date = request.form.get("due_date")
        amount = request.form.get("amount", None)

        if not title or not due_date:
            flash("Title and due date are required!")
            return redirect("/alerts")

        try:
            amount_value = float(amount) if amount else None
        except ValueError:
            flash("Please enter a valid amount.")
            return redirect("/alerts")

        new_alert = Alert(user_id=user_id, title=title, due_date=due_date, amount=amount_value)
        db.session.add(new_alert)
        db.session.commit()
        flash("Alert added successfully!")
        return redirect("/alerts")

    alerts = Alert.query.filter_by(user_id=user_id).all()
    return render_template("alerts.html", alerts=alerts)

@app.route("/delete_alert/<int:id>", methods=["POST"])
def delete_alert(id):
    if "user_id" not in session:
        flash("Please log in to delete alerts.")
        return redirect("/login")

    alert = Alert.query.get_or_404(id)
    if alert.user_id != session["user_id"]:
        flash("You are not authorized to delete this alert.")
        return redirect("/alerts")

    db.session.delete(alert)
    db.session.commit()
    flash("Alert deleted successfully!")
    return redirect("/alerts")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect("/")

if __name__ == '__main__':
    app.run(debug=True)
