import paho.mqtt.client as mqtt  # cliente MQTT para receber mensagens dos sensores
import json                      # para fazer parse das mensagens JSON recebidas
import dotenv                    # para carregar variáveis de ambiente de um arquivo .env
import os                        # para acessar variáveis de ambiente
from datetime import datetime, timezone  # para timestamps no formato ISO UTC
import math                      # usada para conversão de radianos para graus

# 1. ⬇️ Importações do Firebase
import firebase_admin            # SDK do Firebase Admin
from firebase_admin import credentials, db  # credenciais e módulo de Realtime Database
# O módulo db é usado para interagir com o Realtime Database

# Carrega variáveis de ambiente do arquivo .env
dotenv.load_dotenv()

# Configurações do broker MQTT (lidas do .env)
# BROKER: endereçamento do broker (ex: ip ou hostname)
BROKER = os.getenv("BROKER")
# PORT: porta do broker (ex: 1883)
PORT = int(os.getenv("PORT"))
# TOPIC: tópico MQTT a ser inscrito
TOPIC = os.getenv("TOPIC")

# Configurações de amostragem/histórico (podem ser sobrescritas via .env)
# UPDATES_PER_SAMPLE: quantas atualizações MQTT equivalem a 1 amostra no histórico
UPDATES_PER_SAMPLE = int(os.getenv("UPDATES_PER_SAMPLE", "6"))
# HIST_MAX: número máximo de amostras a manter no histórico
HIST_MAX = int(os.getenv("HIST_MAX", "48"))
# HIST_WINDOW_MINUTES: janela (em minutos) usada para calcular chuva nos últimos X minutos
HIST_WINDOW_MINUTES = int(os.getenv("HIST_WINDOW_MINUTES", "30"))

# 1. 🧠 Inicialização do Firebase
# Arquivo de credenciais JSON do serviço (deve existir no projeto)
cred = credentials.Certificate("puclima-firebase-adminsdk-fbsvc-5632f97c5b.json")
# A URL do Realtime Database vem do .env
DATABASE_URL = os.getenv("FIREBASE_DB_URL") 

if not DATABASE_URL:
    # Se a URL não estiver definida, abortamos com instruções
    print("❌ Erro: A variável de ambiente FIREBASE_DB_URL não foi definida.")
    print("Por favor, crie um arquivo .env com FIREBASE_DB_URL=sua_url_do_firebase")
    exit()

try:
    # Inicializa o app do Firebase com as credenciais e a URL do DB
    firebase_admin.initialize_app(cred, {
        'databaseURL': DATABASE_URL
    })
    print("✅ Conexão com Firebase Realtime Database estabelecida com sucesso!")
except Exception as e:
    # Caso falhe, imprime o erro e encerra
    print(f"❌ Falha ao inicializar o Firebase: {e}")
    exit()


# 2. 🧩 Função para salvar/atualizar dados no Firebase
def atualizar_dados_climaticos(dispositivo, dados, mensagem_original):
    # Normaliza o nome do dispositivo para gerar uma chave segura no Firebase
    chave_firebase = dispositivo.lower().replace(" ", "_")

    # Referência ao nó do dispositivo em 'dados_climaticos/<chave>'
    ref = db.reference(f'dados_climaticos/{chave_firebase}')

    # Prepara o dicionário com os campos que serão gravados/atualizados
    dados_a_salvar = {
        # Timestamp de quando gravamos no DB (ISO 8601 UTC)
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # Timestamp original vindo da mensagem (se houver)
        "mensagem_timestamp": dados.get("mensagem_timestamp"),
        # Medidas principais extraídas
        "temperatura_cel": dados.get("temperatura_cel"),
        "umidade_relativa": dados.get("umidade_relativa"),
        "radiacao_solar_w_m2": dados.get("radiacao_solar_w_m2"),
        "direcao_vento": dados.get("direcao_vento"),
        "velocidade_vento_media_m_s": dados.get("velocidade_vento_media_m_s"),
        "velocidade_vento_gust_m_s": dados.get("velocidade_vento_gust_m_s"),
        "nivel_chuva_m": dados.get("nivel_chuva_m"),
        # Mensagem bruta inteira (útil para debugging)
        "mensagem_bruta": mensagem_original
    }

    try:
        # Atualiza (merge) os campos no nó do dispositivo, sem apagar outros subnós
        ref.update(dados_a_salvar)
        print(f"♻️ Dados de '{dispositivo}' atualizados no Firebase.")

        # ---------- LÓGICA DE AMOSTRAGEM E HISTÓRICO ----------
        # 'meta' guarda metadados como contador e resultados de cálculo
        meta_ref = ref.child('meta')

        # Lê o contador atual (padrão 0 se não existir)
        contador = meta_ref.child('contador').get()
        try:
            contador = int(contador) if contador is not None else 0
        except Exception:
            contador = 0

        # Incrementa o contador a cada atualização recebida
        contador += 1
        meta_ref.update({'contador': contador})

        # Decide se devemos criar uma amostra no histórico (a cada UPDATES_PER_SAMPLE mensagens)
        should_sample = (contador % UPDATES_PER_SAMPLE) == 0

        if should_sample:
            # Referência para o nó de histórico
            hist_ref = ref.child('historico')

            # Constroi o objeto amostra com os campos que queremos manter no histórico
            amostra = {
                'mensagem_timestamp': dados.get('mensagem_timestamp'),
                'nivel_chuva_m': dados.get('nivel_chuva_m'),
                'temperatura_cel': dados.get('temperatura_cel'),
                'umidade_relativa': dados.get('umidade_relativa'),
                'radiacao_solar_w_m2': dados.get('radiacao_solar_w_m2'),
                'direcao_vento': dados.get('direcao_vento'),
                'velocidade_vento_media_m_s': dados.get('velocidade_vento_media_m_s'),
                'velocidade_vento_gust_m_s': dados.get('velocidade_vento_gust_m_s'),
                # Timestamp de quando gravamos a amostra
                'grava_timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Insere a amostra no histórico com uma chave única (push gera a key)
            new_key = hist_ref.push(amostra)

            # Busca todo o histórico para verificar tamanho e possivelmente remover antigos
            hist = hist_ref.get() or {}
            # Converte o dict de histórico em uma lista de (key, timestamp_numérico)
            items = []
            for k, v in hist.items():
                ts = None
                # Tenta usar mensagem_timestamp (numérico) se disponível
                if isinstance(v, dict) and v.get('mensagem_timestamp') is not None:
                    try:
                        ts = float(v.get('mensagem_timestamp'))
                    except Exception:
                        ts = None
                if ts is None:
                    # fallback: usa grava_timestamp (ISO) para obter timestamp numérico
                    try:
                        ts = datetime.fromisoformat(v.get('grava_timestamp')).timestamp()
                    except Exception:
                        ts = 0
                items.append((k, ts))

            # Ordena as entradas pelo timestamp (ascendente)
            items.sort(key=lambda x: x[1])

            # Remove entradas mais antigas enquanto ultrapassar HIST_MAX
            while len(items) > HIST_MAX:
                key_to_remove, _ = items.pop(0)
                hist_ref.child(key_to_remove).delete()

            # ---------- CÁLCULO DA CHUVA NOS ÚLTIMOS HIST_WINDOW_MINUTES ----------
            # Recarrega histórico (após remoções) para o cálculo
            hist = hist_ref.get() or {}

            latest_ts = None
            latest_val = None
            entries = []  # lista de tuples (timestamp, nivel_chuva_m)
            for k, v in hist.items():
                mts = None
                try:
                    mts = float(v.get('mensagem_timestamp')) if v.get('mensagem_timestamp') is not None else None
                except Exception:
                    mts = None
                if mts is None:
                    try:
                        mts = datetime.fromisoformat(v.get('grava_timestamp')).timestamp()
                    except Exception:
                        mts = None
                if mts is None:
                    # não conseguimos obter timestamp dessa entrada, pular
                    continue
                nivel = v.get('nivel_chuva_m')
                try:
                    nivel = float(nivel) if nivel is not None else None
                except Exception:
                    nivel = None
                entries.append((mts, nivel))

            if entries:
                # ordena por tempo e pega o mais recente
                entries.sort(key=lambda x: x[0])
                latest_ts, latest_val = entries[-1]

                # calcula janela em segundos e limiar
                window_secs = HIST_WINDOW_MINUTES * 60
                threshold = latest_ts - window_secs

                # encontra a primeira entrada dentro da janela
                earlier = None
                for mts, nivel in entries:
                    if mts >= threshold:
                        earlier = (mts, nivel)
                        break

                # se não encontrou nenhuma dentro da janela, usa a mais antiga disponível
                if earlier is None and len(entries) > 0:
                    earlier = entries[0]

                chuva_30min_mm = None
                if earlier is not None and latest_val is not None and earlier[1] is not None:
                    # diferença em metros convertido para milímetros (m -> mm)
                    diff_m = latest_val - earlier[1]
                    chuva_30min_mm = diff_m * 1000.0

                # grava contador e resultado do cálculo de chuva em meta
                update_calc = {'contador': contador}
                if chuva_30min_mm is not None:
                    update_calc['chuva_30min_mm'] = chuva_30min_mm
                meta_ref.update(update_calc)

    except Exception as e:
        # Qualquer erro na atualização é logado aqui
        print(f"⚠️ Erro ao atualizar dados no Firebase: {e}")


# Função para extrair bn, temperatura e outros campos da mensagem MQTT (JSON)
def extrair_dados(msg_str):
    dispositivo = "Desconhecido"  # valor padrão caso não identifiquemos o dispositivo
    # dicionário com as chaves que vamos popular a partir da mensagem
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
        # parsea string JSON para estrutura Python (lista de dicionários esperada)
        data = json.loads(msg_str)
        # iteramos cada item do payload
        for item in data:
            # se o item contém 'bn' (base name), podemos identificar o dispositivo
            if "bn" in item:
                if item["bn"] == "F803320100033877":
                    dispositivo = "Temp Externa"
                # se houver campo de timestamp bruto 'bt', guardamos
                if "bt" in item:
                    dados["mensagem_timestamp"] = item.get("bt")

            # extraímos valores por nome ('n'), unidade ('u') e valor ('v')
            nome = item.get("n")
            unidade = item.get("u")
            valor = item.get("v")

            # preenche os campos apropriados dependendo da unidade/nome
            if unidade == "Cel":
                dados["temperatura_cel"] = valor
            elif unidade == "%RH":
                dados["umidade_relativa"] = valor
            elif unidade == "W/m2" or nome == "emw_solar_radiation":
                dados["radiacao_solar_w_m2"] = valor
            elif nome == "emw_wind_direction":
                # valor costuma vir em radianos — converte para graus
                try:
                    if valor is not None:
                        dados["direcao_vento"] = float(valor) * 180.0 / math.pi
                    else:
                        dados["direcao_vento"] = None
                except Exception:
                    # se falhar na conversão, salva o valor original
                    dados["direcao_vento"] = valor
            elif nome == "emw_average_wind_speed":
                dados["velocidade_vento_media_m_s"] = valor
            elif nome == "emw_gust_wind_speed":
                dados["velocidade_vento_gust_m_s"] = valor
            elif nome == "emw_rain_level":
                dados["nivel_chuva_m"] = valor

    except Exception as e:
        # se o JSON estiver inválido ou ocorrer outro erro, logamos
        print(f"⚠️ Erro ao processar mensagem: {e}")

    # retorna o dispositivo identificado e o dicionário com os dados coletados
    return dispositivo, dados


# Callback: chamado quando o cliente MQTT conecta ao broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        # rc == 0 significa sucesso
        print("✅ Conectado ao broker com sucesso!")
        # inscreve no tópico configurado
        client.subscribe(TOPIC)
        print(f"📡 Inscrito no tópico '{TOPIC}'")
    else:
        # erro de conexão
        print(f"⚠️ Falha na conexão. Código de retorno: {rc}")


# Callback: chamado quando chega uma mensagem no tópico inscrito
def on_message(client, userdata, msg):
    # decodifica payload de bytes para string
    mensagem = msg.payload.decode()
    print(f"\n📥 Mensagem bruta recebida: {mensagem}")

    # extrai dispositivo e dicionário de dados
    dispositivo, dados = extrair_dados(mensagem)

    print(f"📡 Dispositivo identificado: {dispositivo}")

    # Formatação condicional para evitar erros se a variável for None
    temperatura = dados.get("temperatura_cel")
    umidade = dados.get("umidade_relativa")
    temp_str = f"🌡️ Temperatura: {temperatura:.2f} °C" if temperatura is not None else "🌡️ Temperatura: N/A"
    umid_str = f"💧 Umidade: {umidade:.2f} %" if umidade is not None else "💧 Umidade: N/A"
    print(temp_str)
    print(umid_str)

    # Verifica se há pelo menos algum dado relevante para enviar
    dados_validos = any([
        dados.get("temperatura_cel") is not None,
        dados.get("umidade_relativa") is not None,
        dados.get("radiacao_solar_w_m2") is not None,
        dados.get("velocidade_vento_media_m_s") is not None,
        dados.get("velocidade_vento_gust_m_s") is not None,
        dados.get("nivel_chuva_m") is not None
    ])

    if dispositivo != "Desconhecido" and dados_validos:
        # Chama a função de persistência do Firebase com o dict de dados
        atualizar_dados_climaticos(dispositivo, dados, mensagem)
    else:
        print("❌ Dados incompletos ou dispositivo não reconhecido.")


# Cria cliente MQTT (biblioteca paho)
client = mqtt.Client()

# Define callbacks do cliente MQTT
client.on_connect = on_connect
client.on_message = on_message

# Conecta ao broker especificado nas variáveis de ambiente
print("🔌 Conectando ao broker...")
client.connect(BROKER, PORT, keepalive=60)

# Mantém o loop do cliente rodando (bloqueante)
client.loop_forever()