// telegram.js

// Функция для отправки Telegram ID на сервер
async function sendTelegramID() {
    // Используем Telegram Web App API для получения данных
    const initDataUnsafe = window.Telegram.WebApp.initDataUnsafe;
    const telegramID = initDataUnsafe?.user?.id;

    if (!telegramID) {
        console.error("Telegram ID не найден.");
        return;
    }

    console.log("Telegram ID:", telegramID);

    // Отправка Telegram ID на сервер через POST-запрос
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
document.addEventListener("DOMContentLoaded", sendTelegramID);
