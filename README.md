# Estimate Volume Extractor

Локальный инструмент для себя: исходный документ сначала конвертируется в Markdown через MinerU, затем из Markdown извлекается ведомость объёмов работ без ценовых показателей.

## Что умеет

- Загружает PDF, Excel, CSV, DOC/DOCX, изображения или готовый Markdown.
- Поддерживает два режима MinerU:
  - `accurate` — через API key, для основного использования.
  - `agent` — лёгкий режим MinerU без ключа, через signed-upload: сначала передаётся `file_name`, затем файл загружается по `file_url`.
- Не парсит PDF/Excel напрямую: весь pipeline идёт через промежуточный Markdown.
- Показывает и даёт скачать Markdown.
- Извлекает колонки: № п/п, код расценки, наименование работ, единица измерения, количество, примечание.
- Вычисляет строки вида `Объем=3 / 100` и подставляет объём в предыдущую позицию.
- Экспортирует CSV/XLSX.

## Установка

```bash
python -m pip install -r requirements.txt
```

Для тестов:

```bash
python -m pip install -r requirements-dev.txt
```

## Локальный интерфейс

```bash
streamlit run app.py
```

В интерфейсе можно:

1. загрузить исходный файл;
2. выбрать режим MinerU `accurate` или `agent`;
3. вставить API key для `accurate` режима;
4. обработать документ;
5. посмотреть таблицу результата;
6. раскрыть или скачать промежуточный Markdown;
7. скачать CSV/XLSX.

## CLI

Обработка исходного документа через MinerU accurate:

```bash
export MINERU_API_KEY="your-token"
python main.py -i estimate.pdf -o result.xlsx --format xlsx --markdown-output estimate.md --mineru-mode accurate
```

Обработка через agent-режим без API key:

```bash
python main.py -i estimate.pdf -o result.csv --mineru-mode agent --markdown-output estimate.md
```

Если Markdown уже есть:

```bash
python main.py -i estimate.md --from-md -o result.csv
```

## Pake

Pake можно использовать как desktop-оболочку вокруг локального Streamlit UI. Подробности: [`docs/pake.md`](docs/pake.md).

## Тесты

```bash
pytest
```
