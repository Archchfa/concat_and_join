import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Анализ CSV файлов", layout="wide")
st.title("📊 Инструмент для анализа CSV файлов")
st.markdown("<style>div[data-testid='stNotification'] {display: none;}</style>", unsafe_allow_html=True)

def load_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Ошибка при чтении файла {uploaded_file.name}: {e}")
        return pd.DataFrame()

def merge_files(files, merge_on):
    dfs = []
    columns_set = None

    for file in files:
        df = load_csv(file)
        if df.empty or merge_on not in df.columns:
            st.warning(f"Файл {file.name} пропущен (нет столбца '{merge_on}')")
            continue

        if columns_set is None:
            columns_set = set(df.columns)
        else:
            df = df[[col for col in df.columns if col in columns_set or col == merge_on]]

        dfs.append(df)

    if len(dfs) < 2:
        st.error("Недостаточно файлов для объединения")
        return pd.DataFrame()

    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=merge_on, how="outer", suffixes=('', '_dup'))
        merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_dup')]

    merged_df = merged_df.loc[:, ~merged_df.columns.str.fullmatch(r'Unnamed.*')]
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
                        filters.append(eval(f"df[column] {condition1} value1"))
                    except:
                        st.warning("Некорректное значение 1")
                if condition2 != "Нет" and value2:
                    try:
                        value2 = float(value2)
                        filters.append(eval(f"df[column] {condition2} value2"))
                    except:
                        st.warning("Некорректное значение 2")
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
    
    group_by_cols = st.multiselect("Выберите столбцы для группировки", df.columns, max_selections=2)
    agg_func = st.selectbox("Функция агрегации", ["count", "sum", "mean", "nunique"])

    if agg_func != "count":
        value_col = st.selectbox("Столбец значений (Y)", df.columns)
    else:
        value_col = None

    # Обработка дат
    for col in group_by_cols:
        if detect_column_type(df[col]) == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    if group_by_cols:
        try:
            if agg_func == "count":
                data = df.groupby(group_by_cols).size().reset_index(name="Значение")
            else:
                grouped = df.groupby(group_by_cols)[value_col]
                if agg_func == "sum":
                    data = grouped.sum(numeric_only=True).reset_index(name="Значение")
                elif agg_func == "mean":
                    data = grouped.mean(numeric_only=True).reset_index(name="Значение")
                elif agg_func == "nunique":
                    data = grouped.nunique().reset_index(name="Значение")
        except Exception as e:
            st.error(f"Ошибка агрегации: {e}")
            return
    else:
        st.warning("Выберите хотя бы один столбец для группировки")
        return

    color_col = group_by_cols[1] if len(group_by_cols) > 1 else None

    fig = None
    if chart_type == "Гистограмма":
        fig = px.histogram(data, x=group_by_cols[0], y="Значение", color=color_col)
    elif chart_type == "Столбчатая диаграмма":
        fig = px.bar(data, x=group_by_cols[0], y="Значение", color=color_col, barmode="group")
    elif chart_type == "Линейный график":
        fig = px.line(data, x=group_by_cols[0], y="Значение", color=color_col)
    elif chart_type == "Круговая диаграмма":
        fig = px.pie(data, names=group_by_cols[0], values="Значение")

    if fig:
        st.plotly_chart(fig, use_container_width=True)

# Основной интерфейс
st.sidebar.header("Выберите действие")
option = st.sidebar.radio("", [
    "Объединить файлы",
    "Фильтрация данных",
    "Построить график",
    "Построить график из одного файла"
])

if option == "Объединить файлы":
    uploaded_files = st.file_uploader("Загрузите CSV файлы", type="csv", accept_multiple_files=True)
    if uploaded_files:
        sample_df = load_csv(uploaded_files[0])
        merge_column = st.selectbox("Выберите столбец для объединения", sample_df.columns)
        if merge_column:
            merged_df = merge_files(uploaded_files, merge_column)
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
    uploaded_file = st.file_uploader("Загрузите CSV файл", type="csv")
    if uploaded_file:
        df = load_csv(uploaded_file)
        plot_data(df)
