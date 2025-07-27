from google.cloud import storage
import os

PROJECT_ID = "tonal-land-467116-p9"
BUCKET_NAME = "real_time_market_data"
LOCATION = "us-central1"

def create_bucket():
    """Create a new GCS bucket in a given project and location."""
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    new_bucket = storage_client.create_bucket(bucket,location=LOCATION)
    print(f"Bucket '{new_bucket.name}' created in location '{new_bucket.location}'.")

create_bucket()