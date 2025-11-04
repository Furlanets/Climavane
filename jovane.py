import paho.mqtt.client as mqtt
import json
import dotenv
import os
# Carrega variáveis de ambiente do arquivo .env
dotenv.load_dotenv()

# Configurações do broker
BROKER = os.getenv("BROKER")
PORT = int(os.getenv("PORT"))
TOPIC = os.getenv("TOPIC")

# Função para extrair o campo de temperatura (u == "Cel")
def extrair_temperatura(msg_str):
    try:
        data = json.loads(msg_str)
        for item in data:
            if item.get("u") == "Cel":
                return item.get("v")
    except Exception as e:
        print(f"⚠️ Erro ao processar mensagem: {e}")
    return None

# Callback: conexão com o broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Conectado ao broker com sucesso!")
        client.subscribe(TOPIC)
        print(f"📡 Inscrito no tópico '{TOPIC}'")
    else:
        print(f"⚠️ Falha na conexão. Código de retorno: {rc}")

# Callback: mensagem recebida
def on_message(client, userdata, msg):
    mensagem = msg.payload.decode()
    print(f"\n📥 Mensagem bruta recebida: {mensagem}")

    valor_cel = extrair_temperatura(mensagem)
    if valor_cel is not None:
        print(f"🌡️ Temperatura (Cel): {valor_cel:.2f} °C")
    else:
        print("❌ Campo de temperatura não encontrado na mensagem.")

# Cria cliente MQTT
client = mqtt.Client()

# Define callbacks
client.on_connect = on_connect
client.on_message = on_message

# Conecta ao broker
print("🔌 Conectando ao broker...")
client.connect(BROKER, PORT, keepalive=60)

# Mantém conexão ativa
client.loop_forever()