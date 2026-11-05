#!/usr/bin/env bash
# Сравнение с настоящим Maven. Нужны mvn и dot (brew install maven graphviz).
# Пример: bash examples/compare_with_maven.sh org.springframework:spring-context:6.0.13
cd "$(dirname "$0")/.."
PACKAGE="${1:-org.springframework:spring-context:6.0.13}"
IFS=: read -r GROUP ARTIFACT VERSION <<< "$PACKAGE"
WORK="$(mktemp -d)"
mkdir -p output
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
./run.sh -p "$PACKAGE" -d 20 -o "output/$ARTIFACT.png"

echo "=== mvn dependency:tree ==="
mvn -q -f "$WORK/pom.xml" dependency:tree -DoutputFile=/dev/stdout

echo "=== mvn dependency:tree -DoutputType=dot (standard Maven picture) ==="
mvn -q -f "$WORK/pom.xml" dependency:tree -DoutputType=dot \
    -DoutputFile="$PWD/output/$ARTIFACT-maven.dot"
cat "output/$ARTIFACT-maven.dot"
dot -Tpng -o "output/$ARTIFACT-maven.png" "output/$ARTIFACT-maven.dot" \
    && echo "saved: output/$ARTIFACT-maven.png"
rm -rf "$WORK"
