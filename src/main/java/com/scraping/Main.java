package com.scraping;

import java.time.LocalDate;

import com.scraping.pages.LoginPage;
import com.scraping.pages.ProfilPage;
import com.scraping.utils.SleepUtils;
import com.scraping.utils.WebDriverUtils;

public class Main {
    public static void main(String[] args) {
        // Initialize the WebDriver to start browser automation
        WebDriverUtils.initWebDriver();

        String posteDuJour; // Variable to store the job title of the day

        // Check if the current day of the month is even or odd
        if (LocalDate.now().getDayOfMonth() % 2 == 0) {
            System.out.println("Ingénieur logiciel");
            posteDuJour = "Ingénieur logiciel"; // Set job title for even days
        } else {
            System.out.println("Développeur logiciel");
            posteDuJour = "Développeur logiciel"; // Set job title for odd days
        }

        try {
            // Navigate to the login page
            LoginPage loginPage = new LoginPage();
            ProfilPage profilPage = new ProfilPage();

            // Open the login page
            loginPage.open();
            SleepUtils.sleep(2000); // Pause for 2 seconds

            // Perform login with empty credentials (replace with actual credentials)
            loginPage.login("", "");
            SleepUtils.sleep(2000); // Pause for 2 seconds

            // Change the job title on the profile page
            profilPage.changePoste(posteDuJour);
            SleepUtils.sleep(2000); // Pause for 2 seconds

        } finally {
            // Ensure the WebDriver is closed properly after execution
            WebDriverUtils.quitWebDriver();
        }
    }
}
