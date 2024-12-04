import io
import os
import re
import sys
import pandas as pd
from google.cloud import vision
from google.cloud.vision_v1 import types
from PIL import Image



def get_image_content(image_path):
    """Reads the image file and returns its binary content."""
    with io.open(image_path, 'rb') as image_file:
        return image_file.read()


def extract_text_from_image(client, image_content):
    """Uses Google Vision OCR to extract text from an image."""
    image = types.Image(content=image_content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        extracted_text = texts[0].description
        print('Detected text:')
        print(extracted_text)
    else:
        print('No text detected')
        extracted_text = ""

    if response.error.message:
        raise Exception(f'{response.error.message}')

    return extracted_text

def parse_receipt_text(extracted_text):
    """Parses the receipt text to extract items, quantities, and total prices."""
    lines = extracted_text.strip().split('\n')
    item_lines = []
    price_lines = []

    # Separate items and prices
    for line in lines:
        if re.match(r"^\d+\.\d{2}$", line.strip()):  # Line is a price
            price_lines.append(float(line.strip()))
        else:  # Line is an item
            item_lines.append(line.strip())

    # Pair items with prices
    print(f"Items: {item_lines}")
    print(f"Prices: {price_lines}")
    receipt_data = []
    max_pairs = max(len(item_lines), len(price_lines))  # Ensure all items are accounted for
    for i in range(max_pairs):
        # Get the item and price, or assign NaN for missing values
        item_line = item_lines[i] if i < len(item_lines) else None
        price = price_lines[i] if i < len(price_lines) else None

        # Extract quantity and item name
        if item_line:
            match = re.match(r"^\s*(\d+)?\s*(.*?)\s*(\(\$?\d+\.\d{2}\))?$", item_line)
            if match:
                quantity = int(match.group(1)) if match.group(1) else 1
                item_name = match.group(2).strip()
                receipt_data.append((item_name, quantity, price))
            else:
                receipt_data.append((item_line, 1, price))  # Default quantity to 1 if no match
        else:
            # Handle cases where there is a price but no corresponding item
            receipt_data.append((None, None, price))

    return receipt_data

def main():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '~/igneous-aleph-394703-550f3acb3017.json'

    client = vision.ImageAnnotatorClient()

    if len(sys.argv) < 2:
        print("Usage: python script.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    image_content = get_image_content(image_path)
    extracted_text = extract_text_from_image(client, image_content)
    receipt_data = parse_receipt_text(extracted_text)

    # Save the extracted data to a DataFrame and output to Excel
    df = pd.DataFrame(receipt_data, columns=["Item", "Quantity", "Price"])
    df.to_excel('receipt_output.xlsx', index=False)
    print("Receipt data saved to receipt_output.xlsx")

    print("Parsed Receipt Data:")
    print(df)


if __name__ == "__main__":
    main()
