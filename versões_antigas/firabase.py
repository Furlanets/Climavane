import paho.mqtt.client as mqtt
import json
import dotenv
import os
from datetime import datetime, timezone
# 1. ⬇️ Importações do Firebase
import firebase_admin
from firebase_admin import credentials, db
# O módulo db é usado para interagir com o Realtime Database

# Carrega variáveis de ambiente do arquivo .env
dotenv.load_dotenv()

# Configurações do broker
BROKER = os.getenv("BROKER")
PORT = int(os.getenv("PORT"))
TOPIC = os.getenv("TOPIC")

# 1. 🧠 Inicialização do Firebase
# Usando o JSON de credenciais que você forneceu
cred = credentials.Certificate("puclima-firebase-adminsdk-fbsvc-5632f97c5b.json")
# ⚠️ Substitua 'https://SEU_PROJETO.firebaseio.com' pela URL do seu Realtime Database
DATABASE_URL = os.getenv("FIREBASE_DB_URL") 

if not DATABASE_URL:
    print("❌ Erro: A variável de ambiente FIREBASE_DB_URL não foi definida.")
    print("Por favor, crie um arquivo .env com FIREBASE_DB_URL=sua_url_do_firebase")
    exit()

try:
    firebase_admin.initialize_app(cred, {
        'databaseURL': DATABASE_URL
    })
    print("✅ Conexão com Firebase Realtime Database estabelecida com sucesso!")
except Exception as e:
    print(f"❌ Falha ao inicializar o Firebase: {e}")
    exit()


# 2. 🧩 Função para salvar/atualizar dados no Firebase
def atualizar_dados_climaticos(dispositivo, temperatura, umidade, mensagem_original):
    # O Firebase não usa "coleções" como o MongoDB, mas sim "caminhos" (paths)
    # Vamos usar o nome do dispositivo como a chave principal (nó)
    
    # Normaliza o nome do dispositivo para ser uma chave válida no Firebase
    # Ex: 'Temp Interna' -> 'temp_interna'
    chave_firebase = dispositivo.lower().replace(" ", "_")

    # Referência ao nó (path) no Firebase
    ref = db.reference(f'dados_climaticos/{chave_firebase}')
    
    # Prepara os dados a serem salvos
    dados_a_salvar = {
        # Armazena o timestamp em formato ISO 8601 UTC
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperatura_cel": temperatura,
        "umidade_relativa": umidade,
        "mensagem_bruta": mensagem_original
    }

    try:
        # Usamos set() para sobrescrever ou criar o nó com o nome do dispositivo.
        # Isso simula o 'upsert' baseado na chave 'dispositivo'.
        ref.set(dados_a_salvar)
        print(f"♻️ Dados de '{dispositivo}' atualizados/criados no Firebase.")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar dados no Firebase: {e}")

# O restante das funções é mantido
# ---

# 🔍 Função para extrair bn, temperatura e umidade
def extrair_dados(msg_str):
    temperatura = None
    umidade = None
    dispositivo = "Desconhecido"

    try:
        data = json.loads(msg_str)
        # Assumindo que a mensagem é uma lista de dicionários
        for item in data:
            if "bn" in item:
                if item["bn"] == "F803320100033CAE":
                    dispositivo = "Temp Interna"
                elif item["bn"] == "F803320100033877":
                    dispositivo = "Temp Externa"
            # O bloco 'elif' verifica se os campos de temperatura ou umidade estão presentes
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
    
    # Formatação condicional para evitar erros se a variável for None
    temp_str = f"🌡️ Temperatura: {temperatura:.2f} °C" if temperatura is not None else "🌡️ Temperatura: N/A"
    umid_str = f"💧 Umidade: {umidade:.2f} %" if umidade is not None else "💧 Umidade: N/A"
    print(temp_str)
    print(umid_str)

    if dispositivo != "Desconhecido" and (temperatura is not None or umidade is not None):
        # Chama a nova função de persistência do Firebase
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