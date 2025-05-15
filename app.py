import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Анализ CSV файлов", layout="wide")
st.title("📊 Инструмент для анализа CSV файлов")

def load_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8', header=None)
        new_header = df.iloc[0].astype(str).str.strip()
        new_header = [col if col and col != 'nan' else f"unknown_{i}" for i, col in enumerate(new_header)]
        seen = {}
        unique_header = []
        for col in new_header:
            if col not in seen:
                seen[col] = 0
                unique_header.append(col)
            else:
                seen[col] += 1
                unique_header.append(f"{col}_{seen[col]}")
        df = df[1:].reset_index(drop=True)
        df.columns = unique_header
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

    # inner join — только общие строки
    result = pd.merge(df1, df2, on="_merge_key", how="inner", suffixes=('', '_dup'))
    result = result.loc[:, ~result.columns.str.endswith('_dup')]
    result = result.loc[:, ~result.columns.str.fullmatch(r'Unnamed.*')]
    result = result.rename(columns={"_merge_key": f"{merge_col_1} / {merge_col_2}"})

    return result

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

st.sidebar.title("Навигация")
option = st.sidebar.radio("Выберите раздел", ["Объединить файлы", "Фильтрация данных", "Построить график"], key="menu_option")

if option == "Объединить файлы":
    uploaded_files = st.file_uploader("Загрузите 2 CSV файла", type="csv", accept_multiple_files=True)
    if uploaded_files:
        merged_df = merge_files(uploaded_files)
        if not merged_df.empty:
            st.dataframe(merged_df)
            download_link(merged_df, "объединенные_файлы.csv")

elif option == "Фильтрация данных":
    filtered_df = filter_dataframe()
    if filtered_df is not None:
        st.dataframe(filtered_df)
        download_link(filtered_df, "отфильтрованные_данные.csv")

elif option == "Построить график":
    uploaded_file = st.file_uploader("Загрузите CSV файл", type="csv", key="plot_file")
    if uploaded_file:
        df = load_csv(uploaded_file)
        plot_data(df)
