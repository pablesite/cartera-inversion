# Usa una imagen ligera de Python
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos al contenedor
COPY . .

# Instala las dependencias
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expone el puerto que usará Streamlit
EXPOSE 8501

# Comando para arrancar la aplicación
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]