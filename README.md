
# 📊 Dashboard de Inversiones

Este proyecto permite visualizar y registrar movimientos de inversión usando Streamlit, SQLite y un dashboard interactivo.

---

## 🚀 Arrancar el entorno de desarrollo

### 🔧 Opción 1: Usar entorno virtual de Python (recomendado en desarrollo)

```bash
# Crear entorno virtual
python -m venv venv

# Activarlo (Windows)
venv\Scripts\activate

# O si usas conda
conda activate cartera_inversiones

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
streamlit run app.py







### 🐳 Opción 2: Usar Docker (alternativa)

# Construir y arrancar el contenedor
docker-compose up --build

# Acceder a la app en el navegador:
http://localhost:8501



Si necesitas reconstruir la base de datos cartera_inversiones.db desde los ficheros transacciones.xlsx y activos_para_etiquetar.xlsx, ejecuta:

# Con entorno virtual activado
python regenerar_base_datos.py

⚠️ Este script reemplaza completamente la base de datos con los datos del Excel.



🔄 Actualizar Excel desde la base de datos
Si has hecho cambios en la base de datos y quieres reflejar esos cambios en el Excel, ejecuta:


python exportar_base_datos_a_excel.py
Esto genera o sobrescribe los ficheros:

transacciones.xlsx

activos_para_etiquetar.xlsx






