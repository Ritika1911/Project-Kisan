from google.cloud import bigquery
from google.api_core.exceptions import Conflict

# --- Configuration ---
# Replace with your Google Cloud Project ID
PROJECT_ID = "tonal-land-467116-p9"
# Replace with your BigQuery Dataset ID
DATASET_ID = "Real_Time_Price_Details"
# Replace with your desired Table ID
TABLE_ID = "market_data"

DATASET_LOCATION = "us-central1"

# Full table ID in the format: project.dataset.table


# --- Initialize BigQuery Client ---
# The client will automatically pick up credentials from your environment
# (e.g., if you've run `gcloud auth application-default login` or
# are running on a GCP service like Compute Engine with appropriate permissions).
client = bigquery.Client(project=PROJECT_ID)

# --- Construct Dataset Reference ---
# This creates a reference to the dataset within your project.
dataset_id_full = f"{PROJECT_ID}.{DATASET_ID}"
dataset = bigquery.Dataset(dataset_id_full)

# --- Set Dataset Properties (Optional but Recommended) ---
# Set the geographic location for the dataset.
dataset.location = DATASET_LOCATION
# Add a description for better organization and understanding.
dataset.description = "This dataset stores data for my new application."

# --- Define Table Schema ---
# This defines the columns and their data types for your new table.
# You can add more fields as needed.
schema = [
    bigquery.SchemaField("State", "STRING", mode="REQUIRED",
                         description="The state where the market is located."),
    bigquery.SchemaField("District", "STRING", mode="REQUIRED",
                         description="The district where the market is located."),
    bigquery.SchemaField("Market", "STRING", mode="REQUIRED",
                         description="The name of the agricultural market."),
    bigquery.SchemaField("Commodity", "STRING", mode="REQUIRED",
                         description="The type of agricultural commodity (e.g., Wheat, Rice, Tomato)."),
    bigquery.SchemaField("Variety", "STRING", mode="NULLABLE",
                         description="The specific variety of the commodity (e.g., Sona Masuri for Rice)."),
    bigquery.SchemaField("Grade", "STRING", mode="NULLABLE",
                         description="The quality grade of the commodity."),
    bigquery.SchemaField("Arrival_Date", "STRING", mode="REQUIRED",
                         description="The date when the commodity arrived at the market."),
    bigquery.SchemaField("Min_Price", "STRING", mode="REQUIRED",
                         description="The minimum price of the commodity on the arrival date."),
    bigquery.SchemaField("Max_Price", "STRING", mode="REQUIRED",
                         description="The maximum price of the commodity on the arrival date."),
    bigquery.SchemaField("Modal_Price", "STRING", mode="REQUIRED",
                         description="The most common (modal) price of the commodity on the arrival date."),
    bigquery.SchemaField("Commodity_Code", "STRING", mode="NULLABLE",
                         description="An optional unique code for the commodity."),
]


try:
    # Make the API request to create the dataset.
    dataset = client.create_dataset(dataset, timeout=30)

    TABLE_FULL_ID = f"{PROJECT_ID}.{dataset.dataset_id}.{TABLE_ID}"

    # --- Create BigQuery Table Object ---
    # Construct a full BigQuery Table object with the specified ID and schema.
    table = bigquery.Table(TABLE_FULL_ID, schema=schema)

    # --- Create the Table in BigQuery ---
    print(f"Attempting to create table: {TABLE_FULL_ID}")
    # Make the API request to create the table.
    table = client.create_table(table)
    print(f"Successfully created table '{table.table_id}' in dataset '{table.dataset_id}'.")
    print(f"Table URI: {table.full_table_id}")
except Conflict:
    print(f"Table '{TABLE_FULL_ID}' already exists. Skipping creation.")
except Exception as e:
    print(f"An error occurred: {e}")

# You can also set table properties like description, expiration, partitioning, etc.
# For example, to add a description:
# table.description = "This table stores transaction data for analysis."
# table = client.update_table(table, ["description"]) # Update the table with the new description
