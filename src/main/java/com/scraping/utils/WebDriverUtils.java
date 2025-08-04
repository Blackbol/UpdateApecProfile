package com.scraping.utils;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;

public class WebDriverUtils {
    private static WebDriver driver; // Static WebDriver instance to be used across the application

    // Method to initialize the WebDriver with specific Chrome options
    public static void initWebDriver() {
        // Set the path to the ChromeDriver executable
        System.setProperty("webdriver.chrome.driver", "driver/chromedriver.exe");

        // Initialize Chrome options
        ChromeOptions options = new ChromeOptions();

        // Set the path to the Chrome binary
        options.setBinary("browser/chrome-win/chrome.exe");

        // Argument to solve "Unable to establish websocket connection" issue
        options.addArguments("--remote-allow-origins=*");

        // Arguments to run Chrome in headless mode and avoid displaying the browser GUI
        options.addArguments("--headless=new");
        options.addArguments("--disable-gpu");
        options.addArguments("--window-size=1920,1200");

        // Initialize the WebDriver with the specified options
        driver = new ChromeDriver(options);
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
