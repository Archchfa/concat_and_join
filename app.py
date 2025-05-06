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

combined_df = None

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
            time.sleep(1.5)

        st.balloons()
        st.success("✅ Файлы успешно объединены!")
        st.dataframe(combined_df.head())

        buffer = BytesIO()
        combined_df.to_csv(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Скачать объединённый CSV",
            data=buffer,
            file_name=f"{output_filename}.csv",
            mime="text/csv"
        )

# --- Новый раздел: Поиск пересечений ---
if combined_df is not None:
    st.header("🔍 Ищем пересекающиеся значения")
    new_file = st.file_uploader("Загрузите файл для сравнения", type="csv", key="compare")

    if new_file is not None:
        try:
            compare_df = pd.read_csv(new_file)
            st.success("Файл для сравнения успешно загружен!")

            col1 = st.selectbox("Выберите столбец из объединённого файла", combined_df.columns)
            col2 = st.selectbox("Выберите столбец из нового файла", compare_df.columns)

            intersect_output_filename = st.text_input("Введите имя для файла с пересечениями (без расширения)", value="intersected_rows")

            if st.button("🔎 Найти пересечения"):
                intersection_values = pd.Series(list(set(combined_df[col1]) & set(compare_df[col2])))
                percent = len(intersection_values) / len(compare_df[col2].dropna()) * 100
                st.info(f"✅ Найдено {len(intersection_values)} пересечений — это {percent:.2f}% от столбца сравнения.")

                filtered_df = compare_df[compare_df[col2].isin(intersection_values)]
                st.dataframe(filtered_df.head())

                result_buffer = BytesIO()
                filtered_df.to_csv(result_buffer, index=False)
                result_buffer.seek(0)

                st.download_button(
                    label="⬇️ Скачать файл с пересечениями",
                    data=result_buffer,
                    file_name=f"{intersect_output_filename}.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Ошибка при обработке файла: {e}")
