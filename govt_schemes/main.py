import requests
from bs4 import BeautifulSoup
import os
from google.cloud import storage
from google.cloud import translate_v3
from llama_index.readers.file.unstructured import UnstructuredReader
from vertexai import rag
import tempfile
from io import BytesIO

PROJECT_ID = "tonal-land-467116-p9"
BUCKET_NAME = "govt_scheme_details"
LOCATION = "us-central1"
RAG_CORPUS_ID = "2305843009213693952"
RAG_CORPUS_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{RAG_CORPUS_ID}"

translate_client = translate_v3.TranslationServiceClient()
storage_client = storage.Client(project=PROJECT_ID)

def upload_to_gcs(file_name, content, content_type):
    try:
        bucket = storage_client.bucket(BUCKET_NAME, user_project=PROJECT_ID)
        blob = bucket.blob(file_name)
        blob.upload_from_string(content, content_type=content_type)
        return {
            "status_code": 200,
            "message": f"Successfully uploaded {file_name}",
            "gcs_path": f"gs://{BUCKET_NAME}/{file_name}"
        }
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            "status_code": 500, # Using 500 for general server-side error
            "message": f"Failed to upload {file_name}: {e}",
            "gcs_path": None
        }

def translate_filename(filename):
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    response = translate_client.translate_text(contents=[filename],parent = parent, source_language_code="kn", target_language_code="en")
    return response.translations[0].translated_text

def translate_document_and_upload(
    input_folder_path:str,
    output_folder_path: str
) -> None:
    
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"

    # Read the content of the local document
    input_bucket = storage_client.bucket(BUCKET_NAME)
    input_blob = input_bucket.blob(input_folder_path)
    document_content = input_blob.download_as_bytes()

    document_input_config = translate_v3.DocumentInputConfig(
        content=document_content,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # for .docx
    )

    request = translate_v3.TranslateDocumentRequest(
        parent=parent,
        document_input_config=document_input_config,
        source_language_code="kn",
        target_language_code="en",
    )

    response = translate_client.translate_document(request=request)

    print(f"Translation complete. Saved translated document to: {output_folder_path}")

    upload_to_gcs(output_folder_path,response.document_translation.byte_stream_outputs[0], "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

def convert_to_markdown_and_upload(input_folder_path, output_folder_path, translated_filename):

    reader = UnstructuredReader()

    # Read the content of the local document
    input_bucket = storage_client.bucket(BUCKET_NAME)
    input_blob = input_bucket.blob(input_folder_path)

    file_bytes = input_blob.download_as_bytes()
    # Write to a temp file and parse
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as temp_file:
        temp_file.write(file_bytes)
        temp_file.flush()

        docs = reader.load_data(file=temp_file.name)
        content = docs[0].text
    # docs = reader.load_data(file=BytesIO(file_bytes), file_name=translated_filename)
    # content = docs[0].text

    upload_to_gcs(output_folder_path,content, "application/octet-stream")

def generate_embeddings(embedding_files):
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


def generate_embeddings_govt_schemes():
    url="https://raitamitra.karnataka.gov.in/english"
    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    links = soup.find_all('a')
    scheme_details = []

    for link in links:
        if link.get('href') and "Scheme" in link.get('href') and "Details" in link.get('href'):
            scheme_details.append(link.get('href'))
        
    for scheme in scheme_details:
        response = requests.get(scheme.strip())

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')

        extensions = ('.docx')
        embedding_files = []
        for link in links:
            href = link.get('href')
            if href and href.endswith(extensions):
                file_url = href if href.startswith("http") else requests.compat.urljoin(url, href)
                filename = os.path.basename(file_url)

                file_response = requests.get(file_url)

                if file_response.status_code == 200:
                    upload_to_gcs("kannada/"+filename,file_response.content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    translated_filename = translate_filename(filename)
                    blobs = list(storage_client.list_blobs(BUCKET_NAME, prefix="english/"))
                    blob_names = [blob.name for blob in blobs]
                    print(blob_names)
                    if "english/"+translated_filename not in blob_names:
                        translate_document_and_upload("kannada/"+filename,"english/"+translated_filename)
                    blobs = list(storage_client.list_blobs(BUCKET_NAME, prefix="markdown/"))
                    blob_names = [blob.name for blob in blobs]
                    if "markdown/"+os.path.splitext(translated_filename)[0]+".md" not in blob_names:
                        convert_to_markdown_and_upload("english/"+translated_filename, "markdown/"+os.path.splitext(translated_filename)[0]+".md", translated_filename)
                    
                    generate_embeddings([f"gs://{BUCKET_NAME}/markdown/"+os.path.splitext(translated_filename)[0]+".md"])
                    embedding_files.append(f"gs://{BUCKET_NAME}/markdown/"+os.path.splitext(translated_filename)[0]+".md")

                else:
                    print("Error with file:"+file_url)
        # generate_embeddings(embedding_files)

# generate_embeddings_govt_schemes()