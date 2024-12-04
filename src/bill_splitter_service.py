import os
import time
from threading import Thread
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, request, jsonify, make_response, url_for, g
from db import DB
from pydantic import BaseModel, ValidationError
from uuid import uuid4
from PIL import Image
from flask_cors import CORS
from google.cloud import vision
from receipt_reader import extract_text_from_image, parse_receipt_text

load_dotenv()

app = Flask(__name__)
CORS(app)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser('~/igneous-aleph-394703-550f3acb3017.json')
# Database connection setup
db = DB(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

# Pydantic models for request and response validation
class BillBase(BaseModel):
    bill_name: Optional[str]
    total_amount: Optional[float]
    created_at: Optional[str]

class BillCreate(BillBase):
    bill_name: str
    total_amount: float

class BillUpdate(BillBase):
    pass

class BillItemBase(BaseModel):
    item_name: Optional[str]
    quantity: Optional[int]
    price: Optional[float]

class BillItemCreate(BillItemBase):
    item_name: str
    quantity: int
    price: float

class BillItemUpdate(BillItemBase):
    pass

class BillParticipantBase(BaseModel):
    user_id: Optional[str]
    amount_paid: Optional[float] = 0.0
    amount_owed: Optional[float] = 0.0
    created_at: Optional[str]

class BillParticipantCreate(BillParticipantBase):
    user_id: str

class BillParticipantUpdate(BillParticipantBase):
    pass

# Middleware for starting a timer before handling a request
@app.before_request
def start_timer():
    """Start a timer before handling a request."""
    g.start = time.time()

# Middleware for logging request details after the response is generated
@app.after_request
def log_request(response):
    """Log the request details after the response is generated."""
    duration = time.time() - g.start
    request_details = f"{request.method} {request.path} - Status: {response.status_code} - Duration: {duration:.4f}s"
    print(request_details)  # For production, use a proper logging mechanism
    return response

@app.route("/")
def healthcheck():
    return make_response("<h1>Bill Splitter Microservice</h1>", 200)

# Routes for managing bills

@app.route("/bills", methods=["GET"])
def get_bills():
    """Fetch a list of bills with optional query parameters."""
    bill_name = request.args.get("bill_name")
    skip = int(request.args.get("skip", 0))
    limit = int(request.args.get("limit", 10))

    filters = {k: v for k, v in {"bill_name": bill_name}.items() if v}
    bills = db.select("Bills", rows=[], filters=filters, limit=limit, offset=skip)
    
    # Convert Decimal fields to float
    for bill in bills:
        bill["total_amount"] = float(bill["total_amount"])
    
    return jsonify(bills), 200


@app.route("/bills/<bill_id>", methods=["GET"])
def get_bill(bill_id: str):
    """Fetch a single bill by ID."""
    bills = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not bills:
        return jsonify({"detail": "Bill not found"}), 404

    bill = bills[0]
    return jsonify(bill), 200

@app.route("/bills", methods=["POST"])
def create_bill():
    """Create a new bill."""
    try:
        bill_data = BillCreate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    bill_dict = bill_data.dict()
    bill_dict["bill_id"] = str(uuid4()).replace("-", "")
    bill_dict["created_at"] = time.strftime('%Y-%m-%d %H:%M:%S')

    # Insert into Bills table
    db.insert("Bills", {
        "bill_id": bill_dict["bill_id"],
        "bill_name": bill_dict["bill_name"],
        "total_amount": bill_dict["total_amount"],
        "created_at": bill_dict["created_at"]
    })

    print(f"Bill created: {bill_dict}")  # Print created bill details
    headers = {"Location": url_for("get_bill", bill_id=bill_dict["bill_id"])}
    return make_response(jsonify(bill_dict), 201, headers)

@app.route("/bills/<bill_id>", methods=["PUT"])
def update_bill(bill_id: str):
    """Update an existing bill."""
    try:
        bill_update_data = BillUpdate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    existing_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not existing_bill:
        return jsonify({"detail": "Bill not found"}), 404

    # Extract update data
    update_data = {k: v for k, v in bill_update_data.dict(exclude_unset=True).items() if v is not None}

    # Check if update_data is empty
    if not update_data:
        return jsonify({"detail": "No valid fields provided for update"}), 400

    db.update("Bills", update_data, filters={"bill_id": bill_id})

    # Fetch updated bill data
    updated_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})[0]

    return jsonify(updated_bill), 200

@app.route("/bills/<bill_id>", methods=["DELETE"])
def delete_bill(bill_id: str):
    """Delete a bill by ID."""
    existing_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not existing_bill:
        return jsonify({"detail": "Bill not found"}), 404

    db.delete("Bills", filters={"bill_id": bill_id})
    print(f"Bill deleted: {existing_bill}")  # Print deleted bill details
    return "", 204

# Routes for managing bill items

@app.route("/bills/<bill_id>/items", methods=["GET"])
def get_bill_items(bill_id: str):
    """Fetch items associated with a bill."""
    existing_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not existing_bill:
        return jsonify({"detail": "Bill not found"}), 404

    items = db.select("Bill_Items", rows=[], filters={"bill_id": bill_id})
    return jsonify(items), 200

@app.route("/bills/<bill_id>/items", methods=["POST"])
def create_bill_item(bill_id: str):
    """Create an item for a bill."""
    existing_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not existing_bill:
        return jsonify({"detail": "Bill not found"}), 404

    try:
        item_data = BillItemCreate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    item_dict = item_data.dict()
    item_dict["bill_id"] = bill_id

    # Insert into Bill_Items table
    db.insert("Bill_Items", {
        "bill_id": item_dict["bill_id"],
        "item_name": item_dict["item_name"],
        "quantity": item_dict["quantity"],
        "price": item_dict["price"]
    })

    print(f"Bill item created: {item_dict}")  # Print created item details
    return make_response(jsonify(item_dict), 201)

@app.route("/bills/<bill_id>/items/<item_id>", methods=["PUT"])
def update_bill_item(bill_id: str, item_id: str):
    """Update an item of a bill."""
    try:
        item_update_data = BillItemUpdate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    existing_item = db.select("Bill_Items", rows=[], filters={"bill_id": bill_id, "item_id": item_id})
    if not existing_item:
        return jsonify({"detail": "Item not found"}), 404

    # Extract update data
    update_data = {k: v for k, v in item_update_data.dict(exclude_unset=True).items() if v is not None}

    # Check if update_data is empty
    if not update_data:
        return jsonify({"detail": "No valid fields provided for update"}), 400

    db.update("Bill_Items", update_data, filters={"bill_id": bill_id, "item_id": item_id})

    # Fetch updated item data
    updated_item = db.select("Bill_Items", rows=[], filters={"bill_id": bill_id, "item_id": item_id})[0]

    return jsonify(updated_item), 200

@app.route("/bills/<bill_id>/items/<item_id>", methods=["DELETE"])
def delete_bill_item(bill_id: str, item_id: str):
    """Delete an item from a bill."""
    existing_item = db.select("Bill_Items", rows=[], filters={"bill_id": bill_id, "item_id": item_id})
    if not existing_item:
        return jsonify({"detail": "Item not found"}), 404

    db.delete("Bill_Items", filters={"bill_id": bill_id, "item_id": item_id})
    print(f"Bill item deleted: {existing_item}")  # Print deleted item details
    return "", 204

# Routes for managing bill participants

@app.route("/bills/<bill_id>/participants", methods=["GET"])
def get_bill_participants(bill_id: str):
    """Fetch participants associated with a bill."""
    existing_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not existing_bill:
        return jsonify({"detail": "Bill not found"}), 404

    participants = db.select("Bill_Participants", rows=[], filters={"bill_id": bill_id})
    return jsonify(participants), 200

@app.route("/bills/<bill_id>/participants", methods=["POST"])
def add_bill_participant(bill_id: str):
    """Add a participant to a bill."""
    existing_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not existing_bill:
        return jsonify({"detail": "Bill not found"}), 404

    try:
        participant_data = BillParticipantCreate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    participant_dict = participant_data.dict()
    participant_dict["bill_id"] = bill_id
    participant_dict["created_at"] = time.strftime('%Y-%m-%d %H:%M:%S')

    # Insert into Bill_Participants table
    db.insert("Bill_Participants", {
        "bill_id": participant_dict["bill_id"],
        "user_id": participant_dict["user_id"],
        "amount_paid": participant_dict.get("amount_paid", 0.0),
        "amount_owed": participant_dict.get("amount_owed", 0.0),
        "created_at": participant_dict["created_at"]
    })

    print(f"Bill participant added: {participant_dict}")  # Print added participant details
    return make_response(jsonify(participant_dict), 201)

@app.route("/bills/<bill_id>/participants/<participant_id>", methods=["PUT"])
def update_bill_participant(bill_id: str, participant_id: str):
    """Update a participant of a bill."""
    try:
        participant_update_data = BillParticipantUpdate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    existing_participant = db.select("Bill_Participants", rows=[], filters={"bill_id": bill_id, "id": participant_id})
    if not existing_participant:
        return jsonify({"detail": "Participant not found"}), 404

    # Extract update data
    update_data = {k: v for k, v in participant_update_data.dict(exclude_unset=True).items() if v is not None}

    # Check if update_data is empty
    if not update_data:
        return jsonify({"detail": "No valid fields provided for update"}), 400

    db.update("Bill_Participants", update_data, filters={"bill_id": bill_id, "id": participant_id})

    # Fetch updated participant data
    updated_participant = db.select("Bill_Participants", rows=[], filters={"bill_id": bill_id, "id": participant_id})[0]

    return jsonify(updated_participant), 200

@app.route("/bills/<bill_id>/participants/<participant_id>", methods=["DELETE"])
def delete_bill_participant(bill_id: str, participant_id: str):
    """Remove a participant from a bill."""
    existing_participant = db.select("Bill_Participants", rows=[], filters={"bill_id": bill_id, "id": participant_id})
    if not existing_participant:
        return jsonify({"detail": "Participant not found"}), 404

    db.delete("Bill_Participants", filters={"bill_id": bill_id, "id": participant_id})
    print(f"Bill participant deleted: {existing_participant}")  # Print deleted participant details
    return "", 204

# Asynchronous operations
@app.route("/bills/<bill_id>/calculate", methods=["POST"])
def calculate_total_async(bill_id: str):
    """Asynchronous calculation of the total cost for a bill."""
    existing_bill = db.select("Bills", rows=[], filters={"bill_id": bill_id})
    if not existing_bill:
        return jsonify({"detail": "Bill not found"}), 404

    def calculate_total_task(bill_id: str):
        items = db.select("Bill_Items", rows=["price", "quantity"], filters={"bill_id": bill_id})
        total = sum(item["price"] * item["quantity"] for item in items)
        db.update("Bills", {"total_amount": total}, filters={"bill_id": bill_id})
        print(f"Total calculated for bill {bill_id}: {total}")

    Thread(target=calculate_total_task, args=(bill_id,)).start()
    return jsonify({"detail": "Calculation started"}), 202

# Receipt processing
@app.route('/bills/<bill_id>/receipt', methods=['POST'])
def process_receipt(bill_id):
    """Process receipt image for a bill using receipt_reader.py functions."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Validate file extension
    if not file.filename.lower().endswith(('jpg', 'jpeg', 'png')):
        return jsonify({'error': 'Invalid file format'}), 400

    try:
        # Open and verify image
        image = Image.open(file)
        image.verify()  # Ensure the file is an actual image
        file.seek(0)  # Reset file pointer after verification

        # Read image content from the in-memory file
        image_content = file.read()

        # Initialize Google Cloud Vision client
        client = vision.ImageAnnotatorClient()

        # Extract text from the image using the imported function
        extracted_text = extract_text_from_image(client, image_content)

        # Parse the extracted text using the imported function
        receipt_data = parse_receipt_text(extracted_text)
        print(receipt_data)

        # Insert parsed items into the database
        for item in receipt_data:
            item_name, quantity, price = item
            if item_name and price is not None:
                db.insert("Bill_Items", {
                    "bill_id": bill_id,
                    "item_name": item_name,
                    "quantity": quantity or 1,
                    "price": price
                })

        return jsonify({
            'message': 'Receipt processed successfully',
            'bill_id': bill_id
        }), 200

    except Exception as e:
        print(f"Error processing receipt: {e}")  # Log the error
        return jsonify({'error': f'Failed to process the image: {str(e)}'}), 500

# Run the Flask app if executed as main
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
