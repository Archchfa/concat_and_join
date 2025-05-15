import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Анализ CSV файлов", layout="wide")
st.title("📊 Инструмент для анализа CSV файлов")

def load_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
        df.columns = df.iloc[0].astype(str).str.strip()
        df = df[1:].reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Ошибка при чтении файла {uploaded_file.name}: {e}")
        return pd.DataFrame()

def merge_files(files):
    if len(files) != 2:
        st.error("❌ Для объединения нужно загрузить ровно 2 файла")
        return pd.DataFrame()

    df1 = load_csv(files[0])
    df2 = load_csv(files[1])

    if df1.empty or df2.empty:
        st.warning("Один из файлов пуст или не загружен корректно")
        return pd.DataFrame()

    st.write(f"Файл 1: {files[0].name}")
    merge_col_1 = st.selectbox("Выберите столбец для объединения из первого файла:", df1.columns, key="merge_col_1")

    st.write(f"Файл 2: {files[1].name}")
    merge_col_2 = st.selectbox("Выберите столбец для объединения из второго файла:", df2.columns, key="merge_col_2")

    df1[merge_col_1] = df1[merge_col_1].astype(str)
    df2[merge_col_2] = df2[merge_col_2].astype(str)

    df1 = df1.rename(columns={merge_col_1: "_merge_key"})
    df2 = df2.rename(columns={merge_col_2: "_merge_key"})

    result = pd.merge(df1, df2, on="_merge_key", how="outer", suffixes=('', '_dup'))
    result = result.loc[:, ~result.columns.str.endswith('_dup')]
    result = result.loc[:, ~result.columns.str.fullmatch(r'Unnamed.*')]
    result = result.rename(columns={"_merge_key": f"{merge_col_1}/{merge_col_2}"})

    return result

def download_link(df, filename="результат.csv"):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button("📥 Скачать результат", buffer, file_name=filename, mime="text/csv")

st.sidebar.title("Навигация")
option = st.sidebar.radio("Выберите раздел", ["Объединить файлы"], key="menu_option")

if option == "Объединить файлы":
    uploaded_files = st.file_uploader("Загрузите 2 CSV файла", type="csv", accept_multiple_files=True)
    if uploaded_files:
        merged_df = merge_files(uploaded_files)
        if not merged_df.empty:
            st.dataframe(merged_df)
            download_link(merged_df, "объединенные_файлы.csv")
