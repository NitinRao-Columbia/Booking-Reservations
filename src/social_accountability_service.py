import os
from flask import Flask, request, jsonify
from db import DB
from pydantic import BaseModel, ValidationError
from typing import List, Optional

app = Flask(__name__)

# Initialize the database
db = DB(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)

# Pydantic models for validation
class Friend(BaseModel):
    name: str
    email: str

class AccountabilityMetrics(BaseModel):
    points: int
    days_late: int
    total_amount: float

class LeaderboardEntry(BaseModel):
    user: str
    metrics: AccountabilityMetrics

# Endpoints
@app.route("/friends", methods=["POST"])
def add_friend():
    try:
        data = request.get_json()
        friend = Friend(**data)
        db.execute("INSERT INTO friends (name, email) VALUES (%s, %s)", (friend.name, friend.email))
        return jsonify({"message": "Friend added successfully!"}), 201
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

@app.route("/friends/<email>", methods=["DELETE"])
def remove_friend(email):
    db.execute("DELETE FROM friends WHERE email = %s", (email,))
    return jsonify({"message": "Friend removed successfully!"}), 200

@app.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    results = db.query("SELECT user, points, days_late, total_amount FROM leaderboard ORDER BY points DESC")
    leaderboard = [
        LeaderboardEntry(
            user=row["user"],
            metrics=AccountabilityMetrics(
                points=row["points"],
                days_late=row["days_late"],
                total_amount=row["total_amount"],
            ),
        )
        for row in results
    ]
    return jsonify([entry.dict() for entry in leaderboard]), 200

@app.route("/metrics", methods=["POST"])
def update_metrics():
    try:
        data = request.get_json()
        user = data.get("user")
        metrics = AccountabilityMetrics(**data.get("metrics"))
        db.execute(
            "INSERT INTO leaderboard (user, points, days_late, total_amount) VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE points = %s, days_late = %s, total_amount = %s",
            (user, metrics.points, metrics.days_late, metrics.total_amount,
             metrics.points, metrics.days_late, metrics.total_amount),
        )
        return jsonify({"message": "Metrics updated successfully!"}), 200
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

if __name__ == "__main__":
    app.run(debug=True)
