import os
import requests
from flask import Flask, jsonify
from pydantic import BaseModel, ValidationError

app = Flask(__name__)

# Pydantic model for validation
class Payment(BaseModel):
    user: str
    amount_paid: float


@app.route("/", methods=["GET"])
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Home Page</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #f0f0f0;
            }
            .container {
                text-align: center;
                background: #fff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }
            button {
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                border: none;
                background-color: #007bff;
                color: #fff;
                border-radius: 5px;
            }
            button:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to the Social Accountability Service</h1>
            <button onclick="location.href='/payments'">Go to Payments Page</button>
        </div>
    </body>
    </html>
    '''


# Endpoint to get the amount each person has paid
@app.route("/payments", methods=["GET"])
def get_payments():
    try:
        # Retrieve user data from the user management microservice
        response = requests.get("http://localhost:5000/users")
        response.raise_for_status()
        users = response.json()

        # Extract payment information
        payments = [
            Payment(
                user=f"{user['First_name']} {user['Last_name']}",
                amount_paid=user.get("Points", 0)
            )
            for user in users
        ]
        return jsonify([payment.dict() for payment in payments]), 200
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

if __name__ == "__main__":
    app.run(debug=True)
