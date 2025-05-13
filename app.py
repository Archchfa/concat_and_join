import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Анализ CSV файлов", layout="wide")
st.title("📊 Инструмент для анализа CSV файлов")

def load_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Ошибка при чтении файла {uploaded_file.name}: {e}")
        return pd.DataFrame()

def detect_column_type(series):
    try:
        pd.to_numeric(series.dropna())
        return "numeric"
    except:
        try:
            pd.to_datetime(series.dropna(), errors='raise')
            return "datetime"
        except:
            return "string"

def download_link(df, filename="результат.csv"):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button("📥 Скачать результат", buffer, file_name=filename, mime="text/csv")

def plot_data(df):
    st.subheader("📈 Построение графика")
    chart_type = st.selectbox("Тип графика", ["Столбчатая диаграмма", "Линейный график", "Круговая диаграмма"])
    group_by = st.multiselect("Группировать по", df.columns, default=[])
    value_col = st.selectbox("Агрегируемый столбец", df.columns)
    agg_func = st.selectbox("Агрегация", ["Сумма", "Количество уникальных", "Среднее"])

    if not group_by:
        st.warning("Выберите хотя бы одну колонку для группировки")
        return

    for col in group_by:
        if detect_column_type(df[col]) == "datetime":
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    if agg_func == "Сумма":
        grouped = df.groupby(group_by)[value_col].sum().reset_index()
    elif agg_func == "Количество уникальных":
        grouped = df.groupby(group_by)[value_col].nunique().reset_index()
    elif agg_func == "Среднее":
        grouped = df.groupby(group_by)[value_col].mean().reset_index()
    else:
        grouped = df

    fig = None
    color = group_by[1] if len(group_by) > 1 else None
    if chart_type == "Столбчатая диаграмма":
        fig = px.bar(grouped, x=group_by[0], y=value_col, color=color)
    elif chart_type == "Линейный график":
        fig = px.line(grouped, x=group_by[0], y=value_col, color=color)
    elif chart_type == "Круговая диаграмма":
        fig = px.pie(grouped, names=group_by[0], values=value_col)

    if fig:
        st.plotly_chart(fig, use_container_width=True)

# Интерфейс
st.sidebar.title("Навигация")
option = st.sidebar.radio("Выберите раздел", [
    "Построить график"
], key="menu_option")

if option == "Построить график":
    uploaded_file = st.file_uploader("Загрузите CSV файл", type="csv")
    if uploaded_file:
        df = load_csv(uploaded_file)
        plot_data(df)
