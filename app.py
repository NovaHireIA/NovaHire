import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
from streamlit_mic_recorder import mic_recorder

# -----------------------------
# CARGAR API KEY
# -----------------------------
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
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
# ESTILO FUTURISTA
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

/* Arregla el cuadro blanco del micrófono */
[data-testid="stAudioInput"] {
    background-color: transparent;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='avatar'>🤖</div>", unsafe_allow_html=True)
st.title("NOVAHIRE - IA Entrevistadora")
st.write("Modo Gamer Activado 🎮")

# -----------------------------
# ESTADO
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "question_count" not in st.session_state:
    st.session_state.question_count = 0

if "scores" not in st.session_state:
    st.session_state.scores = []

if "started" not in st.session_state:
    st.session_state.started = False

if "finished" not in st.session_state:
    st.session_state.finished = False

if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

if "mic_used" not in st.session_state:
    st.session_state.mic_used = False

area = st.selectbox("Selecciona tu área:", ["Sistemas", "Administración"])

# -----------------------------
# INICIAR
# -----------------------------
if st.button("Iniciar Entrevista") and not st.session_state.started:
    st.session_state.started = True
    st.session_state.finished = False
    st.session_state.messages = []
    st.session_state.question_count = 0
    st.session_state.scores = []
    st.session_state.mic_used = False
    st.session_state.last_audio_id = None

    system_prompt = f"""
    Eres NOVAHIRE, una IA holográfica futurista.
    Entrevista para el área de {area}.

    Después de cada respuesta:
    - Evalúa del 1 al 10
    - Escribe: PUNTUACIÓN: X/10
    - Explica brevemente la razón
    - Haz la siguiente pregunta

    Después de 5 preguntas:
    - Da evaluación final
    """

    st.session_state.messages.append({"role": "system", "content": system_prompt})

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
# BARRA DE PUNTUACIÓN
# -----------------------------
if st.session_state.scores:
    promedio = sum(st.session_state.scores) / len(st.session_state.scores)
    st.subheader("Nivel del Candidato")
    st.progress(int(promedio * 10))
    st.write(f"⭐ Promedio actual: {round(promedio,2)}/10")

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
        st.info("Por motivos de librerías, se rehabilitará el micrófono en la siguiente entrevista.")

    # INPUT TEXTO
    user_input = st.chat_input("Responde a NOVAHIRE...")

    # SI HABLA
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
        st.session_state.messages.append({"role": "user", "content": user_input})
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
# FINAL
# -----------------------------
if st.session_state.finished:
    promedio_final = sum(st.session_state.scores) / len(st.session_state.scores)
    st.success("🎯 ENTREVISTA TERMINADA")
    st.write(f"🏆 Puntaje Final: {round(promedio_final,2)}/10")

    if promedio_final >= 8:
        st.balloons()
        st.write("🔥 Nivel alto, excelente desempeño.")
    elif promedio_final >= 6:
        st.write("👍 Buen nivel, pero puedes mejorar algunos puntos.")
    else:
        st.write("⚠️ Necesitas practicar más. No te rindas.")