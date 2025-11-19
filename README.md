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
