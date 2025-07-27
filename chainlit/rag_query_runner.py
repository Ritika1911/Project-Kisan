from vertexai import rag, init

PROJECT_ID = "rich-brace-467014-n8"
LOCATION = "us-central1"
BUCKET_NAME = "real_time_market_data"
PREFIX = "markdown/"  
CORPUS_NAME="projects/rich-brace-467014-n8/locations/us-central1/ragCorpora/4611686018427387904"

def ask_rag(prompt: str, top_k=3, distance_threshold=0.5):
    init(project=PROJECT_ID, location=LOCATION)

    retrieval_config = rag.RagRetrievalConfig(
        top_k=top_k,
        filter=rag.Filter(vector_distance_threshold=distance_threshold),
    )

    response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(rag_corpus=CORPUS_NAME)
        ],
        text=prompt,
        rag_retrieval_config=retrieval_config,
    )
    print("Retrieved Context : ", response)
    return response

# if __name__ == "__main__":
#     prompt = "What is RAG and why it is helpful?"
#     result = ask_rag(prompt)
#     print(result)
