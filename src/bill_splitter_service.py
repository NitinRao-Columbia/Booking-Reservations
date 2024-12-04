from flask import Flask, request, jsonify
import threading
import time
from PIL import Image

app = Flask(__name__)

from flask_cors import CORS
CORS(app)

# Sample Data Storage
bills = {}
items = {}

# Routes for managing bills and items

# GET, PUT, POST for Bills
def generate_id():
    return str(len(bills) + 1)

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Bill Splitter API!"})

# POST: Process receipt directly
@app.route('/bills/<bill_id>/receipt', methods=['POST'])
def process_receipt(bill_id):
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

        return jsonify({
            'message': 'Receipt processed successfully',
            'bill_id': bill_id
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to process the image: {str(e)}'}), 500
    
# GET: Retrieve a bill
@app.route('/bills/<bill_id>', methods=['GET'])
# Req 1 This GET method satisfies the requirement for retrieving a resource (bill) by its ID.
def get_bill(bill_id):
    bill = bills.get(bill_id)
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    return jsonify(bill)

# POST: Create a new bill
@app.route('/bills', methods=['POST'])
# Req 1 This POST method satisfies the requirement for creating a resource (bill).
def create_bill():
    data = request.get_json()
    bill_id = generate_id()
    bills[bill_id] = data
    return jsonify({'id': bill_id, 'message': 'Bill created successfully'}), 201

# PUT: Update an existing bill
@app.route('/bills/<bill_id>', methods=['PUT'])
# Req 1 This PUT method satisfies the requirement for updating a resource (bill) by its ID.
def update_bill(bill_id):
    if bill_id not in bills:
        return jsonify({'error': 'Bill not found'}), 404
    data = request.get_json()
    bills[bill_id] = data
    return jsonify({'message': 'Bill updated successfully'}), 200

# Basic Navigation Paths with Query Parameters
@app.route('/bills', methods=['GET'])
# Req 2 This GET method with query parameters supports basic navigation paths by allowing filtering by user_id.
def get_bills():
    user_id = request.args.get('user_id')
    if user_id:
        user_bills = {bill_id: bill for bill_id, bill in bills.items() if bill.get('user_id') == user_id}
        return jsonify(user_bills)
    return jsonify(bills)

# Synchronous Call to Sub-resource
@app.route('/bills/<bill_id>/items', methods=['GET'])
# Req 3 This GET method provides a synchronous call to sub-resources (items associated with a bill).
def get_bill_items(bill_id):
    if bill_id not in bills:
        return jsonify({'error': 'Bill not found'}), 404
    return jsonify(items.get(bill_id, []))

# POST: Create an item for a bill
@app.route('/bills/<bill_id>/items', methods=['POST'])
# Req 1 This POST method allows the creation of sub-resources (items) for a given bill.
def create_item(bill_id):
    if bill_id not in bills:
        return jsonify({'error': 'Bill not found'}), 404
    data = request.get_json()
    item_id = generate_id()
    if bill_id not in items:
        items[bill_id] = []
    items[bill_id].append({**data, 'item_id': item_id})
    return jsonify({'item_id': item_id, 'message': 'Item created successfully'}), 201

# Asynchronous Resource Update
@app.route('/bills/<bill_id>/calculate', methods=['POST'])
# Req 4 This POST method implements an asynchronous operation to calculate the total cost for a bill.
def calculate_total_async(bill_id):
    if bill_id not in bills:
        return jsonify({'error': 'Bill not found'}), 404
    thread = threading.Thread(target=calculate_total, args=(bill_id,))
    thread.start()
    return jsonify({'message': 'Calculation started'}), 202

def calculate_total(bill_id):
    # Req 4 This function performs the asynchronous calculation of the total cost for a bill, simulating a long-running process.
    # time.sleep(5)  # Simulate long calculation
    bill_items = items.get(bill_id, [])
    total = sum(item['cost'] for item in bill_items)
    bills[bill_id]['total'] = total
    print(f'Total calculated for bill {bill_id}: {total}')

if __name__ == '__main__':
    app.run(debug=True)
