# 🎰 Alerta Bet BR 🚨   

# Sistema integrado de reconhecimento facial e monitoramento de fadiga em tempo real

Aplicação local desenvolvida em Python + OpenCV + MediaPipe + FastAPI, com dashboard web interativo para visualização de dados e alertas.
Criada como parte do projeto prático da disciplina de IoT & IOB (FIAP), a solução tem como objetivo detectar comportamentos de risco em apostas online e incentivar pausas conscientes durante o uso prolongado.

---

## 🎯 Objetivo

Muitos usuários que participam de ambientes de apostas online passam longos períodos focados em tela, apresentando sinais de fadiga ocular e redução da atenção.
O Alerta Bet BR atua como uma ferramenta de prevenção comportamental, monitorando o rosto do usuário e o tempo contínuo de atividade.

Quando são detectados sinais de risco — como baixa frequência de piscadas ou tempo excessivo em frente à tela — o sistema:

Exibe um alerta visual pulsante (“RISCO — PAUSA AGORA”);

Emite um alerta sonoro (no Windows);

Registra o evento no painel web, atualizando o gráfico e o histórico de alertas das últimas 24h.

---

## ⚙️ Tecnologias utilizadas
- **Python 3.10+**
- **OpenCV** (`opencv-python` e `opencv-contrib-python`)
- **MediaPipe** (landmarks faciais para olhos)
- **NumPy**
- **PIL/Pillow** (renderização de legendas)
- **Winsound** (apenas no Windows, para o alerta sonoro)
- **Chart.js + HTML/CSS/JS**
- **FastAPI + Uvicorn**

---

## 📂 Estrutura do projeto
ALERTABET/
├── src/
│   ├── main.py          # Aplicação principal (câmera, lógica de risco, alertas)
│   ├── risk_model.py    # Cálculo de risco e contadores (tempo e piscadas)
│   ├── integration.py   # API local com FastAPI (envio de status e eventos)
│   ├── utils.py         # Funções gráficas, métricas e renderização de painéis
│   ├── face_id.py       # Módulo opcional de reconhecimento facial (LBPH)
│   ├── www/
│   │   ├── index.html   # Dashboard web interativo
│   │   └── assets/...   # Scripts e estilos opcionais
│   └── data/faces/      # Dataset de rostos (para testes com face_id)
├── requirements.txt
└── README.md


---

## ▶️ Como executar

1. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   source .venv/bin/activate # Linux/Mac

---

## Instale as dependências:

pip install -r requirements.txt

## Execute a aplicação:
python src/main.py

## Dashboard web

O dashboard web pode ser acessado em:
http://127.0.0.1:8000/www/index.html

---
## 📊 Dashboard Web
O painel interativo exibe as métricas em tempo real:

👁 Faces detectadas

⏱ Tempo ativo (min)

🔁 Blinks/min (taxa de piscadas)

📈 Piscos (total acumulado)

⚠️ Status de risco (com alerta visual)

📊 Gráfico de alertas (últimas 24h)

🕒 Histórico de eventos

A comunicação entre main.py e o painel é feita via API FastAPI — os dados são enviados continuamente para /status e /events.

## 🎛️ Controles disponíveis
A janela Controles contém sliders para ajustar parâmetros em tempo real:

scaleFactor → precisão da detecção do rosto (1.1–1.4 recomendado)

minNeighbors → confiança mínima p/ aceitar rosto (↑ = menos falsos positivos)

minSize(px) → tamanho mínimo da face detectada em pixels

EAR_thr → sensibilidade do cálculo de piscadas (0.18–0.24 costuma funcionar)

risk_min → minutos até acionar alerta de risco

Atalhos de teclado:

R → resetar tempo e contadores

S → salvar frame (imagem)

H → mostrar/ocultar ajuda

Q ou ESC → sair

---

## 📊 Funcionamento
O sistema detecta rostos usando Haar Cascade e landmarks via MediaPipe.

Calcula o EAR (Eye Aspect Ratio) para medir piscadas.

Monitora:

Blinks/min → taxa de piscadas por minuto.

Tempo ativo (min) → quanto tempo o rosto está sendo detectado continuamente.

Quando os limites são ultrapassados (risk_min ou piscadas anormais), o sistema:

Exibe um alerta visual grande e pulsante.

Emite um beep sonoro (no Windows).

---

## 🚧 Limitações
Requer iluminação adequada e câmera ativada.

Pode gerar falsos positivos com barbas, sombras ou múltiplas pessoas.

Reconhecimento facial com LBPH exige um dataset organizado em pastas (ex.: data/faces/Nome/).

---

## 🔮 Próximos passos
Integrar com uma extensão de navegador para bloquear apostas compulsivas.

Adicionar histórico de sessões (tempo total, pausas realizadas).

Melhorar alertas (dashboard, relatórios, recomendações personalizadas).

---

🧩 Autores

FIAP | IoT & IOB
Projeto desenvolvido por:

Pedro Henrique Alves Guariente 
David de Medeiros Pacheco Junior
Orlando Akio Morii Cardoso