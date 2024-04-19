import base64
import io
import os
import asyncio
import pprint
import wave
import numpy as np

from hume import HumeStreamClient
from hume.models.config import ProsodyConfig
import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import find_peaks
import parselmouth
import soundfile as sf


beginTime = []
endTime = []
# Obtengo los bytes de un wav a partir de su nombre, en la ubicación en la que está el archivo de python
def getBytesFromWav(wavName):
    # Obtener la ruta del directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Conseguimos el path junto con el nombre de donde sacaremos el WAV
    WAVE_ORIGINAL_FILENAME = wavName
    originalVersion_path = os.path.join(script_dir, WAVE_ORIGINAL_FILENAME)

    # Leemos los bytes del archivo WAV original
    # Abrir el archivo WAV en modo binario
    with open(originalVersion_path, 'rb') as f:
        # Leer todos los bytes del archivo
        wav_bytes = f.read()

    return wav_bytes

# Función para ordenar las emociones en cada categoría
def sort_emotions_by_category(emotions_by_category, emotions_dict, beginTime, endTime):
    # Verificar si hay una advertencia de que no se detectó ningún discurso
    if 'prosody' in emotions_dict and 'warning' in emotions_dict['prosody'] and emotions_dict['prosody']['warning'] == 'No speech detected.':
        result = {category: 0 for category in emotions_by_category}
        result['timeBeginMark'] = beginTime
        result['timeEndMark'] = endTime
        return result
    
    emotions_list = emotions_dict['prosody']['predictions'][0]['emotions']
    
    # Inicializar un diccionario para almacenar la suma de puntuaciones por categoría
    summed_emotions = {category: 0 for category in emotions_by_category}  
    
    for emotion in emotions_list:
        for category, category_emotions in emotions_by_category.items():
            if any(substring in emotion['name'] for substring in category_emotions):
                summed_emotions[category] += emotion['score']
    
    summed_emotions['timeBeginMark'] = emotions_dict['prosody']['predictions'][0]['time']['begin']
    summed_emotions['timeEndMark'] = emotions_dict['prosody']['predictions'][0]['time']['end']

    return summed_emotions


def algoritmoEmocionesFinal(emotionsList):
    # Definir el diccionario de emociones por categoría
    emotions_by_category = {
        'Felicidad': ['Admiration', 'Amusement', 'Contentment', 'Triumph', 'Determination',
                    'Adoration', 'Joy', 'Sympathy', 'Love', 'Excitement', 'Desire',
                    'Interest', 'Satisfaction', 'Romance', 'Surprise (positive)',
                    'Concentration', 'Ecstasy'],
        'Tristeza': ['Boredom', 'Distress', 'Disappointment', 'Tiredness', 'Sadness',
                     'Calmness', 'Nostalgia', 'Relief', 'Surprise (negative)'],
        'Miedo': ['Anxiety', 'Confusion', 'Tiredness', 'Awe', 'Embarrassment', 'Shame',
                'Doubt', 'Horror', 'Fear', 'Confusion', 'Empathic Pain', 'Contemplation'],
        'Asco': ['Awkwardness', 'Disgust', 'Craving', 'Pride', 'Aesthetic Appreciation'],
        'Enfado': ['Guilt', 'Annoyance', 'Anger', 'Contempt', 'Envy', 'Pain', 'Craving', 'Entrancement']
    }

    emotionsList2 = []
    for i, emotion in enumerate(emotionsList):
        sorted_emotions_by_category = sort_emotions_by_category(emotions_by_category, emotion, beginTime[i], endTime[i])
        emotionsList2.append(sorted_emotions_by_category)
    # Ordenar las emociones por categoría
    
    return emotionsList2

# Convierte los bytes recibidos en bytes en formato 64 bytes
async def convertBytesto64(wav_bytes):
    wav_bytes64 = base64.b64encode(wav_bytes) 
    return wav_bytes64

# Crea un wav a partir de los bytes y devuelve nchannels, samwidth, framerate y numFrames
def obtener_caracteristicas_wav_desde_bytes(bytes_wav):
    # Crear un objeto de archivo WAV a partir de los bytes
    wav_file = wave.open(io.BytesIO(bytes_wav))

    # Obtener características del archivo WAV
    n_channels = wav_file.getnchannels()
    sampWidth = wav_file.getsampwidth()
    frameRate = wav_file.getframerate()
    numFrames = wav_file.getnframes()

    # Cerrar el archivo WAV
    wav_file.close()

    return n_channels, sampWidth, frameRate, numFrames

# Método que divide el audio en fragmentos de 5 segundos como mucho para poderles enviar a HumeAI
# Tiene una limitación la librería por eso se cortan en fragmentos
def dividir_audio(bytesFromWav):
    segmentos = []

    # Agregar los primeros 44 bytes a cada segmento
    header_bytes = bytesFromWav[:44]

    nChannels, sampWidth, framerate, num_frames = obtener_caracteristicas_wav_desde_bytes(bytesFromWav)
    
    duration = num_frames / framerate  # Duración total del audio en segundos
        
    time = 5
    # Calcular el número de segmentos
    #Mirar para parametrizarlo
    num_segmentos = int(duration / time) + 1
    # Dividir el audio en segmentos de máximo 5 segundos
    inicio_frame = 0

    inicio_tiempo = 0
    fin_tiempo = time
    for i in range(num_segmentos):
        fin_frame = min(inicio_frame + time * framerate * nChannels * sampWidth, len(bytesFromWav))
        segmento = header_bytes + bytesFromWav[inicio_frame:fin_frame]
        segmentos.append(segmento)
        beginTime.append(inicio_tiempo)
        endTime.append(fin_tiempo)
        inicio_tiempo += time
        fin_tiempo += time
        inicio_frame = fin_frame
        # copyWavFromBytes(segmento, "Holaaa" + str(i) + ".wav")
    return segmentos

###Métodos de conseguir características

def getCharacteristics(segment):
    with io.BytesIO(segment) as f:
        audio_data, framerate = sf.read(f)
        
    # Convierte los datos de audio a un objeto de sonido de Parselmouth
    sound = parselmouth.Sound(audio_data.T, sampling_frequency=framerate)
    # Extrae el pitch (tono) utilizando el algoritmo de "To Pitch (cc)"
    pitch = sound.to_pitch()
    framesWithVoices = pitch.count_voiced_frames()
    framesWithoutVoices = pitch.n_frames
    intensity =  sound.get_intensity()
    pitch_values = pitch.selected_array['frequency']

    # Filtrar los valores de pitch que no sean 0
    pitch_values = [x for x in pitch_values if x != 0]
    if(len(pitch_values) > 0):
        # Calcula el promedio (average) del pitch
        average_pitch = sum(pitch_values) / len(pitch_values)

        # Obtiene el máximo (maximum) del pitch
        maximum_pitch = max(pitch_values)

        # Obtiene el mínimo (minimum) del pitch
        minimum_pitch = min(pitch_values)

        # Calcula la desviación estándar (standard deviation) del pitch
        mean = sum(pitch_values) / len(pitch_values)
        variance = sum((x - mean) ** 2 for x in pitch_values) / len(pitch_values)
        standardDesviationPitch = variance ** 0.5

        
        return intensity, framesWithVoices, framesWithoutVoices, average_pitch, maximum_pitch, minimum_pitch, standardDesviationPitch
    else:
        return 0, 0, 0, 0, 0, 0, 0

# Método al que se le pasa el wav segmentado y analizada y devuelve un número de listas
# con las emociones, el número es igual al número de segmentos enviados
async def sendBytesDirectlyAsyncSegmentado(bytesSegments):
    segments64 = []

    for segment in bytesSegments:
        encoded_segment = base64.b64encode(segment)
        segments64.append(encoded_segment)

    emotionsList = []
    # Se ejecuta el resultado final enviándolo y analizando el audio
    client = HumeStreamClient("LIoNt2anG1QMGhnVsNICTIIQqHwotID6hc8C7SFinTGi2ccu")
    config = ProsodyConfig()
    async with client.connect([config]) as socket:
        for segmentFinal in segments64:            
            result = await socket.send_bytes(segmentFinal)
            emotionsList.append(result)
        
        return emotionsList


# script_dir = os.path.dirname(os.path.abspath(__file__))
# file_path = "1000Cosas1.wav"
# originalVersion_path = os.path.join(script_dir, file_path)
# bytesToSend =  getBytesFromWav(originalVersion_path)

# segmentos = dividir_audio(bytesToSend)

# emotions = asyncio.run(sendBytesDirectlyAsyncSegmentado(segmentos))
# algoritmoEmocionesFinal(emotions)

# print(" ")
# for segment in segmentos:
#     intensity, framesWithVoices, framesWithoutVoices, averagePitch, maximumPitch, minimumPitch, standardDesviationPitch = getCharacteristics(segment)
#     # Imprime cada elemento en una línea separada
#     print("Intensidad:", intensity)
#     print("Frames hablados:", framesWithVoices)
#     print("Frames totales:", framesWithoutVoices)
#     print("Media del pitch:", averagePitch)
#     print("Pitch máximo:", maximumPitch)
#     print("Pitch mínimo:", minimumPitch)
#     print("Desviación estándar:", standardDesviationPitch)
#     print(" ")
