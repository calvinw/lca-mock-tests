# Build the standalone server against the current openLCA core. GreenDelta's
# published server library layer currently contains openLCA core 2.0/Derby
# 10.16, which cannot open openLCA 2.6 databases such as BAFU-2026 v1.
FROM ghcr.io/greendelta/gdt-server-native@sha256:4a5b20ea330bbbf1889839822214db38a93b8305e5c445a777067a34f531617e AS native

FROM maven:3.9.11-eclipse-temurin-25 AS build
WORKDIR /src
COPY docker/gdt-server-2.7.patch /src/gdt-server-2.7.patch
RUN git clone https://github.com/GreenDelta/olca-modules.git \
    && cd olca-modules \
    && git checkout fdccef01bfadc6ea443f6743959c7af87edb6601 \
    && mvn install -pl olca-core -am -DskipTests=true

RUN git clone https://github.com/GreenDelta/gdt-server.git \
    && cd gdt-server \
    && git checkout 2e3a1787c13ca119761942b8855ac31407cbb4cd \
    && git apply /src/gdt-server-2.7.patch \
    && sed -i 's/<version>2.5.0<\/version>/<version>2.7.0-SNAPSHOT<\/version>/g' pom.xml \
    && mvn package -DskipTests=true

FROM eclipse-temurin:25-jre
ENV JAVA_MAX_RAM_PERCENTAGE=80
WORKDIR /app
COPY --from=build /src/gdt-server/target/gdt-server.jar /app/gdt-server.jar
COPY --from=build /src/gdt-server/target/lib /app/lib
COPY --from=native /app/native /app/native
COPY --from=native /app/THIRDPARTY_README /app/NATIVE_THIRDPARTY_README
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=80", "-jar", "/app/gdt-server.jar", "-data", "/app/data", "-native", "/app/native"]
