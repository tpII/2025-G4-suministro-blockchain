from dotenv import dotenv_values

# Leer variables del archivo .env
env = dotenv_values(".env")

with open("./TP2-ESCANER-RFID/config.h", "w") as f:
    f.write("// Archivo autogenerado desde .env\n")
    f.write("#ifndef CONFIG_H\n#define CONFIG_H\n\n")
    
    f.write(f'#define WIFI_SSID "{env["WIFI_SSID"]}"\n')
    f.write(f'#define WIFI_PASSWORD "{env["WIFI_PASSWORD"]}"\n\n')
    
    f.write(f'#define MQTT_SERVER "{env["MQTT_BROKER_URL"]}"\n')
    f.write(f'#define MQTT_PORT {env["MQTT_BROKER_PORT"]}\n')
    

    f.write("\n#endif // CONFIG_H\n")

print("✅ config.h generado con éxito a partir de .env")
