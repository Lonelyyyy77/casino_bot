// Получение telegram_id из URL
const urlParams = new URLSearchParams(window.location.search);
const telegramID = urlParams.get("telegram_id");

if (!telegramID) {
    alert("Telegram ID not found. Redirecting to the main page.");
    window.location.href = "index.html"; // Возврат на главную страницу, если ID не найден
} else {
    console.log("Telegram ID:", telegramID);
    // Здесь можно использовать telegramID для других целей
}

// Кнопка "Назад"
document.getElementById("back-btn").addEventListener("click", function (event) {
    event.preventDefault(); // Предотвращаем переход по ссылке
    const mainPageUrl = `/?telegram_id=${telegramID}`;
    window.location.href = mainPageUrl; // Возвращаемся на главную страницу с передачей telegram_id
});

// Кнопка "Крутить бесплатно"
document.getElementById("spin-now-btn").addEventListener("click", function () {
    alert("Вы прокрутили фриспин! Прокрут доступен раз в 24 часа.");
});
