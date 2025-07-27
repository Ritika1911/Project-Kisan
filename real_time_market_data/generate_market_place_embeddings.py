import pandas as pd
import json
import io
from google.cloud import storage
import requests
from vertexai import init, rag
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

api_key = "579b464db66ec23bdd0000013777c416d69d46865b37f5929aaa058f"
api_url = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"
PROJECT_ID = "tonal-land-467116-p9"
LOCATION = "us-central1"
BUCKET_NAME = "real_time_market_data"
# TODO: Create a bucket for market place data
DISPLAY_NAME = "govtscheme"
RAG_CORPUS_NAME="projects/tonal-land-467116-p9/locations/us-central1/ragCorpora/2305843009213693952"

today = datetime.now()

yesterday = today - timedelta(days=15)
file_name = yesterday.strftime("%d-%m-%Y") + ".jsonl"
# print
formatted_date=yesterday.strftime("%d/%m/%Y")
num_days = 23
base_date = datetime.strptime("01/07/2025", "%d/%m/%Y")
 

def fetchMarketData(formatted_date):
    params = {
        "api-key": api_key,
        "format": "json",  # Or 'csv' depending on the API's supported formats
        "offset":0,
        "limit":5000,
        "filters[State]":"Karnataka",
        # "filters[Market]":"Ramanagara",
        # "filters[Commodity]":"Tomato",
        "filters[Arrival_Date]":formatted_date
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        if params["format"] == "json":
            data = response.json()
            # Process the JSON data (e.g., convert to a pandas DataFrame)
            df_daily_prices = pd.DataFrame(data['records']) # Assuming 'records' is the key containing the data
        elif params["format"] == "csv":
            data = response.content.decode('utf-8')
            df_daily_prices = pd.read_csv(io.StringIO(data))

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
    except KeyError as e:
        print(f"Error parsing JSON data: Missing key {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    text_str = ''
    records_for_jsonl = []
    for index, df_row in df_daily_prices.iterrows():
        text_content = (
            f"On {df_row['Arrival_Date']}, in {df_row['State']}, {df_row['District']} district, "
            f"at the {df_row['Market']} market, the commodity '{df_row['Commodity']}' "
            f"(Variety: {df_row['Variety']}, Grade: {df_row['Grade']}) had prices. "
            f"The minimum price was {df_row['Min_Price']} INR, "
            f"the maximum price was {df_row['Max_Price']} INR, "
            f"and the modal (most common) price was {df_row['Modal_Price']} INR."
            f" This commodity has code {df_row['Commodity_Code']}."
        )
        # --- Constructing the JSON record for JSONL file ---
        # The 'text_content' field is mandatory for Vertex AI RAG.
        # Other fields are optional metadata, useful for debugging or if the RAG service
        # ever exposes metadata filtering/retrieval (which it may do in future iterations).
        text_str += text_content+"\n"

        record = {
            "text_content": text_content,
            "state": df_row['State'],
            "district": df_row['District'],
            "market": df_row['Market'],
            "commodity": df_row['Commodity'],
            "variety": df_row['Variety'],
            "grade": df_row['Grade'],
            "arrival_date": df_row['Arrival_Date'],
            "min_price": df_row['Min_Price'],
            "max_price": df_row['Max_Price'],
            "modal_price": df_row['Modal_Price'],
            "commodity_code": df_row['Commodity_Code']
        }
        records_for_jsonl.append(record)

    # Create an in-memory JSON Lines file content
    # jsonl_buffer = io.StringIO()
    # for record in records_for_jsonl:
    #     jsonl_buffer.write(json.dumps(record, separators=(',',':')) + '\n')
    # jsonl_content = jsonl_buffer.getvalue()
    # return jsonl_content
    return text_str

def upload_to_gcs(project_id, bucket_name, file_name, content):
    try:
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name, user_project=project_id)
        blob = bucket.blob(file_name)
        blob.upload_from_string(content, content_type='application/octet-stream')
        print(f"Uploaded {file_name} to gs://{bucket_name}/{file_name}")
        return {
            "status_code": 200,
            "message": f"Successfully uploaded {file_name}",
            "gcs_path": f"gs://{bucket_name}/{file_name}"
        }
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            "status_code": 500, # Using 500 for general server-side error
            "message": f"Failed to upload {file_name}: {e}",
            "gcs_path": None
        }
    

def update_embeddings(embedding_files):
    try:
        response = rag.import_files(
                RAG_CORPUS_NAME,
                embedding_files,
                transformation_config=rag.TransformationConfig(
                    chunking_config=rag.ChunkingConfig(
                        chunk_size=512,
                        chunk_overlap=100,
                    ),
                ),
                max_embedding_requests_per_min=1000,
            )
        print(response)
    except Exception as e:
        print(" Error:", e)

def run_market_embedding_pipeline():
    try:
        # print("fetching data from market api")
        # formatted_data = fetchMarketData()
        # print("uploading file to gcp")
        # upload_result = upload_to_gcs(PROJECT_ID,BUCKET_NAME,file_name,formatted_data)
        # if upload_result["status_code"] == 200:
        #     print("GCS upload was successful!")
        #     print(f"Path: ")
        #     print("Generating embeddings")
        embedding_files = []
        for i in range(21,num_days+1):
            current_date = base_date + timedelta(days=i)
            formatted_date = current_date.strftime("%d-%m-%Y")  # using '-' instead of '/'
            text_string = fetchMarketData(formatted_date)
            upload_to_gcs(PROJECT_ID, BUCKET_NAME, f"market/{formatted_date}.md", text_string)
            embedding_files.append(f"gs://{BUCKET_NAME}/market/{formatted_date}.md")
            update_embeddings([f"gs://{BUCKET_NAME}/market/{formatted_date}.md"])
        
        # else:
        #     print(f"GCS upload failed with status code: {upload_result['status_code']}")
        #     print(f"Error message: {upload_result['message']}")
    except Exception as e:
        print(" Error:", e)

# === RUN ===
if __name__ == "__main__":
    run_market_embedding_pipeline()
