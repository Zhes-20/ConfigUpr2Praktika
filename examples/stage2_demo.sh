#!/usr/bin/env bash
# Этап 2: прямые зависимости пакетов из Maven Central.
cd "$(dirname "$0")/.."
run() { echo; echo "\$ ./run.sh $*"; ./run.sh "$@"; echo "exit code: $?"; }

run -p junit:junit:4.13.2
run -p com.google.guava:guava:32.1.3-jre
run -p org.apache.commons:commons-lang3:3.13.0
run -p org.slf4j:slf4j-api:2.0.9

run -p org.example:no-such-package:1.0
run -p junit:junit:4.13.2 -s https://repo1.maven.org/no-such-repository
