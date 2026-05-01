package com.scraping.utils;

import org.tinylog.Logger;
import org.tinylog.configuration.Configuration;

public class LogConfig {

    public static void init() {
        // Read the application environment from the APP_ENV environment variable.
        // Default to "dev" if no environment variable is set.
        String env = System.getenv().getOrDefault("LOGGER", "dev").toLowerCase();

        // Configure the log writer to output messages to the console.
        Configuration.set("writer", "console");

        // Define the log message format: date, level, class name, and message.
        Configuration.set("writer.format", "{date: yyyy-MM-dd HH:mm:ss} | {level} | {class-name} | {message}");

        // Adjust the log level depending on the current environment.
        switch (env) {
            case "prod":
                // In production, keep logs less verbose.
                Configuration.set("level", "info");
                break;

            case "dev":
                // In dev environments, keep debug logs enabled for troubleshooting.
                Configuration.set("level", "debug");
                break;

            default:
                // In development, enable debug logs by default.
                Configuration.set("level", "debug");
                break;
        }

        // Log that the configuration has been initialized successfully.
        Logger.debug("Logging configuration loaded for environment {}", env);
    }
}