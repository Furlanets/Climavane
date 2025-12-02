### 🦖 Versão antiga
python -m venv .venv

#### 1.2. Ativar Ambiente Virtual
Você **deve** ativar o ambiente antes de instalar as dependências e rodar o código.

| Sistema Operacional | Comando de Ativação |
| :--- | :--- |
| **Linux/macOS** | `source .venv/bin/activate` |
| **Windows** | `.venv\Scripts\activate.bat` |

```markdown
# Para Linux/macOS
source .venv/bin/activate

# Para Windows
.venv\Scripts\activate.bat
````  
#### Instalar Dependências
Instala as bibliotecas listadas no arquivo `requirements.txt`.

pip install -r requirements.txt
```

# ⚡ Como Rodar
Após a configuração acima, execute o arquivo principal do Climavane Antigo (assumindo que seja `main.py` ou similar) com o Python do ambiente ativado:

```
```bash
# Exemplo (se o arquivo principal for 'main.py')
python main.py
```
--------------------------------------------------------------------------------------------------------------------------------------------------
## 🌐 Climavane Site

Esta versão é centralizada no script `firebase.py`, que gerencia a interação com o banco de dados em firebase database realtime

Ao atulizar o banco dados, o site é atualizado automaticamente graças ao firebase hosting

### 🚀 Execução

Basta rodar o arquivo `firebase.py`. A execução deste script é responsável por manter o banco de dados e o site atualizados automaticamente.


```python
# Comando para se conectar aos sensores utilizando mqqt e salvar os dados imprtantes em um banco de dados
python firebase.py


Devemos fazer com que ele atualize de meia em meia hora, como ele atualiza de 5 em 5 minutos, seria necessário fazer com que a cada 15 atualizações ele comece a guardar os dados e compare com os do ultimos 30 minutos(para calcular o nível da chuva), fazer um loop que sempre adiciona um numero no contador quando o mqtt recebe uma atualização, aí as variaveis vão ser atualizadas e subtituidas(fila), nós iremos guardar as ultimas 48 atualizações(duas atualizações a cada hora), depois vamos começar a subtituir elas, calcular uma média da temperatura do dia com esses dados 

O que vai ser mostrado no site: informações atuais(temp,vento), os milimetros de chuva atuais subtraidos pelos ultimos e calcular a diferença

### Rodando com Docker

Você pode rodar o programa dentro de um container Docker. Primeiro construa a imagem no diretório do projeto:

```powershell
docker build -t climavane:latest .
```

Em seguida execute o container montando o arquivo de credenciais do Firebase e seu `.env` (substitua os caminhos pelo caminho real no seu Windows):

```powershell
docker run --rm -it -v C:\caminho\para\puclima-firebase-adminsdk.json:/app/puclima-firebase-adminsdk-fbsvc-5632f97c5b.json -v C:\caminho\para\.env:/app/.env climavane:latest
```

Observação: montar o arquivo de credenciais e o `.env` em tempo de execução evita incluir credenciais sensíveis na imagem.