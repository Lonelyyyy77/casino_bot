// telegram.js

console.log("Telegram WebApp:", window.Telegram?.WebApp);
// Функция для отображения Telegram ID на странице
function displayTelegramID() {
    const initDataUnsafe = window.Telegram.WebApp.initDataUnsafe;
    const telegramID = initDataUnsafe?.user?.id;

    if (telegramID) {
        // Устанавливаем Telegram ID на странице
        const telegramIdElement = document.getElementById('telegramId');
        if (telegramIdElement) {
            telegramIdElement.textContent = `Telegram ID: ${telegramID}`;
        }

        // Отправляем Telegram ID на сервер
        sendTelegramID(telegramID);
    } else {
        console.error("Telegram ID не найден.");
        document.getElementById('telegramId').textContent = "Ошибка: Telegram ID не найден.";
    }
}

// Функция для отправки Telegram ID на сервер
async function sendTelegramID(telegramID) {
    try {
        const response = await fetch('/save_telegram_id', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: telegramID })
        });

        if (response.ok) {
            console.log("Telegram ID успешно отправлен!");
        } else {
            console.error("Ошибка при отправке Telegram ID.");
        }
    } catch (error) {
        console.error("Ошибка при запросе:", error);
    }
}

// Вызов функции при загрузке страницы
document.addEventListener("DOMContentLoaded", () => {
    const initDataUnsafe = window.Telegram.WebApp.initDataUnsafe;

    console.log("initDataUnsafe:", initDataUnsafe);

    if (initDataUnsafe && initDataUnsafe.user) {
        const telegramID = initDataUnsafe.user.id;
        console.log("Telegram ID:", telegramID);

        // Показать на странице
        document.getElementById('telegramId').textContent = `Telegram ID: ${telegramID}`;
    } else {
        console.error("Telegram WebApp не содержит данных пользователя.");
        document.getElementById('telegramId').textContent = "Ошибка: данные пользователя не найдены.";
    }
});

