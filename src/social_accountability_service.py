import os
import time
from flask import Flask, jsonify, request, make_response
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import requests
from dotenv import load_dotenv  # type: ignore
import requests
from datetime import datetime


# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Base URL for the User Management Microservice
USER_MANAGEMENT_BASE_URL = os.getenv("USER_MANAGEMENT_BASE_URL", "http://localhost:8001")

# Swagger UI setup
SWAGGER_URL = '/swagger-ui'  # URL for Swagger UI
API_URL = '/swagger'         # Existing route for Swagger spec

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  # Swagger UI blueprint endpoint
    API_URL,      # API spec endpoint
    config={
        'app_name': "Social Accountability Microservice"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route("/swagger")
def swagger_spec():
    """
    Generate Swagger documentation.
    """
    swag = {
        "swagger": "2.0",
        "info": {
            "title": "Social Accountability Microservice",
            "version": "1.0.0",
            "description": "A microservice to manage social accountability features like leaderboards."
        },
        "paths": {
            "/leaderboard": {
                "get": {
                    "summary": "Get the leaderboard",
                    "description": "Fetches users and their points from the User Management Microservice and returns a sorted leaderboard.",
                    "tags": ["Leaderboard"],
                    "responses": {
                        "200": {
                            "description": "A sorted leaderboard of users by points.",
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {"type": "string"},
                                        "first_name": {"type": "string"},
                                        "last_name": {"type": "string"},
                                        "points": {"type": "integer"}
                                    }
                                }
                            }
                        },
                        "500": {
                            "description": "Internal Server Error"
                        }
                    }
                }
            }
        }
    }
    return jsonify(swag)

#pub to user managment sub
def notify_user_management():
    print("trying to notify")
    webhook_url = "http://3.145.144.209:8001/webhook"  # User Management webhook URL
    #Generate current UTC timestamp in ISO 8601 format
    current_time = datetime.utcnow().isoformat() + "Z"
    payload = {
        "event_type": "UserDataAccess",
        "timestamp": current_time,
        "message": "Social Accountability service is about to access user data."
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        if response.status_code == 200:
            print("Notification sent successfully!")
        else:
            print(f"Failed to notify: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending notification: {e}")

@app.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    """
    Fetches users and their points from the User Management Microservice and returns a sorted leaderboard.
    ---
    tags:
      - Leaderboard
    responses:
      200:
        description: Leaderboard fetched successfully.
        schema:
          type: array
          items:
            type: object
            properties:
              user_id:
                type: string
              first_name:
                type: string
              last_name:
                type: string
              points:
                type: integer
      500:
        description: Internal Server Error
    """
    try:
        # Fetch users from User Management Microservice
        notify_user_management()
        response = requests.get(f"{USER_MANAGEMENT_BASE_URL}/users?limit=10000")  # Large limit to bypass pagination
        if response.status_code != 200:
            return jsonify({"detail": "Failed to fetch user data"}), 500

        users = response.json()

        leaderboard = []

        # Fetch points for each user and construct the leaderboard
        for user in users:
            user_id = user.get("user_id")
            first_name = user.get("first_name")
            last_name = user.get("last_name")

            # Get points using the get_user_points endpoint
            points_response = requests.get(f"{USER_MANAGEMENT_BASE_URL}/users/{user_id}/points")
            points = 0  # Default points if the request fails
            if points_response.status_code == 200:
                points = points_response.json().get("points", 0)

            leaderboard.append({
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "points": points
            })

        # Sort the leaderboard by points in descending order
        leaderboard = sorted(leaderboard, key=lambda x: x["points"], reverse=True)

        return jsonify(leaderboard), 200

    except Exception as e:
        return jsonify({"detail": "An error occurred while fetching the leaderboard", "error": str(e)}), 500

# Health check endpoint
@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return make_response("<h1>Social Accountability Microservice</h1>", 200)

# Run the Flask app
if __name__ == "__main__":
    print("running hello")
    app.run(host="0.0.0.0", port=8002)
