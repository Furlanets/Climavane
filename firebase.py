import paho.mqtt.client as mqtt
import json
import dotenv
import os
from datetime import datetime, timezone
import math

# Firebase
import firebase_admin
from firebase_admin import credentials, db

# Carrega variáveis do .env
dotenv.load_dotenv()

BROKER = os.getenv("BROKER")
PORT = int(os.getenv("PORT"))
TOPIC = os.getenv("TOPIC")

UPDATES_PER_SAMPLE = int(os.getenv("UPDATES_PER_SAMPLE", "6"))
HIST_MAX = int(os.getenv("HIST_MAX", "48"))

# Inicialização Firebase
cred = credentials.Certificate("puclima-firebase-adminsdk-fbsvc-5632f97c5b.json")
DATABASE_URL = os.getenv("FIREBASE_DB_URL")

if not DATABASE_URL:
    print("❌ FIREBASE_DB_URL não definida no .env")
    exit()

firebase_admin.initialize_app(cred, {
    "databaseURL": DATABASE_URL
})

print("✅ Firebase inicializado.")


# ============================================================
#  PARSER DE DADOS CLIMÁTICOS
# ============================================================

def extrair_dados(msg_str):
    dispositivo = "Desconhecido"
    dados = {
        "temperatura_cel": None,
        "umidade_relativa": None,
        "radiacao_solar_w_m2": None,
        "direcao_vento": None,
        "velocidade_vento_media_m_s": None,
        "velocidade_vento_gust_m_s": None,
        "nivel_chuva_m": None,
        "mensagem_timestamp": None
    }

    try:
        data = json.loads(msg_str)

        # Pode vir lista ou dict com "e"
        if isinstance(data, list):
            itens = data
        elif isinstance(data, dict):
            itens = data.get("e", [data])
            if "bn" in data:
                if data["bn"] == "F803320100033877":
                    dispositivo = "Temp Externa"
                if data["bn"] == "F803320100033CAE":
                    dispositivo = "Temp Interna"
            if "bt" in data:
                dados["mensagem_timestamp"] = data["bt"]
        else:
            return dispositivo, dados

        for item in itens:
            if not isinstance(item, dict):
                continue

            # Identifica o dispositivo
            if "bn" in item:
                if item["bn"] == "F803320100033877":
                    dispositivo = "Temp Externa"
                if item["bn"] == "F803320100033CAE":
                    dispositivo = "Temp Interna"
                if "bt" in item:
                    dados["mensagem_timestamp"] = item["bt"]

            nome = item.get("n")
            unidade = item.get("u")
            valor = item.get("v")

            if unidade == "Cel":
                dados["temperatura_cel"] = valor

            elif unidade == "%RH":
                dados["umidade_relativa"] = valor

            elif unidade == "W/m2" or nome == "emw_solar_radiation":
                dados["radiacao_solar_w_m2"] = valor

            elif nome == "emw_wind_direction":
                try:
                    dados["direcao_vento"] = round(float(valor) * 180 / math.pi, 2)
                except:
                    dados["direcao_vento"] = round(valor, 2)

            elif nome == "emw_average_wind_speed":
                dados["velocidade_vento_media_m_s"] = valor

            elif nome == "emw_gust_wind_speed":
                dados["velocidade_vento_gust_m_s"] = valor

            elif nome == "emw_rain_level":
                dados["nivel_chuva_m"] = valor

    except Exception as e:
        print(f"⚠️ Erro ao parsear SenML: {e}")

    return dispositivo, dados


# ============================================================
#  SALVAMENTO NO FIREBASE + HISTÓRICO + CHUVA (DIFERENÇA)
# ============================================================

def atualizar_dados_climaticos(dispositivo, dados, mensagem_original):

    chave = dispositivo.lower().replace(" ", "_")
    ref = db.reference(f"dados_climaticos/{chave}")

    # Atualiza o estado atual
    ref.update({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mensagem_timestamp": dados.get("mensagem_timestamp"),

        "temperatura_cel": dados.get("temperatura_cel"),
        "umidade_relativa": dados.get("umidade_relativa"),
        "radiacao_solar_w_m2": dados.get("radiacao_solar_w_m2"),
        "direcao_vento": dados.get("direcao_vento"),
        "velocidade_vento_media_m_s": dados.get("velocidade_vento_media_m_s"),
        "velocidade_vento_gust_m_s": dados.get("velocidade_vento_gust_m_s"),
        "nivel_chuva_m": dados.get("nivel_chuva_m"),

        "mensagem_bruta": mensagem_original
    })

    meta_ref = ref.child("meta")

    # ========================================================
    #  CÁLCULO SIMPLES DE CHUVA POR DIFERENÇA ENTRE LEITURAS
    # ========================================================
    nivel_atual = dados.get("nivel_chuva_m")

    if nivel_atual is not None:
        ultimo_nivel = meta_ref.child("ultimo_nivel_chuva_m").get()

        if ultimo_nivel is not None:
            try:
                ultimo_nivel = float(ultimo_nivel)
                diff_m = nivel_atual - ultimo_nivel

                if diff_m >= 0:
                    chuva_mm = diff_m
                    meta_ref.update({"chuva_ultima_medicao_mm": chuva_mm})
                    print(f"🌧️ Chuva desde a última medição: {chuva_mm:.2f} mm")
                else:
                    # Sensor resetou
                    print("⚠️ Reset do acumulador de chuva detectado.")
                    meta_ref.update({"chuva_ultima_medicao_mm": 0})
            except:
                pass

        # Atualiza o nível anterior para o próximo cálculo
        meta_ref.update({"ultimo_nivel_chuva_m": nivel_atual})

    # ========================================================
    #  HISTÓRICO SIMPLES (SEM CÁLCULOS DE CHUVA)
    # ========================================================

    # Contador de mensagens
    contador = meta_ref.child("contador").get() or 0
    contador = int(contador) + 1
    meta_ref.update({"contador": contador})

    # Gera amostra apenas a cada X mensagens
    if contador % UPDATES_PER_SAMPLE == 0:

        hist_ref = ref.child("historico")
        hist_ref.push({
            "mensagem_timestamp": dados.get("mensagem_timestamp"),
            "nivel_chuva_m": dados.get("nivel_chuva_m"),
            "temperatura_cel": dados.get("temperatura_cel"),
            "umidade_relativa": dados.get("umidade_relativa"),
            "radiacao_solar_w_m2": dados.get("radiacao_solar_w_m2"),
            "direcao_vento": dados.get("direcao_vento"),
            "velocidade_vento_media_m_s": dados.get("velocidade_vento_media_m_s"),
            "velocidade_vento_gust_m_s": dados.get("velocidade_vento_gust_m_s"),
            "grava_timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Limita histórico
        hist = hist_ref.get() or {}
        if len(hist) > HIST_MAX:
            # remove as mais antigas
            for key in list(hist.keys())[:len(hist) - HIST_MAX]:
                hist_ref.child(key).delete()


# ============================================================
#  MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Conectado ao broker MQTT!")
        client.subscribe(TOPIC)
        print(f"📡 Inscrito em: {TOPIC}")
    else:
        print("❌ Falha ao conectar ao MQTT, código:", rc)


def on_message(client, userdata, msg):
    mensagem = msg.payload.decode()

    print("\n📥 Mensagem bruta recebida:")
    print(mensagem)

    dispositivo, dados = extrair_dados(mensagem)

    print(f"📡 Dispositivo: {dispositivo}")

    dados_validos = any([
        dados.get("temperatura_cel"),
        dados.get("umidade_relativa"),  
        dados.get("radiacao_solar_w_m2"),
        dados.get("velocidade_vento_media_m_s"),
        dados.get("velocidade_vento_gust_m_s"),
        dados.get("nivel_chuva_m")
    ])

    if dispositivo != "Desconhecido" and dados_validos:
        atualizar_dados_climaticos(dispositivo, dados, mensagem)
    else:
        print("ℹ️ Mensagem ignorada (não contém dados climáticos).")


# ============================================================
#  LOOP MQTT
# ============================================================

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("🔌 Conectando ao broker MQTT...")
client.connect(BROKER, PORT, keepalive=60)

client.loop_forever()
