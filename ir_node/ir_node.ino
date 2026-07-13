#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <map>

const char* ssid = "HUAWEI-4gNy";
const char* password = "csffb76673";
const char* mqtt_server = "broker.emqx.io";
const int mqtt_port = 1883;
const int MQTT_LED = D0;
const int WiFi_LED = D1;
const uint16_t kIrLed = D2;
std::map<String, uint32_t> ir_codes;

WiFiClient espClient;
PubSubClient client(espClient);

IRsend irsend(kIrLed);

void setup_wifi() {

  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(WiFi_LED,  !digitalRead(WiFi_LED));
  }

  randomSeed(micros());

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  digitalWrite(WiFi_LED,  1);
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  irsend.sendNEC(ir_codes[message], 32);
  Serial.print("Message sent: ");
  Serial.print(message);
  Serial.print(", with IR Code: ");
  Serial.println(ir_codes[message]);
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    digitalWrite(MQTT_LED, !digitalRead(MQTT_LED));
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      client.subscribe("hash/tvctl");
      digitalWrite(MQTT_LED, 1);
    } else {
      digitalWrite(MQTT_LED, 0);
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 2 seconds");
      // Wait 2 seconds before retrying
      delay(2000);
    }
  }
}

void setup() {
  // Initialize Serial Monitor (to view results on PC)
  Serial.begin(9600);
  
  irsend.begin();

  pinMode(WiFi_LED, OUTPUT);
  pinMode(MQTT_LED, OUTPUT);

  Serial.println("NodeMCU ready to receive strings...");
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  ir_codes["POWER"] = 0x20DF10EF;
  ir_codes["VOL_UP"] = 0x00FD22DD;
  ir_codes["VOL_DOWN"] = 0x00FDC23D;
  ir_codes["OK"] = 0x00FDA857;
  ir_codes["UP"] = 0x00FD6897;
  ir_codes["DOWN"] = 0x00FDE817;
  ir_codes["RIGHT"] = 0x00FD18E7;
  ir_codes["LEFT"] = 0x00FD9867;
  ir_codes["HOME"] = 0x00FD04FB;
  ir_codes["MUTE"] = 0x00FD708F;
  ir_codes["SOURCE"] = 0x00FD48B7;
  ir_codes["BACK"] = 0x00FD12ED;
  ir_codes["YOUTUBE"] = 0x00FD55AA;
  ir_codes["MEDIA"] = 0x00FDCC33;
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}