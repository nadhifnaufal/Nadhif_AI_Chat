import streamlit as st
import ollama
from PIL import Image
import io
import time
import os

# Konfigurasi dasar halaman Streamlit
st.set_page_config(page_title="Nadhif AI Chat", layout="wide")

def local_css(file_name, theme):
    # Tentukan nilai spesifik tema
    themes = {
        "Dark": {
            "bg_primary": "#0E1117", "bg_secondary": "#0B0E14",
            "text_primary": "#F0F6FC", "text_secondary": "#8B949E",
            "border_color": "#30363D", "card_bg": "#161B22",
            "card_hover": "#1C2128", "accent_color": "#58A6FF",
            "input_bg": "#0D1117", "shadow": "rgba(0, 0, 0, 0.4)"
        },
        "Light": {
            "bg_primary": "#FFFFFF", "bg_secondary": "#F6F8FA",
            "text_primary": "#111827", "text_secondary": "#4B5563",
            "border_color": "#E5E7EB", "card_bg": "#FFFFFF",
            "card_hover": "#F9FAFB", "accent_color": "#2563EB",
            "input_bg": "#FFFFFF", "shadow": "rgba(0, 0, 0, 0.05)"
        }
    }
    val = themes[theme]
    
    # Buat string variabel CSS
    theme_vars = f"""
    :root {{
        --bg-primary: {val['bg_primary']}; --bg-secondary: {val['bg_secondary']};
        --text-primary: {val['text_primary']}; --text-secondary: {val['text_secondary']};
        --border-color: {val['border_color']}; --card-bg: {val['card_bg']};
        --card-hover: {val['card_hover']}; --accent-color: {val['accent_color']};
        --input-bg: {val['input_bg']}; --shadow: {val['shadow']};
    }}
    """
    
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{theme_vars}\n{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"CSS file not found at {file_name}")

# Konfigurasi Sidebar untuk Tema
with st.sidebar:
    st.markdown("<h2 style='font-size: 1.5rem; margin-bottom: 1rem;'>💠 Script</h2>", unsafe_allow_html=True)
    theme = "Dark"

# Muat stylesheet profesional menggunakan path relatif untuk portabilitas
current_dir = os.path.dirname(os.path.abspath(__file__))
css_path = os.path.join(current_dir, "CSS", "style.css")

local_css(css_path, theme)

with st.sidebar:
    st.divider()

# Inisialisasi penyimpanan multi-chat di session state agar data tidak hilang saat refresh
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    # Membuat ID chat baru menggunakan timestamp jika belum ada chat yang aktif
    new_id = str(time.time())
    st.session_state.all_chats[new_id] = []
    st.session_state.current_chat_id = new_id

# Alias untuk mempermudah akses ke daftar pesan pada chat yang sedang aktif
messages = st.session_state.all_chats[st.session_state.current_chat_id]

# Pengaturan Sidebar
with st.sidebar:
    st.text_input("🔍 Search", placeholder="Search chats...")
    
    # Tombol untuk memulai sesi percakapan baru
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(time.time())
        st.session_state.all_chats[new_id] = []
        st.session_state.current_chat_id = new_id
        st.rerun()
    
    st.divider()
    st.subheader("Chat History")
    # Menampilkan daftar riwayat percakapan sebelumnya
    for chat_id, chat_msgs in reversed(list(st.session_state.all_chats.items())):
        # Mengambil 20 karakter pertama dari pesan pertama sebagai judul di sidebar
        title = chat_msgs[0]["content"][:20] + "..." if chat_msgs else "Empty Chat"
        if st.sidebar.button(title, key=chat_id, use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()

    st.divider()
    st.header("Multimedia")
    # Fitur unggah gambar untuk dianalisis oleh model Vision (LLaVA)
    uploaded_file = st.file_uploader("Upload an image for analysis", type=["png", "jpg", "jpeg"])
    
    # Menambahkan opsi untuk menonaktifkan analisis gambar sementara tanpa menghapus file
    use_vision = False
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        use_vision = st.checkbox("Gunakan Analisis Gambar", value=True)

    st.divider()
    st.info("Current Models:\n- Text: Mistral\n- Vision: LLaVA")

# --- LOGIKA PEMROSESAN INPUT (Dipindahkan ke atas agar UI sinkron) ---
chat_input = st.chat_input("Summarize the latest...")
active_prompt = None

if chat_input:
    active_prompt = chat_input

if active_prompt:
    # Simpan pesan pengguna ke dalam riwayat sebelum tampilan di-render
    messages.append({"role": "user", "content": active_prompt})

# Logika Area Konten Utama
if not messages:
    # Layar Selamat Datang berdasarkan Layout_UI_1.png
    st.markdown("""
        <div class="welcome-container">
            <h1 class="welcome-title">Welcome to Nadhif AI Chat</h1>
            <p class="welcome-subtitle">Ask anything, write code, or analyze images.<br>Start a conversation below to begin.</p>
        </div>
    """, unsafe_allow_html=True)

else:
    # Header Chat Standar ketika riwayat tersedia
    st.markdown("<h3 style='margin-bottom: 2rem;'>AI Chat</h3>", unsafe_allow_html=True)
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Jalankan asisten jika ada prompt baru yang masuk
if active_prompt:
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # Tampilkan indikator berpikir segera
        thinking_html = """
            <div class="thinking-container">
                <div class="thinking-dot"></div>
                <div class="thinking-dot"></div>
                <div class="thinking-dot"></div>
            </div>
        """
        response_placeholder.markdown(thinking_html, unsafe_allow_html=True)
        
        full_response = ""

        try:
            if uploaded_file and use_vision:
                # Logika analisis gambar menggunakan model LLaVA
                image_bytes = uploaded_file.getvalue()
                response = ollama.generate(
                    model='llava',
                    prompt=active_prompt,
                    images=[image_bytes],
                    stream=True
                )
                # Mengalirkan (streaming) respon teks dari model vision
                for chunk in response:
                    full_response += chunk['response']
                    response_placeholder.markdown(full_response + "▌")
            else:
                # Logika chat teks/pemrograman menggunakan model Mistral
                # Mengirim seluruh riwayat pesan agar model memiliki konteks (memory)
                response = ollama.chat(
                    model='mistral',
                    messages=messages,
                    stream=True
                )
                # Mengalirkan (streaming) respon teks dari model bahasa
                for chunk in response:
                    content = chunk['message']['content']
                    full_response += content
                    response_placeholder.markdown(full_response + "▌")

            # Menampilkan respon lengkap setelah streaming selesai
            response_placeholder.markdown(full_response)
            
            # Menyimpan respon asisten ke dalam riwayat
            messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            # Menangani error koneksi ke server Ollama
            st.error(f"Error connecting to Ollama: {e}")
            st.info("Make sure the Ollama application is running in the background.")

if __name__ == "__main__":
    pass