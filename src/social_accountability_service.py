import os
import requests
from flask import Flask, jsonify
from pydantic import BaseModel, ValidationError

app = Flask(__name__)

# Pydantic model for validation
class Payment(BaseModel):
    user: str
    amount_paid: float

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
