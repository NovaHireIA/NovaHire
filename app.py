import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
from streamlit_mic_recorder import mic_recorder
from pypdf import PdfReader

# -----------------------------
# CARGAR API KEY
# -----------------------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("No se encontró la API KEY en el archivo .env")
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
area = st.selectbox("Selecciona tu área:", ["Sistemas", "Administración"])

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
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

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

    # MICRÓFONO SOLO UNA VEZ
    if not st.session_state.mic_used:

        audio = mic_recorder(
            start_prompt="🎤 Hablar",
            stop_prompt="⏹️ Detener",
            use_container_width=True
        )

    else:
        st.info("El micrófono solo puede usarse una vez durante la entrevista.")

    user_input = st.chat_input("Responde a NOVAHIRE...")

    # -----------------------------
    # TRANSCRIPCIÓN DE VOZ
    # -----------------------------
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

    # -----------------------------
    # PROCESAR RESPUESTA
    # -----------------------------
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

    EVALUACIÓN FINAL:
    breve explicación

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