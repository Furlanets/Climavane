import paho.mqtt.client as mqtt
import json

# Configurações do broker
BROKER = "192.168.1.110"
PORT = 1883
TOPIC = "konda"

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






# import paho.mqtt.client as mqtt

# # Configurações do broker
# BROKER = "192.168.1.110"   # Pode ser alterado para o endereço do seu broker
# PORT = 1883                     # Porta padrão MQTT
# TOPIC = "konda"

# # Função chamada quando a conexão for bem-sucedida
# def on_connect(client, userdata, flags, rc):
#     if rc == 0:
#         print("✅ Conectado ao broker com sucesso!")
#         client.subscribe(TOPIC)
#         print(f"📡 Inscrito no tópico '{TOPIC}'")
#     else:
#         print(f"⚠️ Falha na conexão. Código de retorno: {rc}")

# # Função chamada quando uma mensagem é recebida
# def on_message(client, userdata, msg):
#     print(f"📥 Mensagem recebida no tópico '{msg.topic}': {msg.payload.decode()}")

# # Cria cliente MQTT
# client = mqtt.Client()

# # Define callbacks
# client.on_connect = on_connect
# client.on_message = on_message

# # Conecta ao broker
# print("🔌 Conectando ao broker...")
# client.connect(BROKER, PORT, keepalive=60)

# # Loop para manter a conexão e escutar mensagens
# client.loop_forever()
