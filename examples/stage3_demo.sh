#!/usr/bin/env bash
# Этап 3: граф зависимостей на тестовых репозиториях и на Maven Central.
cd "$(dirname "$0")/.."
run() { echo; echo "\$ ./run.sh $*"; ./run.sh "$@"; echo "exit code: $?"; }
R=examples/repos

run -p A -m test -s $R/simple.txt
run -p A -m test -s $R/diamond.txt
run -p A -m test -s $R/chain.txt
run -p A -m test -s $R/chain.txt -d 2
run -p A -m test -s $R/exclude.txt
run -p A -m test -s $R/exclude.txt -e TEST
run -p A -m test -s $R/cycle.txt
run -p A -m test -s $R/self.txt
run -p A -m test -s $R/undefined.txt
run -p Z -m test -s $R/simple.txt
run -p A -m test -s $R/broken.txt
run -p TESTKIT -m test -s $R/exclude.txt -e TEST

run -p junit:junit:4.13.2
run -p org.springframework:spring-context:6.0.13 -d 2
run -p org.springframework:spring-context:6.0.13 -d 2 -e aop
