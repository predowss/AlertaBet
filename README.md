# 🎰 Alerta Bet BR 🚨

Aplicação local em **Python + OpenCV + MediaPipe** para detecção de rosto e monitoramento de fadiga.  
Criada como parte de um desafio prático, o objetivo é identificar **comportamentos de risco em apostas online** e incentivar o usuário a **fazer pausas**.

---

## 🎯 Objetivo
Muitos usuários em ambientes de apostas perdem a noção do tempo e apresentam sinais de fadiga ocular.  
Este projeto detecta o rosto em tempo real, mede piscadas, monitora o tempo ativo e emite **alertas visuais e sonoros** quando o uso ultrapassa limites configuráveis.

---

## ⚙️ Tecnologias utilizadas
- **Python 3.10+**
- **OpenCV** (`opencv-python` e `opencv-contrib-python`)
- **MediaPipe** (landmarks faciais para olhos)
- **NumPy**
- **PIL/Pillow** (renderização de legendas)
- **Winsound** (apenas no Windows, para o alerta sonoro)

---

## 📂 Estrutura do projeto
ALERTABET/
├── src/
│ ├── main.py # aplicação principal (UI, lógica de risco, alertas)
│ ├── risk_model.py # regras de risco (tempo ativo, piscadas/minuto)
│ ├── utils.py # funções auxiliares e interface gráfica
│ ├── face_id.py # reconhecimento facial (opcional, LBPH)
│ └── data/faces/ # dataset de rostos (para testes do face_id)
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

---

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