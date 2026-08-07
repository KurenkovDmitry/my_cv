# CV Importer

Импортер предназначен для двусторонней конвертации между resume-like документами и внутренним форматом `portfolio.v1`.

Текущая реализация больше не строится вокруг монолитного JS-файла. Ядро разделено на слои:

- Python-пакет отвечает за маршрутизацию форматов, нормализацию, парсинг разделов, сборку `portfolio.v1` и экспорт;
- C++-модуль отвечает за нативное извлечение текста из PDF без OCR и базовый структурный разбор layout;
- backend использует Python CLI как внешний конвертер и, при необходимости, передаёт ему путь к нативному PDF-экстрактору.

OCR не используется и не нужен. Изображения как источник резюме не поддерживаются намеренно.

## Поддерживаемые потоки

### Импорт в `portfolio.v1`

- raw `portfolio.v1` JSON;
- bundle JSON со `snapshot.payload`;
- PDF с текстовым слоем;
- Markdown;
- TXT;
- HTML.

### Экспорт из `portfolio.v1`

- raw `portfolio.v1` JSON;
- bundle JSON;
- Markdown-документ в стиле резюме.

## Архитектура по папкам

### Python orchestration

- `src/portfolio_cv_importer/application/`
  Команды и основной сервис конвертации/экспорта.
- `src/portfolio_cv_importer/domain/`
  Модели, константы и фабрика безопасного базового `portfolio.v1`.
- `src/portfolio_cv_importer/extractors/`
  Извлечение текста из PDF: pure Python и optional native bridge.
- `src/portfolio_cv_importer/parsers/`
  Разбиение резюме на секции и маппинг в поля портфолио.
- `src/portfolio_cv_importer/normalizers/`
  Нормализация строк и текстовых артефактов.
- `src/portfolio_cv_importer/exporters/`
  Обратное преобразование `portfolio.v1` в экспортные документы.
- `src/portfolio_cv_importer/api/cli/`
  CLI-входы для backend и ручного запуска.

### Native PDF extraction

- `native/include/portfolio_cv_importer/`
  Заголовки нативной библиотеки.
- `native/src/pdf_object_reader.cpp`
  Чтение PDF-объектов.
- `native/src/pdf_stream_decoder.cpp`
  Декодирование stream-блоков PDF.
- `native/src/pdf_text_extractor.cpp`
  Извлечение текстовых токенов, восстановление строк и разделение удалённых колонок.
- `native/src/resume_layout_parser.cpp`
  Самописный классификатор секций и семейств layout на C++ с полным facade `PDF -> sections`.
- `native/src/main.cpp`
  CLI-утилита `portfolio_cv_pdf_extract`.

## Маршруты данных

### Импорт

1. Backend принимает исходный файл кандидата на импорт.
2. `ResumeImportConverter` определяет тип источника:
   raw `portfolio.v1`, bundle JSON, PDF, Markdown, TXT или HTML.
3. Для JSON backend извлекает payload напрямую.
4. Для resume-like документов backend запускает Python CLI.
5. Python CLI вызывает `CvImportExportService`.
6. Сервис либо читает PDF встроенным Python-экстрактором, либо делегирует в C++ binary через `PORTFOLIO_RESUME_NATIVE_PDF_BINARY`.
7. Нормализованный `portfolio.v1` возвращается в backend и сохраняется как import candidate.

## Независимость от шаблона

Парсер не ищет конкретные фамилии, компании, вузы или проекты. Python и C++ используют словари семантических заголовков и порядок секций. Поддержаны распространённые семейства документов:

- reverse chronological и chronological CV, где основой служит история занятости;
- functional CV, начинающийся с навыков и компетенций;
- combination CV с опытом, навыками и проектами;
- academic CV с исследованиями и публикациями;
- одноколоночные и двухколоночные макеты;
- русские резюме с секциями «Опыт работы», «Образование», «Навыки», «Проекты»;
- британские и американские варианты с `Professional summary`, `Work experience`, `Employment history`, `Education`, `Certifications` и `Selected projects`.

Неоднозначные значения не переводятся и не дополняются догадками. Они попадают в staged candidate с `needsManualReview`, после чего администратор выбирает изменения по отдельным полям и может исправить каждое значение до применения.

### Экспорт

1. Источник `portfolio.v1` передаётся в Python export service.
2. Exporter собирает raw JSON, bundle JSON или Markdown-резюме.
3. Готовый документ записывается в целевой файл.

## Локальный запуск

### Python CLI

```bash
python -m portfolio_cv_importer.api.cli.convert_source_to_portfolio ./resume.pdf ./resume.portfolio.v1.json
python -m portfolio_cv_importer.api.cli.export_portfolio_document ./resume.portfolio.v1.json ./resume.md --target-format markdown_resume
```

### C++ extractor

```bash
cmake -S ./native -B ./native/build
cmake --build ./native/build --config Release
./native/build/portfolio_cv_pdf_extract ./resume.pdf
```

## Переменные окружения backend

- `RESUME_IMPORT_PYTHON_BINARY`
  Python binary для запуска CLI-конвертера.
- `RESUME_IMPORT_PYTHONPATH`
  Путь до `tools/cv-importer/src`.
- `RESUME_IMPORT_CLI_MODULE`
  Python module entrypoint конвертации.
- `RESUME_IMPORT_WORKDIR`
  Рабочая директория subprocess-конвертера.
- `RESUME_IMPORT_NATIVE_PDF_BINARY`
  Путь до собранного C++ PDF extractor.

## Ограничения текущей версии

- OCR отсутствует намеренно;
- PDF без текстового слоя не поддерживаются;
- DOCX и ODT пока не подключены;
- для runtime-проверки Python CLI нужен установленный Python 3.13+.
