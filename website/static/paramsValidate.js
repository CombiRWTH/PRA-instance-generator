document.addEventListener("DOMContentLoaded", function () {
    // Check if the current page is the parameters selection page
    if (!document.querySelector("#current-param-mode")) {
        return; // Exit if not on the parameters selection page
    }

    // Tabs
    const DefaultTab = document.getElementById("pills-default-tab");
    const advancedTab = document.getElementById("pills-advanced-tab");
    const modeInput = document.getElementById('current-param-mode'); // assign the current room mode to an input field


    // Add event listeners for tab switching
    DefaultTab.addEventListener("shown.bs.tab", (event) => {
        modeInput.value = "default"; // Set the current room mode to "default"
    });
    advancedTab.addEventListener("shown.bs.tab", (event) => {
        modeInput.value = "advanced"; // Set the current room mode to "advanced"
    });

    // Initialize the current param mode (reading out from input field) and append the table entries
    if (modeInput.value === "default") {
        DefaultTab.click(); // Activate the Duo Selection tab
    } else if (modeInput.value === "advanced") {
        advancedTab.click(); // Activate the Sequential tab
    }
});