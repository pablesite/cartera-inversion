import requests

print("Obteniendo tipo de cambio USD → EUR desde exchangerate.host (sin clave)")

try:
    response = requests.get("https://v6.exchangerate-api.com/v6/013d1a2c2928ad7aaa14e76c/latest/USD")
    data = response.json()
    print("Respuesta JSON:", data)

    if data.get("result") == "success":
        tipo_cambio = data["conversion_rates"]["EUR"]
        print(f"Tipo de cambio USD → EUR: {tipo_cambio:.4f}")
    else:
        print("⚠️  No se pudo obtener un resultado exitoso de la API.")
except Exception as e:
    print(f"❌ Error al obtener el tipo de cambio: {e}")




