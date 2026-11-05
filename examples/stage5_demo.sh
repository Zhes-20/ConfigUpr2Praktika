#!/usr/bin/env bash
# Этап 5: текст Graphviz и картинки PNG для трёх пакетов и тестового графа.
cd "$(dirname "$0")/.."
mkdir -p output
run() { echo; echo "\$ ./run.sh $*"; ./run.sh "$@"; echo "exit code: $?"; }

run -p org.springframework:spring-context:6.0.13 -o output/spring-context.png
run -p com.squareup.okhttp3:okhttp:4.12.0 -o output/okhttp.png
run -p ch.qos.logback:logback-classic:1.4.11 -o output/logback-classic.png
run -p A -m test -s examples/repos/cycle.txt -o output/cycle.png
run -p A -m test -s examples/repos/chain.txt -d 3 -o output/chain.png
