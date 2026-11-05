#!/usr/bin/env bash
# Этап 4: сравнение с настоящим Maven. Нужен установленный mvn.
# Пример: bash examples/compare_with_maven.sh org.springframework:spring-context:6.0.13
cd "$(dirname "$0")/.."
PACKAGE="${1:-org.springframework:spring-context:6.0.13}"
IFS=: read -r GROUP ARTIFACT VERSION <<< "$PACKAGE"
WORK="$(mktemp -d)"
cat > "$WORK/pom.xml" <<POM
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>compare</groupId>
  <artifactId>compare</artifactId>
  <version>1</version>
  <dependencies>
    <dependency>
      <groupId>$GROUP</groupId>
      <artifactId>$ARTIFACT</artifactId>
      <version>$VERSION</version>
    </dependency>
  </dependencies>
</project>
POM

echo "=== this tool ==="
./run.sh -p "$PACKAGE" -l -d 20

echo "=== mvn dependency:tree ==="
mvn -q -f "$WORK/pom.xml" dependency:tree -DoutputFile=/dev/stdout

echo "=== mvn dependency:build-classpath (Maven loading order) ==="
mvn -q -f "$WORK/pom.xml" dependency:build-classpath \
    -Dmdep.outputFile=/dev/stdout | tr ':' '\n'
rm -rf "$WORK"
