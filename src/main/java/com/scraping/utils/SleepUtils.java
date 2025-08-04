package com.scraping.utils;

public class SleepUtils {

    /**
     * Pauses the execution for a specified amount of time.
     *
     * @param millis The time to sleep in milliseconds.
     */
    public static void sleep(long millis) {
        try {
            Thread.sleep(millis); // Pause for the specified amount of time
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); // Restore the interrupted status
            System.err.println("Thread sleep was interrupted: " + e.getMessage()); // Print error message
        }
    }
}
