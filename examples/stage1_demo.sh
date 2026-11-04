#!/usr/bin/env bash
# Этап 1: вывод параметров и обработка ошибок для каждой опции.
cd "$(dirname "$0")/.."
run() { echo; echo "\$ ./run.sh $*"; ./run.sh "$@"; echo "exit code: $?"; }

run -p junit:junit:4.13.2
run -p org.slf4j:slf4j-api:2.0.9 -s https://repo1.maven.org/maven2 -o deps.png -d 3 -e test
run -p A -m test -s examples/stage1_demo.sh

run -s https://repo1.maven.org/maven2
run -p junit
run -p abc -m test -s examples/stage1_demo.sh
run -p junit:junit:4.13.2 -m local
run -p junit:junit:4.13.2 -s repo1.maven.org
run -p A -m test -s no_such_repo.txt
run -p junit:junit:4.13.2 -o graph.svg
run -p junit:junit:4.13.2 -o no_such_dir/graph.png
run -p junit:junit:4.13.2 -d two
run -p junit:junit:4.13.2 -d 0
run -p junit:junit:4.13.2 -e "a b"
