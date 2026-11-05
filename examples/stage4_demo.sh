#!/usr/bin/env bash
# Этап 4: порядок загрузки зависимостей.
cd "$(dirname "$0")/.."
run() { echo; echo "\$ ./run.sh $*"; ./run.sh "$@"; echo "exit code: $?"; }
R=examples/repos

run -p A -m test -s $R/simple.txt -l
run -p A -m test -s $R/diamond.txt -l
run -p A -m test -s $R/chain.txt -l
run -p A -m test -s $R/chain.txt -l -d 3
run -p A -m test -s $R/exclude.txt -l -e TEST
run -p A -m test -s $R/cycle.txt -l
run -p A -m test -s $R/self.txt -l

run -p junit:junit:4.13.2 -l
run -p org.springframework:spring-context:6.0.13 -l
run -p com.google.guava:guava:32.1.3-jre -l
