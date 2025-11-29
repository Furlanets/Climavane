import paho.mqtt.client as mqtt
import json
import dotenv
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime, timezone

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

# 🧩 Função para salvar/atualizar temperatura com base no dispositivo
def atualizar_dados_climaticos(dispositivo, temperatura, umidade, mensagem_original):
    db = mongo_client["climavane"]
    colecao = db["dados_climaticos"]

    try:
        filtro = {"dispositivo": dispositivo}
        atualizacao = {
            "$set": {
                "timestamp": datetime.utcnow(),
                "temperatura_cel": temperatura,
                "umidade_relativa": umidade,
                "mensagem_bruta": mensagem_original
            }
        }
        resultado = colecao.update_one(filtro, atualizacao, upsert=True)

        if resultado.matched_count > 0:
            print(f"♻️ Dados de '{dispositivo}' atualizados no MongoDB.")
        else:
            print(f"🆕 Novo registro criado para '{dispositivo}'.")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar dados no MongoDB: {e}")

# 🔍 Função para extrair bn, temperatura e umidade
def extrair_dados(msg_str):
    temperatura = None
    umidade = None
    dispositivo = "Desconhecido"

    try:
        data = json.loads(msg_str)
        for item in data:
            if "bn" in item:
                if item["bn"] == "F803320100033CAE":
                    dispositivo = "Temp Interna"
                elif item["bn"] == "F803320100033877":
                    dispositivo = "Temp Externa"
            elif item.get("u") == "Cel":
                temperatura = item.get("v")
            elif item.get("u") == "%RH":
                umidade = item.get("v")
    except Exception as e:
        print(f"⚠️ Erro ao processar mensagem: {e}")

    return dispositivo, temperatura, umidade

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

    dispositivo, temperatura, umidade = extrair_dados(mensagem)

    print(f"📡 Dispositivo identificado: {dispositivo}")
    if temperatura is not None:
        print(f"🌡️ Temperatura: {temperatura:.2f} °C")
    if umidade is not None:
        print(f"💧 Umidade: {umidade:.2f} %")

    if dispositivo != "Desconhecido" and (temperatura is not None or umidade is not None):
        atualizar_dados_climaticos(dispositivo, temperatura, umidade, mensagem)
    else:
        print("❌ Dados incompletos ou dispositivo não reconhecido.")

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
