const telegramID = document.getElementById("telegram-id").textContent;

// Функция обновления баланса
function updateBalance() {
    fetch('/update_balance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            telegram_id: telegramID,
            amount: 10.0,
        }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                console.log("Balance updated successfully:", data);
                location.reload(); // Перезагружаем страницу
            } else {
                alert("Failed to update balance");
            }
        })
        .catch(error => {
            console.error("Error updating balance:", error);
        });
}

// Добавляем обработчики для кнопок
document.getElementById('update-balance-btn').addEventListener('click', updateBalance);
document.getElementById('casino-btn').addEventListener('click', () => {
    alert("Go to Casino Page");
});
document.getElementById('account-btn').addEventListener('click', () => {
    alert("Go to Account Page");
});
document.getElementById('freespin-btn').addEventListener('click', () => {
    alert("Go to Free Spin");
});
