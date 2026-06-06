# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for audio processing (if needed for libraries like numpy or others)
# Check if this is truly needed; sometimes libraries handle binaries automatically.
# For now, let's include common ones, but you might remove if not necessary to reduce image size.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libsndfile1 \
#     # Add other dependencies if your Python libraries require native components
#     && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the port Chainlit runs on (default is 8000)
EXPOSE 8080

CMD ["sh", "-c", "chainlit run app.py --host 0.0.0.0 --port ${PORT}"]
