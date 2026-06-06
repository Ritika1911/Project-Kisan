from google.cloud import bigquery
import requests
from datetime import datetime, timedelta
import json

PROJECT_ID = "tonal-land-467116-p9"
# Replace with your BigQuery Dataset ID (where your table is located)
DATASET_ID = "Real_Time_Price_Details"
# Replace with your BigQuery Table ID (the table you want to insert into)
TABLE_ID = "market_data"

TABLE_FULL_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

api_key = "579b464db66ec23bdd0000013777c416d69d46865b37f5929aaa058f"
api_url = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"

base_date = datetime.strptime("01/07/2025", "%d/%m/%Y")
num_days = 23

all_records = []
client = bigquery.Client(project=PROJECT_ID)
for i in range(num_days):
    current_date = base_date + timedelta(days=i)
    formatted_date = current_date.strftime("%d/%m/%Y")

    params = {
        "api-key": api_key,
        "format": "json",
        "offset": 0,
        "limit": 500000,
        "filters[State]": "Karnataka",
        # "filters[Market]": "Ramanagara",
        # "filters[Commodity]": "Tomato",
        "filters[Arrival_Date]": formatted_date
    }

    response = requests.get(api_url, params=params)
    json_body = response.json()
    
    all_records.append(json_body["records"])

    errors = client.insert_rows_json(TABLE_FULL_ID, json_body["records"])

    print(errors)
    print("Total Number of records that got inserted: ",len(json_body["records"]))

print(all_records[0])
with open('market_prices.json','w') as f:
    json.dump(all_records[:], f)

