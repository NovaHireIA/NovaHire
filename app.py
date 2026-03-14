import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
from streamlit_mic_recorder import mic_recorder
from pypdf import PdfReader

# -----------------------------
# CARGAR API KEY LOCAL (.env)
# -----------------------------
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("No se encontró la API KEY. Verifica tu archivo .env")
    st.stop()

client = OpenAI(api_key=api_key)

# -----------------------------
# CONFIGURACIÓN
# -----------------------------
st.set_page_config(
    page_title="NOVAHIRE - Entrevista Gamer",
    page_icon="🤖",
    layout="centered"
)

# -----------------------------
# ESTILO
# -----------------------------
st.markdown("""
<style>

body {
    background-color: #0f172a;
}

/* Avatar principal */
.avatar {
    font-size: 80px;
    text-align: center;
    color: #00f7ff;
    animation: glow 1.5s infinite alternate;
}

@keyframes glow {
    from { text-shadow: 0 0 10px #00f7ff; }
    to { text-shadow: 0 0 30px #00f7ff; }
}

/* CONTENEDOR CHAT */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 28px;
    margin-top: 25px;
}

/* FILA IA */
.assistant-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}

/* ICONO IA */
.assistant-icon {
    font-size: 28px;
}

/* BURBUJA IA */
.assistant-msg {
    background: #1e293b;
    color: #e2e8f0;
    padding: 16px;
    border-radius: 14px;
    max-width: 80%;
    font-size: 15px;
    border: 1px solid #334155;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

/* FILA USUARIO */
.user-row {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}

/* ICONO USUARIO */
.user-icon {
    font-size: 26px;
}

/* BURBUJA USUARIO */
.user-msg {
    background: linear-gradient(135deg,#15803d,#166534);
    color: white;
    padding: 16px;
    border-radius: 14px;
    max-width: 80%;
    font-size: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

</style>
""", unsafe_allow_html=True)

st.markdown("<div class='avatar'>🤖</div>", unsafe_allow_html=True)
st.title("NOVAHIRE - IA Entrevistadora")
st.write("Modo Gamer Activado 🎮")

# -----------------------------
# SESSION STATE
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "scores" not in st.session_state:
    st.session_state.scores = []

if "question_count" not in st.session_state:
    st.session_state.question_count = 0

if "started" not in st.session_state:
    st.session_state.started = False

if "finished" not in st.session_state:
    st.session_state.finished = False

if "cv_text" not in st.session_state:
    st.session_state.cv_text = None

if "cv_score" not in st.session_state:
    st.session_state.cv_score = None

if "cv_evaluated" not in st.session_state:
    st.session_state.cv_evaluated = False

if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

if "mic_used" not in st.session_state:
    st.session_state.mic_used = False

# -----------------------------
# SELECCIÓN ÁREA
# -----------------------------
areas_empresa = [
    "Sistemas",
    "Administración",
    "Contabilidad",
    "Producción",
    "Procesos",
    "Recursos Humanos",
    "Logística"
]

area = st.selectbox("Selecciona tu área:", areas_empresa)

# -----------------------------
# SUBIR CV
# -----------------------------
st.subheader("📄 Adjunta tu Curriculum Vitae")

uploaded_file = st.file_uploader(
    "Adjunta tu Curriculum Vitae (PDF)",
    type=["pdf"]
)

if uploaded_file and not st.session_state.cv_evaluated:

    with st.spinner("Analizando CV..."):

        pdf_reader = PdfReader(uploaded_file)

        texto_cv = ""

        for page in pdf_reader.pages:
            texto = page.extract_text()
            if texto:
                texto_cv += texto

        st.session_state.cv_text = texto_cv

        prompt_cv = f"""
Analiza este currículum para el puesto de {area}.

Evalúa experiencia, habilidades y educación.

Da una puntuación del 1 al 10.

Responde EXACTAMENTE así:

PUNTUACIÓN CV: X/10
OPINIÓN: breve análisis del perfil
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt_cv + texto_cv[:2000]}
            ]
        )

        resultado = response.choices[0].message.content

        st.success("CV Analizado")
        st.write(resultado)

        match = re.search(r"PUNTUACIÓN CV:\s*(\d+)/10", resultado)

        if match:
            st.session_state.cv_score = int(match.group(1))

        st.session_state.cv_evaluated = True

# -----------------------------
# INICIAR ENTREVISTA
# -----------------------------
if st.button("Iniciar Entrevista") and not st.session_state.started:

    st.session_state.started = True
    st.session_state.messages = []
    st.session_state.scores = []
    st.session_state.question_count = 0
    st.session_state.finished = False
    st.session_state.mic_used = False

    system_prompt = f"""
Eres NOVAHIRE, una IA entrevistadora profesional.

Estás entrevistando para el área de {area}.

Después de cada respuesta:
- Evalúa del 1 al 10
- Escribe: PUNTUACIÓN: X/10
- Explica brevemente
- Haz la siguiente pregunta

Haz 5 preguntas.
"""

    st.session_state.messages.append(
        {"role": "system", "content": system_prompt}
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages
    )

    st.session_state.messages.append(
        {"role": "assistant", "content": response.choices[0].message.content}
    )

# -----------------------------
# MOSTRAR CHAT
# -----------------------------
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

for msg in st.session_state.messages:

    if msg["role"] == "assistant":

        st.markdown(f"""
        <div class="assistant-row">
            <div class="assistant-icon">🤖</div>
            <div class="assistant-msg">
                {msg['content']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif msg["role"] == "user":

        st.markdown(f"""
        <div class="user-row">
            <div class="user-msg">
                {msg['content']}
            </div>
            <div class="user-icon">👤</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# RESPUESTA USUARIO
# -----------------------------
if (
    st.session_state.started
    and not st.session_state.finished
    and st.session_state.question_count < 5
):

    st.write("✏️ Escribe tu respuesta o usa el micrófono")

    audio = None

    if not st.session_state.mic_used:
        audio = mic_recorder(
            start_prompt="🎤 Hablar",
            stop_prompt="⏹️ Detener",
            use_container_width=True
        )
    else:
        st.info("El micrófono solo puede usarse una vez durante la entrevista.")

    user_input = st.chat_input("Responde a NOVAHIRE...")

    if audio and audio["id"] != st.session_state.last_audio_id:

        st.session_state.last_audio_id = audio["id"]
        st.session_state.mic_used = True

        audio_bytes = audio["bytes"]

        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", audio_bytes)
        )

        user_input = transcription.text
        st.write("🗣️ Dijiste:", user_input)

    if user_input:

        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        st.session_state.question_count += 1

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages
        )

        ai_reply = response.choices[0].message.content

        st.session_state.messages.append(
            {"role": "assistant", "content": ai_reply}
        )

        match = re.search(r"PUNTUACIÓN:\s*(\d+)/10", ai_reply)

        if match:
            score = int(match.group(1))
            st.session_state.scores.append(score)

        if st.session_state.question_count >= 5:
            st.session_state.finished = True

        st.rerun()

# -----------------------------
# EVALUACIÓN FINAL
# -----------------------------
if st.session_state.finished:

    respuestas = ""

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            respuestas += msg["content"] + "\n"

    cv_text = "No se adjuntó curriculum."

    if st.session_state.cv_text:
        cv_text = st.session_state.cv_text[:2000]

    prompt_final = f"""
Eres un reclutador profesional.

Evalúa al candidato considerando:
- Sus respuestas en la entrevista
- Su curriculum (si existe)

RESPUESTAS:
{respuestas}

CURRICULUM:
{cv_text}

Responde EXACTAMENTE así:

EVALUACIÓN FINAL: breve explicación
PUNTUACIÓN FINAL: X/10
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt_final}
        ]
    )

    resultado = response.choices[0].message.content

    st.success("🎯 ENTREVISTA TERMINADA")
    st.write(resultado)

    match = re.search(r"PUNTUACIÓN FINAL:\s*(\d+)/10", resultado)

    if match:

        score = int(match.group(1))

        st.subheader("Nivel del Candidato")
        st.progress(score * 10)

        if score >= 8:
            st.balloons()
            st.write("🔥 Excelente candidato")

        elif score >= 6:
            st.write("👍 Buen candidato")

        else:
            st.write("⚠️ El candidato necesita mejorar habilidades")