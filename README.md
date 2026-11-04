# Визуализатор графа зависимостей Maven (вариант 8)

Практическая работа №2 по дисциплине «Конфигурационное управление».
Готовы этапы 1–2 из 5: конфигурация и сбор данных.

## Общее описание

Консольное приложение для анализа зависимостей пакетов Java (Maven).
Менеджеры пакетов и сторонние библиотеки для получения зависимостей
не используются: описание пакета (`pom.xml`) скачивается по URL
репозитория и разбирается стандартными модулями Python.

На этапе 2 приложение выводит прямые зависимости заданного пакета.
Вывод параметров в формате `ключ=значение` был только на этапе 1.

## Функции и настройки

| Опция | Параметр | По умолчанию |
|---|---|---|
| `-p`, `--package` | анализируемый пакет `groupId:artifactId:version`; в режиме `test` — большие латинские буквы | обязательна |
| `-s`, `--source` | URL репозитория или путь к файлу тестового репозитория | `https://repo1.maven.org/maven2` |
| `-m`, `--mode` | режим работы: `remote` — настоящий репозиторий, `test` — тестовый | `remote` |
| `-o`, `--image` | имя PNG-файла с изображением графа | `graph.png` |
| `-d`, `--depth` | максимальная глубина анализа, целое от 1 | `5` |
| `-e`, `--exclude` | не учитывать пакеты, имя которых содержит подстроку | пусто |

Ошибки, которые проверяются:

- пакет не в формате `groupId:artifactId:version` (в режиме `test` — не из букв `A-Z`);
- неизвестный режим;
- источник не `http(s)`-адрес, а в режиме `test` — файл не существует;
- изображение не `.png` или папка для него не существует;
- глубина не целое число или меньше 1;
- подстрока фильтра содержит пробелы.

При ошибке приложение пишет `config error: ...` и завершается с кодом 1.
Если опция `-p` не задана совсем, справку и ошибку печатает `argparse`,
код завершения 2.

Тестовый режим (`-m test`) появится на этапе 3; сейчас он сообщает об ошибке.

### Как находятся прямые зависимости

1. По координатам строится адрес файла:
   `{репозиторий}/{groupId с / вместо .}/{artifactId}/{version}/{artifactId}-{version}.pom`.
2. Из `pom.xml` берётся раздел `<dependencies>` верхнего уровня.
   Плагины сборки (`<build>`) и профили не учитываются.
3. Версии вида `${hamcrestVersion}` подставляются из `<properties>`.
4. Если версия не указана, она берётся из `<dependencyManagement>`
   самого пакета, его родительских `pom.xml` (`<parent>`) и файлов BOM,
   подключённых через `<scope>import</scope>`.
5. Для каждой зависимости выводится область (`compile`, `test`, `runtime`,
   `provided`) и признак `optional`.

Ошибки: пакета нет в репозитории, нет связи, повреждённый `pom.xml`.

### Файлы

| Файл | Назначение |
|---|---|
| `src/app.py` | точка входа, вывод |
| `src/config.py` | опции командной строки и их проверка |
| `src/maven.py` | скачивание и разбор `pom.xml` |
| `examples/stage1_demo.sh` | все опции и ошибки в них |
| `examples/stage2_demo.sh` | прямые зависимости настоящих пакетов |

## Сборка и тесты

Сборка не нужна, требуется Python 3.9+. Сторонние пакеты не нужны.

```bash
make test                 # модульные тесты
make demo                 # примеры этапов 1 и 2
./run.sh -p junit:junit:4.13.2
```

Без `make`:

```bash
python3 -m unittest discover -s tests -v
python3 -m src.app -p junit:junit:4.13.2
```

## Примеры использования

```
$ ./run.sh -p junit:junit:4.13.2
Direct dependencies of junit:junit:4.13.2:
  org.hamcrest:hamcrest-core:1.3 (compile)
  org.hamcrest:hamcrest-library:1.3 (test)

$ ./run.sh -p com.google.guava:guava:32.1.3-jre
Direct dependencies of com.google.guava:guava:32.1.3-jre:
  com.google.guava:failureaccess:1.0.1 (compile)
  com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava (compile)
  com.google.code.findbugs:jsr305:3.0.2 (compile)
  org.checkerframework:checker-qual:3.37.0 (compile)
  com.google.errorprone:error_prone_annotations:2.21.1 (compile)
  com.google.j2objc:j2objc-annotations:2.8 (compile)

$ ./run.sh -p org.example:no-such-package:1.0
repository error: not found in repository: https://repo1.maven.org/maven2/org/example/no-such-package/1.0/no-such-package-1.0.pom

$ ./run.sh -p junit:junit:4.13.2 -d 0
config error: depth: must be at least 1, got 0
```
