import assemblyai as aai
import openai
import elevenlabs
from queue import Queue
import os
from dotenv import load_dotenv
import threading

load_dotenv(dotenv_path='voicebotkeys.env')
#set up API keys
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")
elevenlabs.set_api_key(os.getenv("ELEVENLABS_API_KEY"))


transcript_queue = Queue()

def on_data(transcript: aai.RealtimeTranscript):
    if not transcript.text:
        return
    if isinstance(transcript, aai.RealtimeFinalTranscript):
        transcript_queue.put(transcript.text + '')
        print("User:", transcript.text, end="\r\n")
    else:
        print(transcript.text, end="\r")

def on_error(error: aai.RealtimeError):
    print("An error occured:", error)

def handle_conversation():
    # Set up the transcriber and microphone stream outside of the loop
    transcriber = aai.RealtimeTranscriber(
        on_data=on_data,
        on_error=on_error,
        sample_rate=44_100,
    )
    transcriber.connect()
    microphone_stream = aai.extras.MicrophoneStream()

    def start_transcription_stream():
        # This function will run in a separate thread to handle streaming.
        transcriber.stream(microphone_stream)

    # Start the transcription stream in a separate thread
    transcription_thread = threading.Thread(target=start_transcription_stream)
    transcription_thread.start()

    try:
        while True:
            # Retrieve data from queue
            transcript_result = transcript_queue.get()

            # Send the transcript to OpenAI for response generation
            response = openai.ChatCompletion.create(
                model='gpt-4',
                messages=[
                    {"role": "system", "content": 'You are a highly skilled AI, answer the questions given within a maximum of 750 characters.'},
                    {"role": "user", "content": transcript_result}
                ]
            )

            # Before playing the audio, mute or stop the microphone stream
            #this is conceptually when it should stop listening as it speaks
            transcriber.close()
            # Extract the text response from OpenAI's response
            text = response['choices'][0]['message']['content']

            # Convert the response to audio and play it
            audio = elevenlabs.generate(
                text=text,
                voice="Daniel" # or any voice of your choice
            )

            print("\nAI:", text, end="\r\n")

            elevenlabs.play(audio)

            # After playing the audio resumes the microphone stream
            #this is conceptually when it should start listening again after Ai spoke

    finally:
        # When everything is done, this closes the stream and transcriber
        microphone_stream.close()
        transcriber.close()
        transcription_thread.join()

handle_conversation()

#hard to get it to detirmine when we are done speaking must fix