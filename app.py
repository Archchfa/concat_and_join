import streamlit as st
import pandas as pd
from io import BytesIO
import time
import streamlit.components.v1 as components

st.set_page_config(page_title="Объединение CSV", layout="centered")
st.title("✨ Объединение CSV-файлов")

# Визуальный эффект заголовка
components.html("""
    <style>
        h1 {
            animation: glow 1.5s infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 10px #00c3ff; }
            to { text-shadow: 0 0 20px #00c3ff, 0 0 30px #00c3ff; }
        }
    </style>
""", height=0)

uploaded_files = st.file_uploader(
    "Загрузите CSV-файлы для объединения", 
    type="csv", 
    accept_multiple_files=True
)

output_filename = st.text_input("Введите имя для итогового файла (без расширения)", value="combined")

if uploaded_files and output_filename:
    dfs = []
    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception as e:
            st.error(f"Ошибка при чтении файла {file.name}: {e}")

    if dfs:
        with st.spinner("🔄 Объединение файлов..."):
            combined_df = pd.concat(dfs, ignore_index=True)
            time.sleep(1.5)  # Небольшая задержка для эффекта

        st.balloons()  # 🎈 Анимация успеха
        st.success("✅ Файлы успешно объединены!")
        st.dataframe(combined_df.head())

        # Подготовка файла для скачивания
        buffer = BytesIO()
        combined_df.to_csv(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Скачать объединённый CSV",
            data=buffer,
            file_name=f"{output_filename}.csv",
            mime="text/csv"
        )
