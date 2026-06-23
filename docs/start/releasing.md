# Как собирать и выпускать релизы

Версия живёт в одном месте — `app/__init__.py` (`__version__`), тот же номер в `pyproject.toml`.
От неё зависит имя папки бинарника и версия, которую сервер сообщает о себе. Менять номер — только
здесь (см. [версионирование](../architecture/versioning/README.md)).

## Вариант 1. Автоматический релиз через GitHub (рекомендуется)

Готовые бинарники под Linux / Windows / macOS собирает GitHub Actions
([`.github/workflows/release.yml`](../../.github/workflows/release.yml)) — по пушу тега `vX.Y.Z`.

Порядок:

1. Поднимите версию в `app/__init__.py` (`__version__`) и тем же числом в `pyproject.toml`.
2. Прогоните тесты (`python -m app.tests.test_security_modes` и др. — см. [../../build/BUILD.md](../../build/BUILD.md)).
3. Закоммитьте и запушьте изменения.
4. Поставьте и запушьте тег, совпадающий с версией:
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```
5. Actions запустит матрицу `ubuntu / windows / macos`, соберёт по бинарнику на каждой ОС, создаст
   Release `v1.1.0` и приложит к нему три бинарника и файлы `.sha256`.

**Тег обязан совпадать с `__version__`** — иначе имя Release разойдётся с папкой сборки.

Ручной прогон без тега: вкладка **Actions → release → Run workflow** (`workflow_dispatch`) — соберёт
артефакты и положит их в workflow artifacts, без создания Release.

### Что нужно настроить один раз

- Включить GitHub Actions в репозитории (по умолчанию включены).
- Больше ничего: workflow использует встроенный `GITHUB_TOKEN` с правом `contents: write` (уже
  объявлено в файле) для создания Release. Сторонних секретов и action-ов нет.

## Вариант 2. Локальная сборка под одну ОС

PyInstaller **не кросс-компилирует** — собирается только под ту ОС, на которой запущено. Для всех
трёх ОС нужен либо Вариант 1, либо сборка на каждой ОС вручную.

```bash
cd build
python build.py            # → dist/<version>/<os>-<arch>/modusbi-mcp-server[.exe] + .sha256
python build.py --clean    # пересобрать с нуля
python build.py --check    # только проверить зависимости
```

Результат и проверка — [../../build/BUILD.md](../../build/BUILD.md), установка готового бинарника —
[../../build/INSTALL.md](../../build/INSTALL.md).

## Чек-лист релиза

- [ ] `__version__` (`app/__init__.py`) = `version` (`pyproject.toml`), чистый `MAJOR.MINOR.PATCH`.
- [ ] Тесты проходят.
- [ ] Тег `vX.Y.Z` совпадает с `__version__`.
- [ ] После сборки проверена контрольная сумма (`sha256sum -c <binary>.sha256`).
