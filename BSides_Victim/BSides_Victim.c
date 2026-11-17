#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"
#include "tiny_sha.h"

// FOR DEBUGGING ADD THE FOLLOWING INCLUDE:
// #include "pico/stdio_usb.h"

// This Code runs on the Victim Pi Pico and performs a SHA3 512 Hash


// Define UART
#define UART_ID uart0
#define BAUD_RATE 115200

// Set UART TX and RX pins
#define UART_TX_PIN 12
#define UART_RX_PIN 13

// Define Victim Pi pin for onboard LED
const uint LED_ONBOARD_PIN = 25;
// Define Victim Pi pin to show when the hash process is running
const uint GP_VICTIM_TRIG = 26;


enum errorCode
{
    SUCCESS = 0,
};


int main()
{
    // Initialise GPIO pin for onboard LED to an output
    // Turn on the LED when the victim is on for a visual indicator
    gpio_init(LED_ONBOARD_PIN);
    gpio_set_dir(LED_ONBOARD_PIN, GPIO_OUT);
    gpio_put(LED_ONBOARD_PIN, 1);

    // Initialise GPIO pin for Victim Trigger to an output
    // This tells us when the Victim Pico hash process is running 
    // We will also use it to tell the Control Pi when the hash process is happening
    // This pin is Active Low, therefore it is initialised to High and goes low when the hash process is about to begin
    gpio_init(GP_VICTIM_TRIG);
    gpio_set_dir(GP_VICTIM_TRIG, GPIO_OUT);
    gpio_put(GP_VICTIM_TRIG, 1);

    stdio_init_all();

    // Set up our UART using defined information
    uart_init(UART_ID, BAUD_RATE);
    // Set the TX and RX pins by using the function select on the GPIO
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);
    
    // Initialise the ciphertext
    unsigned char hash[128];
    unsigned char hash_lfcr[130];

    int i;
    
    // Clear the memory of the Victim Pi before starting process and initialsie variables to 0
    for (i = 0; i < 128; i++)
    {
    hash_lfcr[i] = '0';
    hash[i] = '0';
    }

    // SHA3 512 Encryption

    // Define the Plaintext (hash input data)
    // To stay consistent with the research paper, we will use the same input
    unsigned char plaintext[] = {
        0x00, 0x01, 0x02, 0x03,
        0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x10, 0x11,
        0x12, 0x13, 0x14, 0x15,
        0x16, 0x17, 0x18, 0x19,
        0x20, 0x21, 0x22, 0x23,
        0x24, 0x25, 0x26, 0x27,
        0x28, 0x29, 0x30, 0x31
    };

    // Set Victim Trigger GPIO to low
    // This indicated we are about to start our hash process
    gpio_put(GP_VICTIM_TRIG, 0);

    // Call SHA3_512 function, passing through our plaintext as the input
    SHA3_512(plaintext, sizeof(plaintext), hash);

    // Set Victim Trigger to High to show our process is finished
    gpio_put(GP_VICTIM_TRIG, 1);
    
    // Add a sleep to make sure hash process has completed
    sleep_ms(1);
    
    // Iterate through the hash and store it in the hash variable
    for (i = 0; i < 128; i++)
    {
        hash_lfcr[i] = hash[i];
    }
    hash_lfcr[128]='\n';

    // FOR DEBUGGING:
    // ENABLE pico_enable_stdio_usb(BSides_Victim 1) in CMakeLists.txt
    // Make sure to also add the include that is commented out at the top
    /*
    while (!stdio_usb_connected()) {
        sleep_ms(100);
    }
    printf("SHA3-512 digest:\n");
    for (i = 0; i < 64; i++) {
        printf("%02X", hash[i]);
    }
    printf("\n");
    */

    // Write the hash out over UART
    uart_write_blocking(UART_ID, hash_lfcr, sizeof(hash_lfcr));

    // Add a sleep to ensure our hash has been fully sent over UART
    sleep_ms(20);

    // Add an infinite while loop to stop the Victim Pi from returning or ending in a strange state
    // This keeps Victim Pi on and powered after the hash has been run
    while(true);
    
};

