import google.generativeai as genai
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
import chainlit as cl
from PIL import Image
from google.cloud import translate_v3
import io
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage # Import AIMessage
import base64
import numpy as np
import wave # Import wave module for audio processing
from google.cloud import speech
from google.cloud import texttospeech
import asyncio # For asyncio.sleep
from langchain_core.messages import SystemMessage
from vertexai.generative_models import GenerativeModel, Tool
from vertexai import rag
from rag_query_runner import ask_rag
load_dotenv()

SILENCE_THRESHOLD = 25 # Increased from 40. Start here, then tune.
SILENCE_TIMEOUT_MS = 5000 # Milliseconds of silence to consider the turn finished (2 seconds)
CHUNK_DURATION_MS = 100 # Assuming each chunk is roughly 100ms based on typical audio input
RAG_CORPUS_NAME="projects/rich-brace-467014-n8/locations/us-central1/ragCorpora/4611686018427387904"
project_id = "rich-brace-467014-n8"
location = "us-central1"
rag_retrieval_config = rag.RagRetrievalConfig(
    top_k=3,  # Optional
    filter=rag.Filter(vector_distance_threshold=0.5),  # Optional
)
parent = f"projects/{project_id}/locations/{location}"
translation_client = translate_v3.TranslationServiceClient()

rag_retrieval_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=RAG_CORPUS_NAME
                )
            ],
            rag_retrieval_config=rag_retrieval_config,
        ),
    )
)

rag_model = GenerativeModel(
    model_name="gemini-2.0-flash-001", tools=[rag_retrieval_tool]
)

def image_to_data_url(image: Image.Image, format="JPEG") -> dict:
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/{format.lower()};base64,{encoded}"
        }
    }

def compute_rms(chunk_data):
    # Convert bytes to 16-bit numpy array
    samples = np.frombuffer(chunk_data, dtype=np.int16)
    # print("samples length:", len(samples)) # Debug: Check sample array length
    if len(samples) == 0: # Handle empty chunks
        return 0
    rms = np.sqrt(np.mean(samples**2))
    return int(rms)

@cl.on_chat_start
async def on_chat_start():
    text_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", convert_system_message_to_human=True, stream=True, max_output_tokens=256) # Stream for text_model

    vision_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", convert_system_message_to_human=True, stream=True, max_output_tokens=256) # Use pro for vision for better quality

    text_prompt = ChatPromptTemplate.from_messages([
        ("system", "You're a very knowledgeable assistant to farmers who provides suggestions to farming questions. Relevant background context:\n{context}\n\n. "),
        ("human", "{question}"),
    ])

    text_runnable = text_prompt | text_model | StrOutputParser()
    vision_runnable = vision_model | StrOutputParser() # The model directly, as HumanMessage will contain image + text
    
    cl.user_session.set("text_runnable", text_runnable)
    cl.user_session.set("vision_runnable", vision_runnable)

    # Initialize audio processing state
    cl.user_session.set("message_history", [])
    cl.user_session.set("is_recording", False)
    cl.user_session.set("silent_duration_ms", 0)
    cl.user_session.set("audio_chunks", [])
    cl.user_session.set("silence_task", None) # To store the background task for silence timeout
    cl.user_session.set("image_element", None)
    cl.user_session.set("last_audio_transcription",None)

    # Inform the user about file upload capability
    await cl.Message(
        content="Welcome to Project Kisan! Press `p` to talk or upload an image.",
        author="assistant"
    ).send()

    msg = await cl.Message(content="🌐 Which language do you prefer?").send()

    # Step 2: Send language options as actions linked to the message
    await cl.Action(
        name="handle_language_choice",
        value="en",
        label="🇬🇧 English",
        payload={}
    ).send(for_id=msg.id)

    await cl.Action(
        name="handle_language_choice",
        value="kn",
        label="🇮🇳 ಕನ್ನಡ",
        payload={}
    ).send(for_id=msg.id)

@cl.action_callback("handle_language_choice")
async def handle_language_choice(action):
    # Step 1: Store the chosen language in the session
    print("act ", action)
    if action.label=="🇬🇧 English":
        cl.user_session.set("lang_code","en-US")
        cl.user_session.set("lang_voice","en-US-Standard-B")
    else:
        cl.user_session.set("lang_code","kn-IN")
        cl.user_session.set("lang_voice","kn-IN-Standard-A")

    # Step 2: Confirm the selection to the user
    if action.label == "🇬🇧 English":
        await generate_output_audio("Welcome to Project Kisan! Press `p` to talk or upload an image.You selected English.")
    elif action.label == "🇮🇳 ಕನ್ನಡ":
        await generate_output_audio("ಪ್ರಾಜೆಕ್ಟ್ ಕಿಸಾನ್ ಗೆ ಸುಸ್ವಾಗತ! ಮಾತನಾಡಲು ಅಥವಾ ಚಿತ್ರವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಲು `p` ಒತ್ತಿರಿ. ನೀವು ಕನ್ನಡ ಆಯ್ಕೆಮಾಡಿದ್ದೀರಿ."  )

@cl.on_message
async def on_message(message: cl.Message):
    text_runnable = cl.user_session.get("text_runnable")
    vision_runnable = cl.user_session.get("vision_runnable")


    msg = cl.Message(content="", author="human")
    last_audio_transcription = cl.user_session.get("last_audio_transcription")
    if message.elements:    
        for element in message.elements:
            print(f"DEBUG: Type of element: {type(element)}")
            print("type ", element.mime)
            
            if isinstance(element, cl.Image) or (isinstance(element, cl.File) and element.mime.startswith("image/")):
                print("in image")
                try:
                    if element.path:
                        image = Image.open(element.path)
                    else:
                        image_bytes = element.content
                        try:
                            image = Image.open(io.BytesIO(image_bytes))
                            cl.user_session.set("image_element", image)
                            print("Image opened successfully from raw bytes.")
                        except Exception:
                            print("Failed to open as raw bytes, attempting base64 decode...")
                            image_bytes_decoded = base64.b64decode(element.content)
                            image = Image.open(io.BytesIO(image_bytes_decoded))
                            print("Image opened successfully from base64 decoded bytes.")

                    image_dict = image_to_data_url(image) # Convert image to Gemini-compatible format
                    human_message_content = []
                    if last_audio_transcription:
                        print("processing image with audio")
                        transcripted = await process_audio()
                        translated=transcripted
                        print("transcripted ", transcripted)
                        if cl.user_session.get("lang_code") == "kn-IN":
                            translated = translate_kn_en(transcripted)
                        human_message_content.append(f'Regarding the following image, the user previously said: "{translated}"')
                        cl.user_session.set("last_audio_transcription", None)
                    else:
                        if message.content: 
                            human_message_content.append(message.content)
                    human_message_content.append("Identify the pest or disease, and provide clear, actionable advice on locally available and affordable remedies")
                    human_message_content.append(image_dict)
                    messages = []
                    messages.append(HumanMessage(content=human_message_content))
                    final_img_resp=""
                    async for chunk in vision_runnable.astream(
                        messages, # Pass a list of messages for history or single message
                        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()])
                    ):
                        token = str(chunk)
                        final_img_resp+=token
                    await send_final_resp(final_img_resp)
                    cl.user_session.set("imnage_element",None)
                except Exception as e:
                    await msg.stream_token(f"Failed to process image: {e}")
                    print(f"Error processing image: {e}")
                
            elif isinstance(element, cl.File) and element.mime in ["application/pdf", "text/plain", "text/csv"]:
                await msg.stream_token(f"Processing {element.name} ({element.mime})...")
                await msg.stream_token(f"\nFile {element.name} received. Processing of {element.mime} files is not yet implemented.")
            else:
                await msg.stream_token(f"Unsupported file type: {element.mime}")
    else:
        if last_audio_transcription:
            print("processing just audio")
            transcripted = await process_audio()
            print("resp transcripted ", transcripted)
            answer = await generate_text_answer(transcripted)
            await send_final_resp(answer)
            cl.user_session.set("last_audio_transcription", None)
        else:
            print("processing text")
            translated=message.content
            if cl.user_session.get("lang_code")=='kn-IN':
                translated=translate_kn_en(message.content)
            context = ask_rag(translated)
            print("content: ", context)
            inputs = {
                "context": context,
                "question": translated
            }
            final_text_resp=""
            async for chunk in text_runnable.astream(
                inputs,
                config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
            ):
                token=str(chunk)
                final_text_resp+=token
            await send_final_resp(final_text_resp)
    print("sending")
    # await msg.send()

def translate_kn_en(text: str):
    translated = translation_client.translate_text(contents=[text],parent = parent, source_language_code="kn", target_language_code="en")
    print("translated : ", text ," to english ", translated.translations[0].translated_text)
    return translated.translations[0].translated_text

def translate_en_kn(text: str):
    translated = translation_client.translate_text(contents=[text],parent = parent, source_language_code="en", target_language_code="kn")
    print("translated : ", text ," to Kannada ", translated.translations[0].translated_text)
    return translated.translations[0].translated_text

async def send_final_resp(response: str):
    
        display_translated=response
        if cl.user_session.get("lang_code") == "kn-IN":
            display_translated = translate_en_kn(response)
            print("translated final resp to kannada: ", display_translated)
        # await cl.Message(content=display_translated).send()
        await generate_output_audio(display_translated)



@cl.step(type="tool", name="Transcribing Audio")
async def transcribe_audio_buffer(audio_buffer: bytes) -> str: # Return type is str (transcript)
    client = speech.SpeechClient()
    print("transcribe ")
    audio = speech.RecognitionAudio(content=audio_buffer)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, # WAV (PCM)
        sample_rate_hertz=24000, # Match what you set in the WAV file
        language_code=cl.user_session.get("lang_code"),
    )

    response = client.recognize(config=config, audio=audio)

    transcript = ""
    for result in response.results:
        transcript += result.alternatives[0].transcript + " "

    transcript = transcript.strip()
    print("Transcript:", transcript)
    return transcript


@cl.step(type="tool", name="Text to Speech")
async def text_to_speech(text: str, mime_type: str = "audio/mpeg"):
    """Convert text to speech using Google Cloud TTS and return an audio buffer."""

    # 1. Set up client
    client = texttospeech.TextToSpeechClient()

    # 2. Prepare input text
    input_text = texttospeech.SynthesisInput(text=text)

    # 3. Select voice
    voice = texttospeech.VoiceSelectionParams(
        language_code=cl.user_session.get("lang_code"), # Customize if needed
        name=cl.user_session.get("lang_voice")
    )

    # 4. Determine output format based on MIME type
    audio_encoding_map = {
        "audio/mpeg": texttospeech.AudioEncoding.MP3,
        "audio/wav": texttospeech.AudioEncoding.LINEAR16,
        "audio/ogg": texttospeech.AudioEncoding.OGG_OPUS,
    }

    encoding = audio_encoding_map.get(mime_type, texttospeech.AudioEncoding.MP3)

    audio_config = texttospeech.AudioConfig(audio_encoding=encoding)

    # 5. Synthesize the speech
    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config,
    )

    # 6. Write to buffer
    buffer = io.BytesIO(response.audio_content)
    extension = mime_type.split("/")[-1]
    buffer.name = f"output_audio.{extension}"
    buffer.seek(0)

    return buffer.name, buffer.read()


@cl.step(type="tool", name="Generating Response")
async def generate_text_answer(transcription):
    message_history = cl.user_session.get("message_history", [])
    print("transcription received: ", transcription)
    translated=transcription
    if cl.user_session.get("lang_code")=='kn-IN':
        translated=translate_kn_en(transcription)
    context = ask_rag(translated)
    message_history.append(HumanMessage(content=translated))

    model = cl.user_session.get("text_runnable") # Use the pre-initialized runnable
    response = await model.ainvoke({"question": translated, "context": context}) # Invoke the runnable correctly
    # Store back in session
    cl.user_session.set("message_history", message_history)

    return response


@cl.on_audio_start
async def on_audio_start():
    print("Audio recording started.")
    cl.user_session.set("is_recording", True)
    cl.user_session.set("silent_duration_ms", 0)
    cl.user_session.set("audio_chunks", [])
    # Cancel any previous silence timeout task if it's still running
    if cl.user_session.get("silence_task"):
        cl.user_session.get("silence_task").cancel()
        cl.user_session.set("silence_task", None)
    return True


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    is_recording = cl.user_session.get("is_recording")
    if not is_recording:
        print("Not recording, ignoring chunk.")
        return # Do not process if recording is supposed to be off

    audio_chunks = cl.user_session.get("audio_chunks")
    audio_chunk_np = np.frombuffer(chunk.data, dtype=np.int16)
    audio_chunks.append(audio_chunk_np)
    cl.user_session.set("audio_chunks", audio_chunks) # Update the session

    # Compute the RMS (root mean square) energy of the audio chunk
    audio_energy = compute_rms(chunk.data)

    print(f"DEBUG: Current audio energy: {audio_energy}")

    if audio_energy < SILENCE_THRESHOLD:
        # Audio is considered silent
        print(f"DEBUG: User silent, energy: {audio_energy}")
        silent_duration_ms = cl.user_session.get("silent_duration_ms") + CHUNK_DURATION_MS
        cl.user_session.set("silent_duration_ms", silent_duration_ms)

        # If silence timeout task is not running, start it
        if cl.user_session.get("silence_task") is None:
            print(f"DEBUG: Starting silence timeout task for {SILENCE_TIMEOUT_MS} ms.")
            silence_task = asyncio.create_task(
                _silence_timeout_handler()
            )
            cl.user_session.set("silence_task", silence_task)

    else:
        # Audio is not silent, reset silence timer and cancel timeout task
        print(f"DEBUG: User speaking, energy: {audio_energy}")
        cl.user_session.set("silent_duration_ms", 0)
        # Cancel the silence timeout task if it was running
        if cl.user_session.get("silence_task"):
            print("DEBUG: Cancelling silence timeout task.")
            cl.user_session.get("silence_task").cancel()
            cl.user_session.set("silence_task", None)


async def _silence_timeout_handler():
    """Handles the silence timeout to trigger audio processing."""
    try:
        await asyncio.sleep(SILENCE_TIMEOUT_MS / 1000.0) # Convert ms to seconds
        # If we reach here, silence timeout has been met
        print("DEBUG: Silence timeout reached.")
        # Ensure recording is stopped programmatically
        cl.user_session.set("is_recording", False)
        cl.user_session.set("silent_duration_ms", 0) # Reset silence duration
        cl.user_session.set("last_audio_transcription", True)
        # await process_audio()
    except asyncio.CancelledError:
        print("DEBUG: Silence timeout task cancelled.")
        pass # Task was cancelled because user started speaking again


@cl.on_audio_end
async def on_audio_end():
    # This function is called when the user stops recording (e.g., releases 'p')
    print("Audio recording ended by user.")
    cl.user_session.set("is_recording", False)
    cl.user_session.set("silent_duration_ms", 0) # Reset silence duration
    # Cancel any running silence timeout task
    if cl.user_session.get("silence_task"):
        cl.user_session.get("silence_task").cancel()
        cl.user_session.set("silence_task", None)
    cl.user_session.set("last_audio_transcription", True)
    # await process_audio()


async def process_audio():
    # Get the audio buffer from the session
    print("In transcription")
    audio_chunks = cl.user_session.get("audio_chunks")
    
    if not audio_chunks:
        # await cl.Message(content="I didn't hear anything. Please try speaking again.", author="assistant").send()
        return None

    # Concatenate all chunks
    concatenated = np.concatenate(audio_chunks)

    # Create an in-memory binary stream
    wav_buffer = io.BytesIO()

    # Create WAV file with proper parameters
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(24000)  # sample rate (24kHz PCM)
        wav_file.writeframes(concatenated.tobytes())

    # Reset buffer position
    wav_buffer.seek(0)

    frames = len(concatenated)
    rate = 24000 # This is fixed by your WAV settings

    duration = frames / float(rate)
    
    # Reset audio_chunks in session after processing
    cl.user_session.set("audio_chunks", [])

    if duration < 1.0: # Shorter threshold for minimum audio duration (e.g., 1 second)
        print(f"The audio is too short ({duration:.2f}s), please try again.")
        await cl.Message(content="The audio was too short. Please speak for a bit longer.", author="assistant").send()
        return None

    audio_buffer = wav_buffer.getvalue()

    input_audio_el = cl.Audio(content=audio_buffer, mime="audio/wav")
    
    
    transcription = await transcribe_audio_buffer(audio_buffer)

    
    # Only proceed if transcription is not empty or just whitespace
    if not transcription.strip():
        print("Transcription is empty, not generating response.")
        await cl.Message(content="I didn't catch that. Could you please try again?", author="assistant").send()
        return None
    print("post_transcription : ", transcription)
    await cl.Message(
        author="human",
        type="user_message",
        content=transcription,
        elements=[input_audio_el],
    ).send()

    return transcription


async def generate_output_audio(answer):
    output_name, output_audio = await text_to_speech(answer, "audio/wav")

    output_audio_el = cl.Audio(
        auto_play=True,
        mime="audio/wav",
        content=output_audio,
    )

    await cl.Message(content=answer, elements=[output_audio_el], author="human").send()
