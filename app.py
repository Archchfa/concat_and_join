import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Объединение CSV", layout="centered")
st.title("Объединение CSV-файлов")

uploaded_files = st.file_uploader(
    "Загрузите CSV-файлы для объединения", 
    type="csv", 
    accept_multiple_files=True
)

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception as e:
            st.error(f"Ошибка при чтении файла {file.name}: {e}")

    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        st.success("Файлы успешно объединены!")
        st.dataframe(combined_df.head())

        # Подготовка файла для скачивания
        buffer = BytesIO()
        combined_df.to_csv(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="Скачать объединённый CSV",
            data=buffer,
            file_name="combined.csv",
            mime="text/csv"
        )
