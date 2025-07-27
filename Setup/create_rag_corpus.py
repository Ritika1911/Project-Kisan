from vertexai import init, rag

PROJECT_ID = "tonal-land-467116-p9"
LOCATION = "us-central1"
DISPLAY_NAME = "govtschemes"

def setup_rag_corpus():
    try:
        init(project=PROJECT_ID, location=LOCATION)

        # Try to find an existing corpus
        rag_corpus_name = None
        for corpus in rag.list_corpora():
            if corpus.display_name == DISPLAY_NAME:
                rag_corpus_name = corpus.name
                print(f"Found existing RAG corpus: {rag_corpus_name}")
                break

        if not rag_corpus_name:
            print(f"Corpus '{DISPLAY_NAME}' not found. Creating a new one...")
            embedding_model_config = rag.RagEmbeddingModelConfig(
                vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                    publisher_model="publishers/google/models/text-embedding-005"
                )
            )
            rag_corpus = rag.create_corpus(
                display_name=DISPLAY_NAME,
                backend_config=rag.RagVectorDbConfig(
                    rag_embedding_model_config=embedding_model_config
                ),
            )
            rag_corpus_name = rag_corpus.name
            print(f"Created new RAG corpus: {rag_corpus_name}")
        
        
    except Exception as e:
        print(" Error:", e)



setup_rag_corpus()