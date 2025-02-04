const telegramID = document.getElementById("telegram-id").textContent;

// Проверяем наличие Telegram ID
if (!telegramID) {
    alert("Telegram ID is missing!");
    throw new Error("Telegram ID is required but missing.");
} else {
    console.log("Telegram ID:", telegramID); // Логируем для проверки
}

// Функция для получения параметра из URL
function getParameterByName(name) {
    const url = new URL(window.location.href);
    return url.searchParams.get(name);
}

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
        .then(response => {
            if (!response.ok) throw new Error("Failed to update balance");
            return response.json();
        })
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

// Привязываем ссылку с параметром telegram_id к кнопке freespin
document.getElementById("freespin-btn").addEventListener("click", function (event) {
    event.preventDefault(); // Предотвращаем стандартное поведение ссылки
    const freespinUrl = `freespin.html?telegram_id=${telegramID}`;
    window.location.href = freespinUrl; // Перенаправление на страницу freespin.html
});

// Добавляем обработчики для кнопок
document.getElementById('update-balance-btn')?.addEventListener('click', updateBalance);

document.getElementById('casino-btn')?.addEventListener('click', () => {
    alert("Go to Casino Page");
});

document.getElementById('account-btn')?.addEventListener('click', () => {
    const modal = document.getElementById("account-modal");
    modal.style.display = "flex"; // Открываем модальное окно
});

document.getElementById('freespin-btn')?.addEventListener('click', () => {
    console.log("Redirecting to Free Spin...");
});

// Закрытие модального окна
document.getElementById("close-modal")?.addEventListener("click", function () {
    const modal = document.getElementById("account-modal");
    modal.style.display = "none"; // Закрываем модальное окно
});

// Закрытие модального окна при клике вне области
window.addEventListener("click", function (event) {
    const modal = document.getElementById("account-modal");
    if (event.target === modal) {
        modal.style.display = "none";
    }
});

// Адаптация темы Telegram
document.addEventListener("DOMContentLoaded", () => {
    if (window.Telegram.WebApp.themeParams) {
        const theme = window.Telegram.WebApp.themeParams;
        document.body.style.background = theme.bg_color || "#0f172a";
        document.body.style.color = theme.text_color || "white";
    }
});
