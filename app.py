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
        filters = []
        operators = []  # Список для логических операторов

        add_condition = True
        while add_condition:
            # Выбор столбца
            column = st.selectbox("Выберите столбец", df.columns, key=f"column_{len(filters)}")
            col_type = detect_column_type(df[column])

            if col_type == "datetime":
                df[column] = pd.to_datetime(df[column], errors='coerce')
                min_date, max_date = pd.to_datetime(df[column].min()), pd.to_datetime(df[column].max())
                start, end = st.date_input("Выберите диапазон дат", [min_date, max_date], key=f"date_{len(filters)}")
                filters.append((df[column] >= pd.to_datetime(start)) & (df[column] <= pd.to_datetime(end)))
            elif col_type == "numeric":
                condition = st.selectbox("Выберите условие", ["=", "<", ">", "<=", ">="], key=f"condition_{len(filters)}")
                value = st.text_input(f"Введите значение для {column}", key=f"value_{len(filters)}")
                if value:
                    try:
                        value = float(value)
                        if condition == "=":
                            filters.append(df[column] == value)
                        elif condition == "<":
                            filters.append(df[column] < value)
                        elif condition == ">":
                            filters.append(df[column] > value)
                        elif condition == "<=":
                            filters.append(df[column] <= value)
                        elif condition == ">=":
                            filters.append(df[column] >= value)
                    except ValueError:
                        st.warning(f"Введите корректное числовое значение для {column}")
            else:
                selected = st.multiselect(f"Выберите значения для {column}", sorted(df[column].dropna().unique().astype(str)), key=f"selected_{len(filters)}")
                filters.append(df[column].astype(str).isin(selected))

            # Добавление логического оператора
            if len(filters) > 1:
                logic_op = st.selectbox("Логический оператор", ["И", "ИЛИ"], index=0, key=f"logic_{len(filters)}")
                operators.append(logic_op)

            # Кнопка для добавления нового условия
            add_condition = st.button("Добавить условие", key=f"add_condition_{len(filters)}")
            if not add_condition:
                break

        if filters:
            # Применение логического оператора к фильтрам
            combined_filter = filters[0]
            for i in range(1, len(filters)):
                if operators[i-1] == "И":
                    combined_filter &= filters[i]
                else:
                    combined_filter |= filters[i]

            return df[combined_filter]

        st.warning("Выберите метод фильтрации и условия")
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
