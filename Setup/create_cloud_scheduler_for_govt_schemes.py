import zipfile
from google.cloud import storage
from googleapiclient.discovery import build

PROJECT = "tonal-land-467116-p9"
REGION = "us-central1"
FUNCTION_NAME = "generate_embeddings_for_govt_schemes"
BUCKET_NAME = "govt_scheme_details"
ZIP_PATH = f"gs://{BUCKET_NAME}/functions/{FUNCTION_NAME}.zip"
ENTRY_POINT = "generate_embeddings_govt_schemes"
ZIP_NAME = f"{FUNCTION_NAME}.zip"
SCHEDULE = "*/15 * * * *"
JOB_NAME = "trigger_govt_schemes"

# Zip the folder
with zipfile.ZipFile("../IntegratedCode/govt_schemes/"+ZIP_NAME, "w") as zipf:
    zipf.write("../IntegratedCode/govt_schemes/main.py", arcname="main.py")
    zipf.write("../IntegratedCode/govt_schemes/requirements.txt", arcname="requirements.txt")
print("done")
# Upload to GCS
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)
blob = bucket.blob(f"functions/{ZIP_NAME}")
blob.upload_from_filename("../IntegratedCode/govt_schemes/"+ZIP_NAME)
print(f"Uploaded to: gs://{BUCKET_NAME}/functions/{ZIP_NAME}")
print("done")
service = build("cloudfunctions", "v1")
print("done")
function = {
    "name": f"projects/{PROJECT}/locations/{REGION}/functions/{FUNCTION_NAME}",
    "entryPoint": ENTRY_POINT,
    "runtime": "python311",
    "availableMemoryMb": 1024,
    "httpsTrigger": {},  # HTTP trigger
    "sourceArchiveUrl": ZIP_PATH
}

request = service.projects().locations().functions().create(
    location=f"projects/{PROJECT}/locations/{REGION}",
    body=function
)
print("done")
response = request.execute()
print("Deployment started:", response["name"])
print("done")
FUNCTION_URL = f"https://{REGION}-{PROJECT}.cloudfunctions.net/{FUNCTION_NAME}"

service = build("cloudscheduler", "v1")

job_body = {
    "name": f"projects/{PROJECT}/locations/{REGION}/jobs/{JOB_NAME}",
    "schedule": SCHEDULE,
    "timeZone": "Asia/Kolkata",
    "httpTarget": {
        "uri": FUNCTION_URL,
        "httpMethod": "GET",
        "oidcToken": {
            "serviceAccountEmail": f"{PROJECT}@appspot.gserviceaccount.com"
        }
    }
}
print("done")

response = service.projects().locations().jobs().create(
    parent=f"projects/{PROJECT}/locations/{REGION}",
    body=job_body
).execute()

print("Scheduler job created:", response["name"])
