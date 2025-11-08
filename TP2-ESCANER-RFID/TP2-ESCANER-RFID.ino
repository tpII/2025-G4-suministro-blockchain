#define MCU_ESP8266
//#define MCU_ESP32
#include "config.h"


// Para conectar al WiFi. (Seleccionar MCU) 
#ifdef MCU_ESP8266
  #include <ESP8266WiFi.h>
#elif defined(MCU_ESP32)
  #include <WiFi.h>ds
#else 
  #error Debe definir MCU_ESP8266 o MCU_ESP32 antes de compilar.
#endif

// Para usar el escaner RFID
#include <MFRC522.h>
#include <SPI.h>
// Para usar el sensor de temperatura y humedad DHT11
#include <DHT.h>
// Para usar PROTOCOLO MQTT
#include <PubSubClient.h>

#include <string.h>

/* RED WiFi*/
// Nombre de red
const char* ssid = WIFI_SSID;  //en .env
// Contraseña de red
const char* password = WIFI_PASSWORD;  //en .env

/* MQTT */
// Direccion IP del servidor MQTT
const char* mqtt_server = MQTT_SERVER;  
// Puerto MQTT predeterminado
const int mqtt_port = MQTT_PORT;  

// Instancias de cliente MQTT
WiFiClient espClient;
PubSubClient client(espClient);

/* RFID */
// Pines del lector RFID
#define SS_PIN  2 //ESP8266 pin GPIO2 (D4)
//#define SS_PIN  15  // ESP8266 pin GPIO15 (D8) - ESP32 pin GPIO5 
#define RST_PIN 0 // ESP8266 pin GPIO0 (D3) - ESP32 pin GPIO27 
// Pin para manejar LED escaneo RFID
#define RFID_LED_PIN 14 // ESP32 pin GPIO14

// Instancia de RFID
MFRC522 rfid(SS_PIN, RST_PIN);

// FLAG de peticion RFID
static bool RFID_REQUEST = false;

/* DHT11 */
// Se selecciona el modelo de DHT
#define DHTTYPE DHT11
// Pin del sensor DHT11
#define dht_dpin 4
//Instancia de DHT11
DHT dht(dht_dpin,DHTTYPE);

// FLAG de petición DHT
static bool DHT_REQUEST = false;

/* Variables de tiempo */
// Tiempos máximos
#define HEARTBEAT_WAIT 3000 // Esperar 3000 ms antes de mandar un "látido"
static unsigned long last_heartbeat_time = 0;

//El lector deja de leer si pasa mucho tiempo --> se debe reiniciar
unsigned long tiempoSinRespuesta = 0;
unsigned long ultimoIntento = 0;
const unsigned long TIEMPO_MAX_SIN_RESPUESTA = 8000; // si pasa 8s sin leer, reiniciamos


void setup() {

  // Inicializar comunicacion serie
  Serial.begin(115200);

  // Configura el LED para el escaneo RFID como SALIDA
  //pinMode(RFID_LED_PIN, OUTPUT);

  // Inicializar SPI y el lector RFID
  SPI.begin();
  rfid.PCD_Init();

  //Inicializar DHT11
  dht.begin();

  // Inicializar WiFi
  setup_wifi();

  // Inicializar SAP (red local) 
  setup_SAP();

  // Asigna servidor MQTT y callback
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  
  // Si se desconecto del servidor MQTT -> reconectar 
  if (!client.connected()) {
    reconnect();
  }

  // Se debe llamar periodicamente, para manejar la comunicación MQTT
  client.loop();

  // Envia un "látido"
  send_heartbeat();
  
  // Si se solicita lectura de RFID 
  if (RFID_REQUEST) {
    //Escanea RFID
    scan_rfid();        
  } else if (DHT_REQUEST) {
    // Envia lecturas de temperatura y humedad a los canales temp y hum
    send_dht();
  } else {
    // Apagar LED
    //digitalWrite(RFID_LED_PIN, LOW);
  }
}

// Inicializar WiFi
void setup_wifi() {

  // Conectar a la red Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
      delay(1000);
      Serial.println("Conectando a la red WiFi...");
  }

  // Aviso de conexión establecida
  Serial.println("Conexión WiFi establecida");
  // Imprimo dirección IP del dispositivo IOT
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

// Funcion que inicializa red local Soft Access Point y muestra direccion IP de dispositivo
void setup_SAP(){
  
  WiFi.softAP(ssid, password);

  IPAddress IP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(IP);
}

// Establecer función de callback para protocolo MQTT
void callback(char* topic, byte* payload, unsigned int length) {
  
  Serial.print("Mensaje recibido en el tema: ");
  Serial.println(topic);
  Serial.print("Contenido: ");
  String message = "";
  for (int i = 0; i < length; i++) {
    //Serial.print((char)payload[i]);
    message += (char)payload[i];
  }
  Serial.println(message);
  Serial.println();

  // Si se recibe una solicitud RFID, activa el flag para realizar lecturas de RFID
  if (strcmp(topic, "rfid_request") == 0) {
    if (message == "ON") {
      RFID_REQUEST = true;
      // Suscripcion al tema rfid para enviar datos
      client.subscribe("rfid"); 
      ultimoIntento = millis(); //guarda el momento en que se hizo el request
    } else if (message == "OFF") {
      RFID_REQUEST = false;
    }
  } else if (strcmp(topic, "dht_request") == 0) {
    if (message == "ON") {
      DHT_REQUEST = true;
      // Suscripcion al tema dht para enviar datos
      client.subscribe("temp"); 
      client.subscribe("hum"); 
    } else if (message == "OFF") {
      DHT_REQUEST = false;
    }    
  }

}

// Función para reconectar al BROKER MQTT
void reconnect() {
  
  while (!client.connected()) {
    Serial.print("Intentando conectar al servidor MQTT...");
    if (client.connect("ESPClient")) {
      Serial.println("conectado");
      // Suscribirse a topics
      client.subscribe("rfid_request"); 
      client.subscribe("dht_request");
    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      Serial.println(" Intentando de nuevo en 5 segundos");
      delay(5000);
    }
  }
}

//Funcion que genera heartbeat y publica el resultado
void send_heartbeat(){
  
  if (millis() - last_heartbeat_time > HEARTBEAT_WAIT) {
      last_heartbeat_time = millis();
      // Publica el mensaje de heartbeat en el tema correspondiente
      client.publish("heartbeat", "A");
  }    
}

//Funcion que realiza el escaneo del codigo rfid y lo publica en el topic "rfid"
void scan_rfid(){
  
  // Encender LED de ESCANEO
    //digitalWrite(RFID_LED_PIN, HIGH);
    // Si se lee un TAG RFID
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
      String uid = "";
      Serial.println("ENTRO");
      // Se construye el UID
      for (int i = 0; i < rfid.uid.size; i++) {
        uid += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
        uid += String(rfid.uid.uidByte[i], HEX);
      }

      /* Terminar comunicación con RFID */ 
       // Halt PICC
       rfid.PICC_HaltA();
      // Stop encryption on PCD
       rfid.PCD_StopCrypto1();

      // Publicar el UID del RFID en el topic "rfid"
      client.publish("rfid", uid.c_str());
      Serial.println("UID RFID: " + uid);

      // Desuscribirse del canal rfid después de escanear el RFID
      client.unsubscribe("rfid");

      RFID_REQUEST = false;
    }else{
      // si se cree que el lector se ha "apagado", se manda señal de reinicio
      tiempoSinRespuesta = millis() - ultimoIntento; //tiempo actual - tiempo en que se hizo el request 
      if(tiempoSinRespuesta > TIEMPO_MAX_SIN_RESPUESTA){
        Serial.println("No se detectan tarjetas hace mucho. Reiniciando RC522...");
        reiniciarRC522();
        ultimoIntento = millis(); //se guarda el momento en que se hizo el reset 
      }
        return;
    }  
}

// Funcion que lee el sensor DHT11 y envia la lectura por los topicos "temp" y "hum"
void send_dht(){
  //Variables para almacenar valores leidos de temperatura y humedad
  struct dht11_values{
    float temp;
    float hum;
    char temp_str[16];
    char hum_str[16];
  } dhtval;
   
  // Encender LED de ESCANEO 
  digitalWrite(RFID_LED_PIN, HIGH);

  //Lee temperatura y humedad en el ambiente
  dhtval.temp = dht.readTemperature();
  dhtval.hum = dht.readHumidity();
  
  Serial.println(dhtval.temp);
  Serial.println(dhtval.hum);

  //Convierte los datos leidos de float a char*
  snprintf(dhtval.temp_str, sizeof(dhtval.temp_str), "%.2f", dhtval.temp);
  snprintf(dhtval.hum_str, sizeof(dhtval.temp_str), "%.2f", dhtval.hum);

  // Publicar los valores leidos por el DHT11 en los topics "temp" y "hum"
  client.publish("temp",dhtval.temp_str);
  client.publish("hum",dhtval.hum_str);
  
  // Desuscribirse de los topics "temp" y "hum"
  client.unsubscribe("temp");
  client.unsubscribe("hum");
}

void reiniciarRC522() {
  rfid.PCD_Reset();
  delay(50);
  rfid.PCD_Init();
  Serial.println("RC522 reinicializado correctamente.");
}