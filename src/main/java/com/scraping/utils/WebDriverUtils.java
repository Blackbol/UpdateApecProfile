package com.scraping.utils;

import java.net.URL;
import java.net.MalformedURLException;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.remote.DesiredCapabilities;
import org.openqa.selenium.remote.RemoteWebDriver;

public class WebDriverUtils {
    private static WebDriver driver; // Static WebDriver instance to be used across the application

    // Method to initialize the WebDriver with specific Chrome options
    public static void initWebDriver() {
        try {
            // Utilise l'URL du conteneur Selenium définie par la variable d'environnement
            String seleniumHubUrl = System.getenv("SELENIUM_HUB_URL");
            if (seleniumHubUrl == null) {
                seleniumHubUrl = "http://localhost:4444/wd/hub"; // URL par défaut
            }

            URL url = new URL(seleniumHubUrl);

            // Configurer les capacités pour Chrome
            DesiredCapabilities capabilities = new DesiredCapabilities();
            capabilities.setBrowserName("chrome");

            // Initialiser le WebDriver avec les capacités configurées
            driver = new RemoteWebDriver(url, capabilities);

        } catch (MalformedURLException e) {
            e.printStackTrace();
        }
    }

    // Method to get the WebDriver instance
    public static WebDriver getWebDriver() {
        return driver;
    }

    // Method to quit the WebDriver and clean up resources
    public static void quitWebDriver() {
        if (driver != null) {
            driver.quit(); // Quit the WebDriver if it is not null
        }
    }
}
