import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Анализ CSV файлов", layout="wide")
st.title("📊 Инструмент для анализа CSV файлов")
st.markdown("<style>div[data-testid='stNotification'] {display: none;}</style>", unsafe_allow_html=True)

# --- Функции ---
def load_csv(uploaded_file):
    try:
        return pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
    except Exception as e:
        st.error(f"Ошибка при чтении файла {uploaded_file.name}: {e}")
        return pd.DataFrame()

def merge_files(files, merge_on):
    dfs = []
    for file in files:
        df = load_csv(file)
        if df.empty:
            st.warning(f"Файл {file.name} пустой или содержит ошибки. Пропущен.")
            continue
        if merge_on not in df.columns:
            st.warning(f"В файле {file.name} нет столбца '{merge_on}'. Пропущен.")
            continue
        dfs.append(df)
    if len(dfs) < 2:
        st.error("Недостаточно файлов с нужным столбцом для объединения.")
        return pd.DataFrame()
    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=merge_on, how="outer")
    return merged_df

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
        if df.empty:
            return None

        search_type = st.radio("Выберите способ поиска:", ["Ввести вручную", "Загрузить файл со значениями", "По условию"])
        if search_type == "Ввести вручную":
            column = st.selectbox("Выберите столбец для поиска", df.columns)
            col_type = detect_column_type(df[column])
            if col_type == "string":
                selected = st.multiselect("Выберите значения", sorted(df[column].dropna().unique().astype(str)))
                return df[df[column].astype(str).isin(selected)]
            else:
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
            col_type = detect_column_type(df[column])
            logic_op = st.selectbox("Логический оператор", ["И", "ИЛИ"], index=0)
            df[column] = df[column].copy()
            filters = []

            if col_type == "datetime":
                df[column] = pd.to_datetime(df[column], errors='coerce')
                min_date, max_date = pd.to_datetime(df[column].min()), pd.to_datetime(df[column].max())
                start, end = st.date_input("Выберите диапазон дат", [min_date, max_date])
                filters.append((df[column] >= pd.to_datetime(start)) & (df[column] <= pd.to_datetime(end)))

            elif col_type == "numeric":
                condition1 = st.selectbox("Условие 1", ["=", "<", ">", "<=", ">="])
                value1 = st.text_input("Значение 1")
                condition2 = st.selectbox("Условие 2 (опционально)", ["Нет", "=", "<", ">", "<=", ">="])
                value2 = st.text_input("Значение 2")

                if value1:
                    try:
                        value1 = float(value1)
                        if condition1 == "=":
                            filters.append(df[column] == value1)
                        elif condition1 == "<":
                            filters.append(df[column] < value1)
                        elif condition1 == ">":
                            filters.append(df[column] > value1)
                        elif condition1 == "<=":
                            filters.append(df[column] <= value1)
                        elif condition1 == ">=":
                            filters.append(df[column] >= value1)
                    except ValueError:
                        st.warning("Введите корректное числовое значение для первого условия")

                if condition2 != "Нет" and value2:
                    try:
                        value2 = float(value2)
                        if condition2 == "=":
                            filters.append(df[column] == value2)
                        elif condition2 == "<":
                            filters.append(df[column] < value2)
                        elif condition2 == ">":
                            filters.append(df[column] > value2)
                        elif condition2 == "<=":
                            filters.append(df[column] <= value2)
                        elif condition2 == ">=":
                            filters.append(df[column] >= value2)
                    except ValueError:
                        st.warning("Введите корректное числовое значение для второго условия")

            else:
                selected = st.multiselect("Выберите значения", sorted(df[column].dropna().unique().astype(str)))
                filters.append(df[column].astype(str).isin(selected))

            if filters:
                if logic_op == "И":
                    return df[pd.concat(filters, axis=1).all(axis=1)]
                else:
                    return df[pd.concat(filters, axis=1).any(axis=1)]
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
        preview_file = load_csv(uploaded_files[0])
        if not preview_file.empty:
            merge_column = st.selectbox("Выберите столбец для объединения", preview_file.columns)
            merged_df = merge_files(uploaded_files, merge_column)
            if not merged_df.empty:
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
        if not df.empty:
            plot_data(df)
