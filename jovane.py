import paho.mqtt.client as mqtt
import json
import dotenv
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Carrega variáveis de ambiente do arquivo .env
dotenv.load_dotenv()

# Configurações do broker
BROKER = os.getenv("BROKER")
PORT = int(os.getenv("PORT"))
TOPIC = os.getenv("TOPIC")

# 🧠 Função para inicializar e verificar conexão com o MongoDB
def inicializar_banco_dados():
    connection_string = os.getenv("MONGO_URI")

    if not connection_string:
        print("❌ Erro: A variável de ambiente MONGO_URI não foi definida.")
        print("Por favor, crie um arquivo .env com MONGO_URI=sua_conexao")
        exit()

    try:
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.server_info()
        print("✅ Conexão com MongoDB estabelecida com sucesso!")
        return client
    except ConnectionFailure as e:
        print(f"❌ Falha ao conectar ao MongoDB: {e}")
        exit()

# Inicializa banco de dados
mongo_client = inicializar_banco_dados()

# 🧩 Função para armazenar dados no MongoDB
def salvar_temperatura(valor_cel, mensagem_original):
    db = mongo_client["climavane"]
    colecao = db["dados_climaticos"]

    try:
        documento = {
            "timestamp": datetime.utcnow(),
            "temperatura_cel": valor_cel,
            "mensagem_bruta": mensagem_original
        }
        resultado = colecao.insert_one(documento)
        print(f"💾 Temperatura armazenada no MongoDB com ID: {resultado.inserted_id}")
    except Exception as e:
        print(f"⚠️ Erro ao inserir dados no MongoDB: {e}")

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
        salvar_temperatura(valor_cel, mensagem)
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
