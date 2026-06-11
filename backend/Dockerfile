FROM eclipse-temurin:21-jdk-jammy AS build

WORKDIR /app

COPY gradlew ./
COPY gradle ./gradle
COPY build.gradle settings.gradle ./

RUN chmod +x gradlew

COPY src ./src

RUN ./gradlew bootJar --no-daemon

FROM eclipse-temurin:21-jre-jammy

WORKDIR /app

COPY --from=build /app/build/libs/*.jar /app/app.jar
COPY data ./data

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
