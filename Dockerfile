# Use Python slim image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file into the container
COPY src/requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the entire src directory into the container
COPY src/ .

# Expose the application port (adjust if necessary)
EXPOSE 8002

# Set the command to run the application
CMD ["python", "social_accountability_service.py"]

