package com.scraping.pages;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

import com.scraping.utils.SleepUtils;
import com.scraping.utils.WebDriverUtils;

public class LoginPage {
    private WebDriver driver; // WebDriver instance to interact with the browser

    // Define WebElements using XPath to locate them on the webpage
    @FindBy(xpath = "/html/body/div[1]/div/div[1]/div/form/div[3]/input")
    private WebElement usernameField; // WebElement for the username input field

    @FindBy(xpath = "/html/body/div[1]/div/div[1]/div/form/div[4]/input")
    private WebElement passwordField; // WebElement for the password input field

    @FindBy(xpath = "/html/body/div[1]/div/div[1]/div/form/div[5]/button")
    private WebElement loginButton; // WebElement for the login button

    // Constructor to initialize the WebDriver and WebElements
    public LoginPage() {
        this.driver = WebDriverUtils.getWebDriver(); // Initialize WebDriver
        PageFactory.initElements(driver, this); // Initialize WebElements
    }

    // Method to open the login page
    public void open() {
        driver.get("https://www.apec.fr/candidat/mon-espace/profil.html/carte-visite"); // Navigate to the login page URL
        try {
            Thread.sleep(2000); // Pause for 2 seconds to allow the page to load
        } catch (InterruptedException e) {
            e.printStackTrace(); // Print stack trace if the sleep is interrupted
        }
    }

    // Method to perform login with provided username and password
    public void login(String username, String password) {
        usernameField.sendKeys(username); // Enter the username
        SleepUtils.sleep(2000); // Pause for 2 seconds

        passwordField.sendKeys(password); // Enter the password
        SleepUtils.sleep(2000); // Pause for 2 seconds

        loginButton.click(); // Click the login button
        SleepUtils.sleep(2000); // Pause for 2 seconds
    }
}
