from flask import Flask, render_template, request, jsonify, url_for,session,redirect
import os
import datetime
import requests

app = Flask(__name__)
app.secret_key = 'BAD_SECRET_KEY'

# Configuration
USER_DATA_FILE = "users.txt"
LOG_FILE_DIR = "ride_logs"
SERPAPI_KEY = os.getenv('SERPAPI_KEY', "05532de29082adcb6aee4ce9f32cf0f17196740a71387643ba7001893ceb22da")
CURRENCY_CONVERSION_API_KEY = os.getenv('CURRENCY_CONVERSION_API_KEY', "fca_live_f694y2i0X77m2fU6f9b20b22V7j3f4u6g222479")
log_file = "ride_logs/ride_history"
# Ensure ride logs directory exists
if not os.path.exists(LOG_FILE_DIR):
    os.makedirs(LOG_FILE_DIR)

# Ensure user data file exists
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as f:
        pass  # Create empty user file

def get_user_log_file(email):
    """Returns the path for a user's log file."""
    return os.path.join(LOG_FILE_DIR, f"{email}.txt")

def log_ride(email, start, destination, vehicle, cost_details):
    """Logs ride details into a user's specific text file."""
    global log_file
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"[{timestamp}] Start: {start}, Destination: {destination}, Vehicle: {vehicle}, Costs: {cost_details}\n"
    if os.path.exists(log_file):
        with open(log_file, "a") as file:
            file.write(log_entry)
    else:
        with open(log_file, "w") as file:
            file.write(log_entry)

def log_ride1(email, start, destination, vehicle):
    global log_file
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Start: {start}, Destination: {destination}, Vehicle: {vehicle}\n"
    if os.path.exists(log_file):
        with open(log_file, "a") as file:
            file.write(log_entry)
    else:
        with open(log_file, "w") as file:
            file.write(log_entry)     

@app.route("/log_ride", methods=["POST"])
def log_ride_endpoint():
    """API to log ride details."""
    data = request.json
    log_ride(session["email"], data["start"], data["destination"], data["vehicle"], data["costs"])
    return jsonify({"message": "Ride logged successfully"})

@app.route("/log_ride1", methods=["Get"])
def log_ride_endpoint1():
    start = request.args.get("start")
    end   = request.args.get("end")
    log_ride1(session["email"], start, end,'Flight')
    return render_template("index.html")


@app.route("/get_history", methods=["GET"])
def get_history():
    """API to fetch ride history."""
    email = session['email']
    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not os.path.exists(log_file):
        return jsonify({"history": []})

    with open(log_file, "r") as file:
        history = file.readlines()

    return jsonify({"history": history})

@app.route("/")
def home():
    global log_file
    log_file = 'ride_logs/ride_history'
    session.pop('email', default=None)
    return render_template("login.html")

@app.route("/signup", methods=["POST"])
def signup():
    """User Sign Up."""
    data = request.json
    if not all(k in data for k in ["fullname", "email", "phone", "password"]):
        return jsonify({"error": "Missing fields"}), 400

    email, password, fullname, phone = data["email"], data["password"], data["fullname"], data["phone"]

    # Check if user already exists
    with open(USER_DATA_FILE, "r") as f:
        for line in f:
            stored_email, _ = line.strip().split(",", 1)
            if stored_email == email:
                return jsonify({"message": "User already exists! Try signing in."})

    # Store user data
    with open(USER_DATA_FILE, "a") as f:
        f.write(f"{email},{password},{fullname},{phone}\n")

    return jsonify({"message": "Sign Up Successful! Please Sign In."})

@app.route("/signin", methods=["POST"])
def signin():
    """User Sign In."""
    data = request.json
    if not all(k in data for k in ["email", "password"]):
        return jsonify({"error": "Missing fields"}), 400

    email, password = data["email"], data["password"]

    with open(USER_DATA_FILE, "r") as f:
        for line in f:
            stored_email, stored_password, _, _ = line.strip().split(",", 3)
            if stored_email == email and stored_password == password:
                global log_file
                log_file+=email+".txt"
                session['email'] = email
                return jsonify({"redirect": url_for("dashboard")})

    return jsonify({"message": "Invalid Email or Password"})

@app.route("/dashboard")
def dashboard():
    return render_template("index.html")

@app.route("/check")
def vehicle_cost():
    """Render Vehicle Cost Page."""
    return render_template("vehicle_cost.html")

@app.route("/act")
def history_page():
    """Render Ride History Page."""
    return render_template("history.html")

def convert_currency(amount, from_currency, to_currency):
    """Converts currency using an external API with debugging."""
    if from_currency == to_currency:
        return amount

    url = f"https://api.freecurrencyapi.com/v1/latest?apikey={CURRENCY_CONVERSION_API_KEY}&currencies={to_currency}&base_currency={from_currency}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        rate = data["data"].get(to_currency)

        print(f"API Response: {data}")  # Print the API response for debugging
        print(f"Exchange Rate: {rate}") # Print the retrieved rate

        if rate:
            return round(amount * rate, 2)
        else:
            print(f"Currency conversion rate not found for {to_currency}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Currency conversion failed: {e}")
        return None

@app.route("/flights", methods=["GET", "POST"])
def flights():
    """Flight Search Page with Currency Conversion"""
    currency = request.args.get("currency", "USD")  # Default to USD

    if request.method == "POST":
        departure = request.form.get("departure")
        arrival = request.form.get("arrival")
        outbound_date = request.form.get("outbound_date")
        return_date = request.form.get("return_date")
        log_ride1(session["email"], departure, arrival, "Flight")
        params = {
            "api_key": SERPAPI_KEY,
            "engine": "google_flights",
            "departure_id": departure,
            "arrival_id": arrival,
            "outbound_date": outbound_date,
            "return_date": return_date,
        }
        try:
            search = requests.get("https://serpapi.com/search", params=params)
            search.raise_for_status()
            response = search.json()
        except requests.exceptions.RequestException as e:
            print(f"Flight API error: {e}")
            return render_template("flights.html", flights=None, currency=currency, error="Flight search failed.")

        flights = []

        for key in ["best_flights", "other_flights"]:
            for item in response.get(key, []):
                for flight in item.get("flights", []):
                    price = item.get("price", "N/A")

                    # Extract price and convert
                    if isinstance(price, str) and price != "N/A":
                        parts = price.split()
                        if len(parts) == 2:
                            original_currency, amount = parts[0], float(parts[1].replace(",", ""))
                            converted_amount = convert_currency(amount, original_currency, currency)
                            price = f"{currency} {converted_amount:,.2f}" if converted_amount else "N/A"
                    elif isinstance(price, (int, float)):
                        converted_amount = convert_currency(price, "USD", currency)
                        price = f"{currency} {converted_amount:,.2f}" if converted_amount else "N/A"

                    flights.append({
                        "airline": flight.get("airline", "Unknown"),
                        "airplane": flight.get("airplane", "Unknown"),
                        "departure_airport": flight.get("departure_airport", {"name": "Unknown", "time": "Unknown"}),
                        "arrival_airport": flight.get("arrival_airport", {"name": "Unknown", "time": "Unknown"}),
                        "price": price,
                        "original_price": item.get("price", "N/A"),
                    })

        return render_template("flights.html", flights=flights, currency=currency)

    return render_template("flights.html", flights=None, currency=currency)

@app.route("/currency_converter", methods=["GET"])
def currency_converter():
    """Render Currency Converter Page."""
    return render_template("currency_converter.html")

@app.route('/convert_currency', methods=['POST'])
def convert_currency_api():
    data = request.get_json()
    amount = data.get('amount')
    from_currency = data.get('from_currency')
    to_currency = data.get('to_currency')

    converted_amount = convert_currency(amount, from_currency, to_currency)
    if converted_amount is not None:
        return jsonify({'converted_amount': converted_amount})
    else:
        return jsonify({'error': 'Currency conversion failed'}), 500

@app.route("/iata_codes")
def iata_codes():
    """Render IATA Codes Page."""
    return render_template("iata_codes.html")


if __name__ == "__main__":
    app.run(port=4000,debug=True)
