document.addEventListener("DOMContentLoaded", function () {
    // check if the current page is the room selection page
    if (!document.querySelector("#duo_bed_size_1")) {
        return; // Exit if not on the room selection page
    }
    // OPTION 1
    const bedSize1 = document.getElementById("duo_bed_size_1");
    const bedSize2 = document.getElementById("duo_bed_size_2");
    const bedNum1 = document.getElementById("duo_bed_num_1");
    const nextButton = document.querySelector("input[type='submit']");
    const errorPaneDiv = document.getElementById("error-pane-divide"); // Reference the pre-existing error pane
    // OPTION 2
    const bedSize1Seq = document.getElementById("seq_bed_size_1"); // Initialize bedSize1Seq here
    const addRoomBtn = document.getElementById("add-room-btn"); // Reference the Add Room button
    const removeRoomBtn = document.getElementById("remove-room-btn"); // Reference the Remove Last Row button
    const roomsTable = document.getElementById("rooms-table").querySelector("tbody"); // Reference the table body
    const toggleSuperincreasing = document.getElementById("room-superincreasing"); // Reference the toggle switch
    // Tabs
    const duoSelectionTab = document.getElementById("pills-duo-tab");
    const sequentialTab = document.getElementById("pills-seq-tab");
    const modeInput = document.getElementById('current-room-mode'); // assign the current room mode to an input field

    // option 1
    // Function to check divisibility between Room 1 and Room 2
    function checkDivisibility() {
        const size1 = parseInt(bedSize1.value, 10);
        const size2 = parseInt(bedSize2.value, 10);

        if (size1 > 0 && size2 > 0 && size2 % size1 !== 0) {
            // Show the error pane if bed_size_1 does not divide bed_size_2
            errorPaneDiv.classList.remove("d-none");
            nextButton.disabled = true; // Disable the "Next" button
        } else {
            // Hide the error pane and enable the "Next" button
            errorPaneDiv.classList.add("d-none");
            nextButton.disabled = false;

            // Calculate `n` such that `r_1 * n = r_2`
            const n = size2 / size1;
            // set the minimum value of bed_num_1 to n - 1
            bedNum1.setAttribute("min", Math.max(n - 1,0));

            // Update the amount of Room 1 if it's less than `n - 1`
            const currentNum1 = parseInt(bedNum1.value, 10);
            if (currentNum1 < n - 1) {
                bedNum1.value = n - 1;
            }
        }
    }

    // option 2
    // Function to update all room sizes based on Room 1 size
    function updateRoomSizes() {
        const room1Size = parseInt(bedSize1Seq.value, 10); // Get the size of Room 1

        if (isNaN(room1Size) || room1Size < 0) {
            alert("Please enter a valid size for Room 1.");
            return;
        }

        // Check if the toggleSuperincreasing is activated
        const isSuperincreasing = toggleSuperincreasing.checked;

        // Loop through all rows and update the size input
        Array.from(roomsTable.rows).forEach((row, index) => {
            if (index === 0) return; // Skip Room 1
            const sizeInput = row.querySelector(`input[id="seq_bed_size_${index + 1}"]`);
            if (sizeInput) {
                sizeInput.value = isSuperincreasing
                ? room1Size * Math.pow(2, index) // Use 2^i for superincreasing
                : room1Size * (index + 1); // Use index + 1 for linear increasing
            }
        });
    }

    // option 2
    // Add a new row to the table
    function getTableRow(rowCount,initSize=0,initNum=1) {
        return `<td class="text-start"><strong>Room Type ${rowCount}</strong></td>
            <td>
                <input id="seq_bed_size_${rowCount}" type="number" class="form-control text-center" name="seq_bed_size_${rowCount}" value="${initSize}" max="1000" disabled>
            </td>
            <td>
                <input id="seq_bed_num_${rowCount}" type="number" class="form-control text-center" name="seq_bed_num_${rowCount}" value="${initNum}" min="1" max="1000" step="1">
            </td>
        `;
    }
    function addRoomRow() {
        const rowCount = roomsTable.rows.length + 1; // Get the current number of rows
        const newRow = document.createElement("tr");

        newRow.innerHTML = getTableRow(rowCount); // Create a new row with the current row count

        roomsTable.appendChild(newRow); // Append the new row to the table
        updateRoomSizes(); // Update all room sizes after adding a new row
    }

    // option 2
    // Remove the last row from the table
    function removeLastRoomRow() {
        const rowCount = roomsTable.rows.length; // Get the current number of rows
        if (rowCount > 1) {
            roomsTable.deleteRow(rowCount - 1); // Remove the last row
        } else {
            // alert("You must have at least one room!"); // Prevent removing the last row
        }
    }

    // option 1
    // Add event listeners for bed size inputs
    bedSize1.addEventListener("input", checkDivisibility);
    bedSize2.addEventListener("input", checkDivisibility);
    // Check divisibility on page load
    checkDivisibility();
    // Set the minimum value of bed_num_1 to n - 1 (which is now stored in the min attribute)
    // bedNum1.addEventListener("input", () => {
    //     const min = parseInt(bedNum1.getAttribute("min"), 10);
    //     if (parseInt(bedNum1.value, 10) < min) {
    //         bedNum1.value = min; // Set to minimum value
    //         errorPaneAmount.classList.remove("d-none"); // Show the error pane
    //         setTimeout(() => {
    //             errorPaneAmount.classList.add("d-none"); // Hide the error pane after 3 seconds
    //         }, 3000);
    //     }
    // });


    // option 2
    // Add event listeners
    bedSize1Seq.addEventListener("input", () => {
        updateRoomSizes(); // Update all room sizes when Room 1 size changes
    });
    toggleSuperincreasing.addEventListener("change", () => {
        updateRoomSizes(); // Update all room sizes when the toggle state changes
    });
    addRoomBtn.addEventListener("click", addRoomRow); // Add a new row
    removeRoomBtn.addEventListener("click", removeLastRoomRow); // Remove the last row
    updateRoomSizes(); // Initialize room sizes on page load


    // Add event listeners for tab switching
    duoSelectionTab.addEventListener("shown.bs.tab", (event) => {
        nextButton.disabled = false; // Enable the "Next" button
        checkDivisibility(); // Run checkDivisibility when Duo Selection is activated
        modeInput.value = "duo"; // Set the current room mode to "duo"
    });
    sequentialTab.addEventListener("shown.bs.tab", (event) => {
        nextButton.disabled = false; // Enable the "Next" button
        updateRoomSizes(); // Run updateRoomSizes when Sequential is activated
        modeInput.value = "seq"; // Set the current room mode to "seq"
    });


    // Initialize the current room mode (reading out from input field) and append the table entries
    if (modeInput.value === "duo") {
        duoSelectionTab.click(); // Activate the Duo Selection tab
    } else if (modeInput.value === "seq") {
        sequentialTab.click(); // Activate the Sequential tab
    }
    
});
