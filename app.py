import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Анализ CSV файлов", layout="wide")

st.title("\U0001F4CA Инструмент для анализа CSV файлов")

# Убираем анимации
st.markdown("<style>div[data-testid='stNotification'] {display: none;}</style>", unsafe_allow_html=True)

# --- Функции ---
def load_csv(uploaded_file):
    return pd.read_csv(uploaded_file)

def merge_files(files):
    dfs = [load_csv(file) for file in files]
    return pd.concat(dfs, ignore_index=True)

def filter_dataframe(df, method):
    if method == "Поиск по значениям":
        search_type = st.radio("Выберите способ поиска:", ["Ввести вручную", "Загрузить файл со значениями", "По условию"])

        if search_type == "Ввести вручную":
            column = st.selectbox("Выберите столбец для поиска", df.columns)
            values = st.text_input("Введите значения через запятую:").split(',')
            values = [v.strip() for v in values if v.strip()]
            return df[df[column].astype(str).isin(values)]

        elif search_type == "Загрузить файл со значениями":
            uploaded = st.file_uploader("Загрузите файл со значениями", type="csv", key="value_file")
            if uploaded:
                value_df = load_csv(uploaded)
                value_col = st.selectbox("Выберите столбец со значениями", value_df.columns)
                target_col = st.selectbox("Выберите столбец для поиска в основном файле", df.columns)
                return df[df[target_col].astype(str).isin(value_df[value_col].astype(str))]

        elif search_type == "По условию":
            column = st.selectbox("Выберите столбец", df.columns)
            condition = st.selectbox("Выберите условие", ["=", "<", ">", "<=", ">="])
            value = st.text_input("Введите значение")
            if value:
                try:
                    value = float(value)
                    if condition == "=":
                        return df[df[column] == value]
                    elif condition == "<":
                        return df[df[column] < value]
                    elif condition == ">":
                        return df[df[column] > value]
                    elif condition == "<=":
                        return df[df[column] <= value]
                    elif condition == ">=":
                        return df[df[column] >= value]
                except ValueError:
                    st.warning("Введите числовое значение")
    return df

def download_link(df, filename="результат.csv"):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button("\U0001F4E5 Скачать результат", buffer, file_name=filename, mime="text/csv")

def plot_data(df):
    st.subheader("\U0001F4C8 Построение графика")
    chart_type = st.selectbox("Тип графика", ["Гистограмма", "Столбчатая диаграмма", "Линейный график"])
    x_col = st.selectbox("Ось X (категории)", df.columns)
    y_col = st.selectbox("Ось Y (значения)", df.columns)
    agg_type = st.selectbox("Тип агрегации", ["Количество уникальных", "Общее количество"])

    if agg_type == "Количество уникальных":
        data = df.groupby(x_col)[y_col].nunique().reset_index(name="Значение")
    else:
        data = df.groupby(x_col)[y_col].count().reset_index(name="Значение")

    fig = None
    if chart_type == "Гистограмма":
        fig = px.histogram(df, x=x_col)
    elif chart_type == "Столбчатая диаграмма":
        fig = px.bar(data, x=x_col, y="Значение")
    elif chart_type == "Линейный график":
        fig = px.line(data, x=x_col, y="Значение")

    if fig:
        st.plotly_chart(fig, use_container_width=True)

# --- Основная логика ---
st.sidebar.header("Выберите действие")
option = st.sidebar.radio("", [
    "Объединить файлы",
    "Фильтрация данных",
    "Построить график"
])

if option == "Объединить файлы":
    uploaded_files = st.file_uploader("Загрузите CSV файлы для объединения", type="csv", accept_multiple_files=True)
    if uploaded_files:
        merged_df = merge_files(uploaded_files)
        st.dataframe(merged_df)
        st.session_state['data'] = merged_df
        download_link(merged_df, "объединенные_файлы.csv")

elif option == "Фильтрация данных":
    if 'data' not in st.session_state:
        uploaded = st.file_uploader("Загрузите CSV файл", type="csv")
        if uploaded:
            df = load_csv(uploaded)
            st.session_state['data'] = df
    if 'data' in st.session_state:
        df = st.session_state['data']
        filtered_df = filter_dataframe(df, method="Поиск по значениям")
        st.dataframe(filtered_df)
        st.session_state['filtered'] = filtered_df
        download_link(filtered_df, "отфильтрованные_данные.csv")

elif option == "Построить график":
    if 'filtered' in st.session_state:
        plot_data(st.session_state['filtered'])
    elif 'data' in st.session_state:
        plot_data(st.session_state['data'])
    else:
        st.warning("Сначала загрузите или объедините данные")
