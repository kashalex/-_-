"""Local Streamlit interface for the estimate volume extractor."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

from estimate_extractor.export import export_items, items_to_dataframe
from estimate_extractor.mineru_client import MinerUClient, MinerUError
from estimate_extractor.config import ParserConfig
from estimate_extractor.parser import parse_estimate_markdown

st.set_page_config(page_title="Ведомость объёмов работ", layout="wide")

st.title("Ведомость объёмов работ из сметы")
st.caption("Документ всегда сначала переводится в Markdown, после этого парсится ведомость.")

with st.sidebar:
    st.header("Настройки MinerU")
    mode = st.radio("Режим конвертации", ["accurate", "agent"], help="accurate использует API key, agent легче, но с ограничениями MinerU")
    api_key = st.text_input("MinerU API key", value=os.getenv("MINERU_API_KEY", ""), type="password")
    model_version = st.selectbox("Модель", ["vlm", "pipeline", "MinerU-HTML"], index=0)
    language = st.text_input("Язык документа", value="ru")
    code_regex = st.text_input("Regex кода норматива", value="")

uploaded = st.file_uploader("Загрузите PDF / Excel / CSV / Markdown", type=["pdf", "xls", "xlsx", "csv", "md", "txt", "doc", "docx", "png", "jpg", "jpeg"])
use_ready_md = st.checkbox("Файл уже Markdown — не вызывать MinerU", value=False)

if uploaded and st.button("Обработать", type="primary"):
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / uploaded.name
        source_path.write_bytes(uploaded.getbuffer())
        try:
            with st.status("Подготовка документа", expanded=True) as status:
                if use_ready_md:
                    st.write("Читаю готовый Markdown...")
                    markdown = source_path.read_text(encoding="utf-8")
                else:
                    st.write(f"Отправляю файл в MinerU, режим: {mode}...")
                    client = MinerUClient(api_key=api_key or None)
                    markdown = client.convert_file(str(source_path), mode=mode, model_version=model_version, language=language)
                st.write("Парсю Markdown и формирую ведомость...")
                items = parse_estimate_markdown(markdown, ParserConfig(code_regex=code_regex) if code_regex else None)
                df = items_to_dataframe(items)
                status.update(label="Готово", state="complete")

            st.subheader("Результат")
            st.dataframe(df, use_container_width=True)

            st.subheader("Промежуточный Markdown")
            st.download_button("Скачать Markdown", markdown.encode("utf-8"), file_name=f"{Path(uploaded.name).stem}.md", mime="text/markdown")
            with st.expander("Показать Markdown"):
                st.code(markdown, language="markdown")

            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Скачать CSV", csv_data, file_name="volume_statement.csv", mime="text/csv")

            xlsx_path = Path(tmpdir) / "volume_statement.xlsx"
            export_items(items, str(xlsx_path), "xlsx")
            st.download_button(
                "Скачать XLSX",
                xlsx_path.read_bytes(),
                file_name="volume_statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except (MinerUError, ValueError, FileNotFoundError, UnicodeDecodeError) as exc:
            st.error(f"Ошибка: {exc}")
