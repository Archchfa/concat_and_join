import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Анализ CSV файлов", layout="wide")

st.title("📊 Инструмент для анализа CSV файлов")

# Убираем анимации
st.markdown("<style>div[data-testid='stNotification'] {display: none;}</style>", unsafe_allow_html=True)

# --- Функции ---
def load_csv(uploaded_file):
    return pd.read_csv(uploaded_file)

def merge_files(files):
    dfs = [load_csv(file) for file in files]
    return pd.concat(dfs, ignore_index=True)

def detect_column_type(series):
    try:
        pd.to_datetime(series)
        return "datetime"
    except (ValueError, TypeError):
        try:
            pd.to_numeric(series)
            return "numeric"
        except ValueError:
            return "string"

def filter_dataframe():
    uploaded_file = st.file_uploader("Загрузите CSV файл для фильтрации", type="csv", key="filter_file")
    if uploaded_file:
        df = load_csv(uploaded_file)
        filter_conditions = []
        logic_ops = []

        # Добавление условий
        add_condition = st.button("Добавить условие")
        
        if 'filter_blocks' not in st.session_state:
            st.session_state['filter_blocks'] = []

        if add_condition:
            # Запоминаем блоки условий в сессии
            st.session_state['filter_blocks'].append({
                'column': st.selectbox("Выберите столбец для фильтрации", df.columns),
                'operation': st.selectbox("Выберите логический оператор", ["=", "<", ">", "<=", ">="]),
                'value': st.text_input("Введите значение для условия"),
            })

        for block in st.session_state['filter_blocks']:
            column = block['column']
            operation = block['operation']
            value = block['value']
            if value:
                col_type = detect_column_type(df[column])

                if col_type == "numeric" and value.replace('.', '', 1).isdigit():
                    value = float(value)

                if operation == "=":
                    filter_conditions.append(df[column] == value)
                elif operation == "<":
                    filter_conditions.append(df[column] < value)
                elif operation == ">":
                    filter_conditions.append(df[column] > value)
                elif operation == "<=":
                    filter_conditions.append(df[column] <= value)
                elif operation == ">=":
                    filter_conditions.append(df[column] >= value)

        # Соединение условий с логическими операторами
        if filter_conditions:
            logic_op = st.selectbox("Логический оператор для объединения условий", ["И", "ИЛИ"], index=0)
            if logic_op == "И":
                df_filtered = df[pd.concat(filter_conditions, axis=1).all(axis=1)]
            else:
                df_filtered = df[pd.concat(filter_conditions, axis=1).any(axis=1)]
            st.dataframe(df_filtered)
            return df_filtered

    return None

def download_link(df, filename="результат.csv"):
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button("📥 Скачать результат", buffer, file_name=filename, mime="text/csv")

def plot_data(df):
    st.subheader("📈 Построение графика")
    
    chart_type = st.selectbox("Тип графика", ["Гистограмма", "Столбчатая диаграмма", "Линейный график", "Круговая диаграмма"])
    x_col = st.selectbox("Ось X (категории)", df.columns)
    y_col = st.selectbox("Ось Y (значения)", df.columns) if chart_type != "Круговая диаграмма" else None
    
    # Добавим возможность выбора дополнительных параметров
    color_col = st.selectbox("Цветовая категория", df.columns) if chart_type not in ["Круговая диаграмма"] else None
    agg_type = st.selectbox("Тип агрегации", ["Количество уникальных", "Общее количество"])

    if agg_type == "Количество уникальных":
        data = df.groupby(x_col)[y_col].nunique().reset_index(name="Значение") if y_col else df[x_col].value_counts().reset_index(name="Значение")
    else:
        data = df.groupby(x_col)[y_col].count().reset_index(name="Значение") if y_col else df[x_col].value_counts().reset_index(name="Значение")

    fig = None
    if chart_type == "Гистограмма":
        fig = px.histogram(df, x=x_col)
    elif chart_type == "Столбчатая диаграмма":
        fig = px.bar(data, x=x_col, y="Значение", color=color_col)
    elif chart_type == "Линейный график":
        fig = px.line(data, x=x_col, y="Значение", color=color_col)
    elif chart_type == "Круговая диаграмма":
        fig = px.pie(data, names="index" if "index" in data.columns else x_col, values="Значение")

    if fig:
        st.plotly_chart(fig, use_container_width=True)

# --- Основная логика ---
st.sidebar.header("Выберите действие")
option = st.sidebar.radio("", [
    "Объединить файлы",
    "Фильтрация данных",
    "Построить график",
    "Построить график из одного файла"
])

if option == "Объединить файлы":
    uploaded_files = st.file_uploader("Загрузите CSV файлы для объединения", type="csv", accept_multiple_files=True)
    if uploaded_files:
        merged_df = merge_files(uploaded_files)
        st.dataframe(merged_df)
        st.session_state['data'] = merged_df
        download_link(merged_df, "объединенные_файлы.csv")

elif option == "Фильтрация данных":
    filtered_df = filter_dataframe()
    if filtered_df is not None:
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

elif option == "Построить график из одного файла":
    uploaded_file = st.file_uploader("Загрузите CSV файл для визуализации", type="csv")
    if uploaded_file:
        df = load_csv(uploaded_file)
        plot_data(df)
