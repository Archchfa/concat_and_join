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

def filter_dataframe():
    uploaded_file = st.file_uploader("Загрузите CSV файл для фильтрации", type="csv", key="filter_file")
    if uploaded_file:
        df = load_csv(uploaded_file)
        search_type = st.radio("Выберите способ поиска:", ["Ввести вручную", "Загрузить файл со значениями", "По условию"])
        if search_type == "Ввести вручную":
            column = st.selectbox("Выберите столбец", df.columns)
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
                value_col = st.selectbox("Столбец со значениями", value_df.columns)
                target_col = st.selectbox("Столбец для поиска", df.columns)
                return df[df[target_col].astype(str).isin(value_df[value_col].astype(str))]
        elif search_type == "По условию":
            column = st.selectbox("Выберите столбец", df.columns)
            col_type = detect_column_type(df[column])
            df[column] = df[column].copy()
            if col_type == "datetime":
                df[column] = pd.to_datetime(df[column], errors='coerce')
                min_date, max_date = pd.to_datetime(df[column].min()), pd.to_datetime(df[column].max())
                start, end = st.date_input("Диапазон дат", [min_date, max_date])
                return df[(df[column] >= pd.to_datetime(start)) & (df[column] <= pd.to_datetime(end))]
            elif col_type == "numeric":
                condition = st.selectbox("Условие", ["=", "<", ">", "<=", ">="])
                value = st.text_input("Значение")
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
                    except:
                        st.warning("Некорректное значение")
            else:
                selected = st.multiselect("Выберите значения", sorted(df[column].dropna().unique().astype(str)))
                return df[df[column].astype(str).isin(selected)]
    return None

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

    # Преобразование дат к формату YYYY-MM-DD
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
        fig = px.bar(grouped, x=group_by[0], y=value_col, color=color, barmode='group')
    elif chart_type == "Линейный график":
        fig = px.line(grouped, x=group_by[0], y=value_col, color=color)
    elif chart_type == "Круговая диаграмма":
        fig = px.pie(grouped, names=group_by[0], values=value_col)

    if fig:
        st.plotly_chart(fig, use_container_width=True)

# Интерфейс
st.sidebar.title("Навигация")
option = st.sidebar.radio("Выберите раздел", [
    "Объединить файлы",
    "Фильтрация данных",
    "Построить график"
], key="menu_option")

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
    uploaded_file = st.file_uploader("Загрузите CSV файл", type="csv", key="plot_file")
    if uploaded_file:
        df = load_csv(uploaded_file)
        plot_data(df)
