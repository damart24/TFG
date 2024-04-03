# La función hello_world() está decorada con @app.route("/"), 
# lo que significa que esta función será llamada cuando alguien acceda 
# a la ruta raíz (/) de tu aplicación Flask.
# La función upload_wav() maneja la carga de archivos WAV 
# y está decorada con @app.route("/upload", methods=["POST"]), lo que significa que esta función
# será llamada cuando alguien envíe una solicitud POST a la ruta /upload.
# La función copyWavVersion() es llamada dentro de hello_world(), 
# y el resultado se muestra como parte de la respuesta HTML generada por esta función.
# Con esta configuración, cuando accedas a la ruta raíz de tu aplicación Flask 
# (por ejemplo, http://127.0.0.1:5000/), verás el mensaje generado por hello_world(), 
# que incluirá el resultado de copyWavVersion().

from asyncio import run
import asyncio
from flask import Flask, request
from HumePrueba import sendBytesDirectlyAsync
from HumePrueba import algoritmoEmociones


app = Flask(__name__)
print(__name__)

# Variable global para almacenar los bytes del archivo WAV
uploaded_bytes = None

@app.route("/", methods=["POST"])
def upload_wav():
    global uploaded_bytes
    # Verificar si se envió un archivo
    if 'file' not in request.files:
        return 'No se envió ningún archivo', 400
    
    file = request.files['file']

    # Verificar si no se envió ningún archivo
    if file.filename == '':
        return 'Nombre de archivo vacío', 400

    # Verificar si el archivo es un archivo WAV
    if file and file.filename.endswith('.wav'):
        # Guardar el archivo en el servidor
        # file.save(file.filename)
        # Lee los bytes del archivo
        bytesFromWav = file.read()
        # Reinicia el cursor del archivo para que pueda leerse de nuevo desde el principio
        file.seek(0)
        print(len(bytesFromWav))
        uploaded_bytes = bytesFromWav
        return 'Archivo WAV subido exitosamente ' + file.filename + ' ', 200

    return 'Tipo de archivo no soportado. Por favor, sube un archivo WAV', 400
    
@app.route("/")
def hello_world():
    global uploaded_bytes
    
    # Verificar si hay bytes de archivo cargados
    if uploaded_bytes is not None:
        print(uploaded_bytes[:44])
        print(type(uploaded_bytes))
        # Obtener el resultado de la función asíncrona
        async def get_emotions_async():
            return await sendBytesDirectlyAsync(uploaded_bytes)

        emotions_result = asyncio.run(get_emotions_async())

        # Procesar el resultado obtenido
        result = algoritmoEmociones(emotions_result)
        return f"<p>Hello, World! Result: {result}</p>"
    else:
        return "<p>Hello, World! No se ha cargado ningún archivo WAV.</p>"

