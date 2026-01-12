package com.scraping.pages;

import org.openqa.selenium.NoSuchElementException;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;

import com.scraping.utils.SleepUtils;
import com.scraping.utils.WebDriverUtils;

public class ProfilPage {
    private WebDriver driver; // WebDriver instance to interact with the browser

    // Define WebElements using XPath to locate them on the webpage
    @FindBy(xpath = "/html/body/div[4]/div[2]/div/div[1]/div/div[2]/div/button[2]")
    private WebElement refuseCookie; // WebElement for the cookie refusal button

    @FindBy(xpath = "/html/body/main/apec-profil-cadre/apec-carte-visite/div/div[2]/div/div[1]/form/div[5]/input")
    private WebElement posteRechercher; // WebElement for the job position input field

    @FindBy(xpath = "/html/body/main/apec-profil-cadre/apec-carte-visite/div/div[2]/div/div[1]/form/div[9]/button")
    private WebElement saveButton; // WebElement for the save button

    // Constructor to initialize the WebDriver and WebElements
    public ProfilPage() {
        this.driver = WebDriverUtils.getWebDriver(); // Initialize WebDriver
        PageFactory.initElements(driver, this); // Initialize WebElements
    }

    // Method to change the job position
    public void changePoste(String nouveauPoste) {
        try {
            // Check if the cookie banner is displayed and click to refuse if it is
            if (refuseCookie.isDisplayed()) {
                refuseCookie.click();
                System.out.println("The cookie banner close on profil page."); // Print message if cookie banner is display
            }
        } catch (NoSuchElementException e) {
            System.out.println("The cookie banner was not displayed on profil page."); // Print message if cookie banner is not displayed
        }
        SleepUtils.sleep(2000); // Pause for 2 seconds

        posteRechercher.clear(); // Clear the current job position field
        SleepUtils.sleep(2000); // Pause for 2 seconds

        posteRechercher.sendKeys(nouveauPoste); // Enter the new job position
        SleepUtils.sleep(2000); // Pause for 2 seconds

        saveButton.click(); // Click the save button to save the new job position
        SleepUtils.sleep(2000); // Pause for 2 seconds
    }
}
