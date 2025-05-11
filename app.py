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
            filters = []
            logic_op = "И"  # Начальный логический оператор
            add_condition = True

            while add_condition:
                column = st.selectbox("Выберите столбец", df.columns)
                col_type = detect_column_type(df[column])

                if col_type == "datetime":
                    df[column] = pd.to_datetime(df[column], errors='coerce')
                    min_date, max_date = pd.to_datetime(df[column].min()), pd.to_datetime(df[column].max())
                    start, end = st.date_input("Выберите диапазон дат", [min_date, max_date])
                    filters.append((df[column] >= pd.to_datetime(start)) & (df[column] <= pd.to_datetime(end)))
                elif col_type == "numeric":
                    condition = st.selectbox("Выберите условие", ["=", "<", ">", "<=", ">="])
                    value = st.text_input(f"Введите значение для {column}")
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
                    selected = st.multiselect(f"Выберите значения для {column}", sorted(df[column].dropna().unique().astype(str)))
                    filters.append(df[column].astype(str).isin(selected))

                # Запрашиваем логический оператор для следующего условия
                logic_op = st.selectbox("Логический оператор", ["И", "ИЛИ"], index=0, key=f"logic_{len(filters)}")

                add_condition = st.button("Добавить условие", key=f"add_condition_{len(filters)}")
                if not add_condition:
                    break

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
