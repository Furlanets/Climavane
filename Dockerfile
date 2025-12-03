FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilar pacotes Python quando necessário
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   build-essential \
	   gcc \
	   libffi-dev \
	&& rm -rf /var/lib/apt/lists/*

# Copia somente requirements primeiro
COPY requirements.txt /app/requirements.txt

# Atualiza pip e instala dependências Python
RUN python -m pip install --upgrade pip \
	&& pip install --no-cache-dir -r /app/requirements.txt

# Copia todo o código da aplicação para /app
COPY . /app

# Cria usuário não-root e ajusta permissões
RUN groupadd -r app && useradd -r -g app app \
	&& chown -R app:app /app

USER app

# Comando padrão para executar a aplicação
CMD ["python", "firebase.py"]