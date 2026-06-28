# Упаковка локального интерфейса через Pake

Pake не заменяет интерфейс приложения: он упаковывает веб-страницу в desktop-окно. Поэтому базовый UI проекта запускается локально через Streamlit, а Pake можно использовать как оболочку.

## Локальный запуск UI

```bash
streamlit run app.py --server.port 8501
```

## Пример упаковки

```bash
pnpm install -g pake-cli
pake http://localhost:8501 --name EstimateExtractor --width 1280 --height 900
```

Перед запуском desktop-оболочки локальный Streamlit-сервер должен быть запущен.
