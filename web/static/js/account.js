// Показ модального окна
document.getElementById("account-btn").addEventListener("click", function () {
    const modal = document.getElementById("account-modal");
    modal.style.display = "flex"; // Показываем модальное окно
    modal.classList.remove("hide"); // Убираем класс "hide", если он был
    modal.classList.add("show"); // Добавляем класс "show" для анимации
});

// Закрытие модального окна
document.getElementById("close-modal").addEventListener("click", function () {
    const modal = document.getElementById("account-modal");
    modal.classList.remove("show"); // Убираем класс "show"
    modal.classList.add("hide"); // Добавляем класс "hide" для анимации

    // Ждём завершения анимации перед скрытием
    setTimeout(() => {
        modal.style.display = "none"; // Полностью скрываем окно
    }, 300); // Время должно совпадать с длительностью анимации (0.3s)
});

// Закрытие при клике на фон
window.addEventListener("click", function (event) {
    const modal = document.getElementById("account-modal");
    if (event.target === modal) {
        modal.classList.remove("show");
        modal.classList.add("hide");

        // Ждём завершения анимации перед скрытием
        setTimeout(() => {
            modal.style.display = "none";
        }, 300);
    }
});