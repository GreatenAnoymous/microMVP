import os
import sounddevice as sd
import wave
import pyaudio
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./alpine-inkwell-383218-a4ad34b18412.json"


from google.cloud import speech

def test1():

    # Create a client object
    client = speech.SpeechClient()

    # Set the path to your audio file
    file_name = "./recording1.wav"

    # Load the audio file into memory
    with open(file_name, "rb") as audio_file:
        content = audio_file.read()

    # Set the encoding and language code
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        enable_automatic_punctuation=True,
        language_code="en-US",
    )

    # Send the transcription request to the Speech-to-Text API
    response = client.recognize(request={"config": config, "audio": audio})
    print(response)
    # print(response.results)
    # Print the transcription
    for result in response.results:
        print(result.alternatives[0].transcript)


def record_and_transcribe():
    # Create a client object for the Speech-to-Text API
    client = speech.SpeechClient()

    # Set the recording parameters
    encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
    sample_rate_hertz = 16000
    language_code = "en-US"

    # Start recording audio from the microphone
    stream = speech.RecognitionAudio(uri="output.wav")

    # Create a recognition request object with the recording parameters
    config = speech.RecognitionConfig(
        encoding=encoding, sample_rate_hertz=sample_rate_hertz, language_code=language_code
    )

    # Send the recording to the Speech-to-Text API for transcription
    response = client.recognize(config=config, audio=stream)

    # Print the transcription
    for result in response.results:
        print("Transcript: {}".format(result.alternatives[0].transcript))


def test_wav():
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = "recording1.wav"

    audio = pyaudio.PyAudio()

    # Start recording
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

    frames = []
    print("start recording!")
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    # Stop recording
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save the recorded data to a WAV file
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

# record_and_transcribe()
test_wav()
test1()