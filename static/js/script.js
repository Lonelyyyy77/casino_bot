// Initialize balance variables
let balance = "0 JPC";
let subBalance = "0 USDT | 0 Stars";

// Function to update balance dynamically
function updateBalance(newBalance, newSubBalance) {
    document.getElementById("balance").textContent = newBalance;
    document.getElementById("sub-balance").textContent = newSubBalance;
}

// Example of dynamic update (replace this with API integration later)
setTimeout(() => {
    updateBalance("150 JPC", "150 USDT | 6100 Stars");
}, 3000);
