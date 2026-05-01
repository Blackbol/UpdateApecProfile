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
            // Uses the Selenium container URL defined by the environment variable
            String seleniumHubUrl = System.getenv("SELENIUM_HUB_URL");
            if (seleniumHubUrl == null) {
                seleniumHubUrl = "http://localhost:4444/wd/hub"; // URL par défaut
            }

            URL url = new URL(seleniumHubUrl);

            // Configure capabilities for Chrome
            DesiredCapabilities capabilities = new DesiredCapabilities();
            capabilities.setBrowserName("chrome");

            // Initialize the WebDriver with the configured capabilities
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
