# Project Kisan: AI-Powered Agricultural Assistant

Project Kisan is an AI-powered assistant designed to provide valuable information and support to farmers. It leverages Google Cloud services, including Generative AI, Speech-to-Text, Text-to-Speech, and RAG (Retrieval Augmented Generation), to offer an interactive experience.

## Features

  * **Multilingual Support:** Interact in English or Kannada for personalized assistance.
  * **Voice Interaction:** Speak your queries and receive audio responses.
  * **Image Analysis:** Upload images of crops to identify pests/diseases and get remedies.
  * **Contextual Information:** Utilizes RAG to provide relevant and accurate farming advice.

## Setup Guide

Follow these steps to set up and run Project Kisan on your Google Cloud Platform.

### Prerequisites

  * A Google Cloud Account.
  * The `gcloud` CLI installed and authenticated.
  * Python 3.9+ installed.
  * `pip` (Python package installer).

### 1\. Google Cloud Project Setup

1.  **Create a New Google Cloud Project:**

      * Go to the [Google Cloud Console](https://console.cloud.google.com/).
      * Create a new project or select an existing one. Remember your `PROJECT_ID`.

2.  **Enable Billing:**

      * Ensure billing is enabled for your project to use all necessary Cloud APIs.

3.  **Enable Required APIs:**

      * Navigate to **APIs & Services \> Enabled APIs & services** in the Google Cloud Console.
      * Click "+ Enable APIs and Services" and enable the following APIs:
          * `Cloud Translation API`
          * `Cloud Speech-to-Text API`
          * `Cloud Text-to-Speech API`
          * `Vertex AI API`
          * `BigQuery API`
          * `Cloud Storage API`
          * `Generative Language API` (often automatically enabled with Vertex AI, but confirm)

4.  **Service Account and IAM Permissions:**

      * Navigate to **IAM & Admin \> Service Accounts**.

      * **Create a new Service Account:**

          * Give it a meaningful name (e.g., `project-kisan-sa`).
          * Click "Done" after creation.

      * **Add Permissions (Roles) to the Service Account:**

          * Locate your newly created service account (or the default App Engine service account if you intend to use that for Cloud Functions: `your-PROJECT_ID@appspot.gserviceaccount.com`).
          * Click on the service account's name, then go to the "Permissions" tab.
          * Grant the following roles:
              * `Cloud Translation API User`
              * `Cloud Speech-to-Text API User`
              * `Cloud Text-to-Speech API User`
              * `Vertex AI User`
              * `BigQuery Data Editor` (or `BigQuery Admin` if you're managing datasets)
              * `Storage Admin` (or more specific roles like `Storage Object Admin` and `Storage Bucket Reader` if preferred for least privilege)
              * `Firebase Admin SDK Administrator Service Agent` (if you plan to use Firebase Admin SDK features from Cloud Functions)
              * `Service Account User` (if this service account will impersonate others, usually not needed for basic setup)

      * **Authentication for Local Development (Optional but Recommended):**

          * While deployed Cloud Functions automatically use the attached service account, for local development or explicit credentialing, you can generate a key.
          * From your service account details page, go to the "Keys" tab and click "Add Key" -\> "Create new key" -\> "JSON". Download this JSON file.
          * Place this JSON file in your project directory (e.g., `service-account-key.json`).
          * Update your `.env` file (see Step 2) to point to this file:
            ```
            GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
            ```
          * **Important:** This `GOOGLE_APPLICATION_CREDENTIALS` variable is primarily for local testing. Deployed Cloud Functions will automatically use their attached service account.

### 2\. Configure Environment Variables

Create a `.env` file in your project's root directory and populate it with your Google Cloud project details:

```env
PROJECT_ID=your-google-cloud-project-id
BUCKET_NAME=your-gcs-bucket-name # e.g., project-kisan-data
RAG_CORPUS_NAME=projects/your-google-cloud-project-id/locations/us-central1/ragCorpora/your-rag-corpus-id
```

  * Replace `your-google-cloud-project-id` with your actual Google Cloud Project ID.
  * Choose a unique `your-gcs-bucket-name`.
  * The `RAG_CORPUS_NAME` will be generated in the next step. You'll update this value after creating your RAG corpus.

### 3\. Cloud Storage and RAG Index Setup

1.  **Navigate to the `setup` directory:**
    ```bash
    cd setup
    ```
2.  **Run the setup script:**
      * This script will create your Cloud Storage bucket and set up the RAG (Retrieval Augmented Generation) indexes.
      * **Note:** The exact command will depend on how your setup script is implemented (e.g., a Python script, shell script). Assuming a Python script named `setup.py`:
        ```bash
        python setup.py
        ```
      * **Important:** After running the setup script, it should output the `RAG_CORPUS_NAME` (e.g., `projects/YOUR_PROJECT_ID/locations/us-central1/ragCorpora/SOME_ID`). **Update your `.env` file with this exact value.**

### 4\. Local Development Environment Setup

1.  **Create a Python Virtual Environment:**
      * It's highly recommended to use a virtual environment to manage dependencies.
    <!-- end list -->
    ```bash
    python -m venv venv
    ```
2.  **Activate the Virtual Environment:**
      * **On macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```
      * **On Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 5\. Run the Application

1.  **Navigate to the `chainlit` directory:**
    ```bash
    cd chainlit
    ```
2.  **Run the Chainlit application:**
    ```bash
    chainlit run app.py -w
    ```
      * The `-w` flag enables hot-reloading, so changes to `app.py` will automatically restart the server.

Your Project Kisan application should now be running locally and accessible via your web browser (usually at `http://localhost:8000`).

-----