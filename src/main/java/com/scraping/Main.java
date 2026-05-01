package com.scraping;

import java.time.LocalDate;
import org.tinylog.Logger;

import com.scraping.pages.LoginPage;
import com.scraping.pages.ProfilPage;
import com.scraping.utils.LogConfig;
import com.scraping.utils.SleepUtils;
import com.scraping.utils.WebDriverUtils;

public class Main {
    public static void main(String[] args) {
        // Initialize logging as early as possible before any other application logic.
        LogConfig.init();

        // Initialize the WebDriver to start browser automation
        WebDriverUtils.initWebDriver();

        Logger.info("Program start");

        String posteDuJour; // Variable to store the job title of the day

        // Check if the current day of the month is even or odd
        if (LocalDate.now().getDayOfMonth() % 2 == 0) {
            posteDuJour = "Ingénieur logiciel"; // Set job title for even days
        } else {
            posteDuJour = "Développeur logiciel"; // Set job title for odd days
        }
        Logger.info("Today the 'posteDuJour is {}", posteDuJour);

        try {
            // Navigate to the login page
            LoginPage loginPage = new LoginPage();
            ProfilPage profilPage = new ProfilPage();

            // Open the login page
            loginPage.open();
            SleepUtils.sleep(2000); // Pause for 2 seconds

            // Get credentials from environment variables
            String username = System.getenv("APEC_USERNAME");
            String password = System.getenv("APEC_PASSWORD");
            Logger.debug("Usename get in env = {}", username);
            Logger.debug("Pasword get in env = {}", password);

            if ((username == null || username.isEmpty()) || (password == null || password.isEmpty())) {
                throw new RuntimeException("The APEC_USERNAME and APEC_PASSWORD identifiers must be defined.");
            }

            // Perform login with empty credentials (replace with actual credentials)
            loginPage.login(username, password);
            SleepUtils.sleep(2000); // Pause for 2 seconds

            // Change the job title on the profile page
            profilPage.changePoste(posteDuJour);
            SleepUtils.sleep(2000); // Pause for 2 seconds

        } finally {
            // Ensure the WebDriver is closed properly after execution
            WebDriverUtils.quitWebDriver();
        }
        Logger.info("Program end");
    }
}
