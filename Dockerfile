# Utilise une image Maven pour construire l'application
FROM maven:3.8.6-eclipse-temurin-17 AS build
WORKDIR /app

# Copie les fichiers du projet
COPY pom.xml .
COPY src ./src

# Construit l'application
RUN mvn clean package

# Utilise une image légère pour exécuter l'application
FROM eclipse-temurin:17-jdk-jammy
WORKDIR /app

# Copie le JAR construit depuis l'étape précédente
COPY --from=build /app/target/UpdateApecProfile-1.0-SNAPSHOT.jar ./app.jar

# Exécute l'application
CMD ["java", "-jar", "app.jar"]
