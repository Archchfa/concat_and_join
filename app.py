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
    dfs = []
    column_sets = []
    for file in files:
        df = load_csv(file)
        if df.empty:
            st.warning(f"Файл {file.name} пропущен")
            continue
        dfs.append((file.name, df))
        column_sets.append(set(df.columns))

    if len(dfs) < 2:
        st.error("❌ Недостаточно файлов для объединения")
        return pd.DataFrame()

    common_columns = set.intersection(*column_sets)
    if not common_columns:
        st.error("❌ Нет общих столбцов во всех файлах")
        return pd.DataFrame()

    merge_column = st.selectbox("Выберите столбец для объединения:", sorted(common_columns))

    for i in range(len(dfs)):
        dfs[i] = (dfs[i][0], dfs[i][1].copy())
        dfs[i][1][merge_column] = dfs[i][1][merge_column].astype(str)

    result = dfs[0][1]
    for name, df in dfs[1:]:
        df[merge_column] = df[merge_column].astype(str)
        result = pd.merge(result, df, on=merge_column, how="outer", suffixes=('', '_dup'))
        result = result.loc[:, ~result.columns.str.endswith('_dup')]

    result = result.loc[:, ~result.columns.str.fullmatch(r'Unnamed.*')]
    return result

def download_link(df, filename="результат.csv"):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button("📥 Скачать результат", buffer, file_name=filename, mime="text/csv")

st.sidebar.title("Навигация")
option = st.sidebar.radio("Выберите раздел", ["Объединить файлы"], key="menu_option")

if option == "Объединить файлы":
    uploaded_files = st.file_uploader("Загрузите CSV файлы", type="csv", accept_multiple_files=True)
    if uploaded_files:
        merged_df = merge_files(uploaded_files)
        if not merged_df.empty:
            st.dataframe(merged_df)
            download_link(merged_df, "объединенные_файлы.csv")
