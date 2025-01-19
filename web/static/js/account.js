document.getElementById("account-btn").addEventListener("click", function () {
    const modal = document.getElementById("account-modal");
    modal.style.display = "block"; // Показываем модальное окно
});

document.getElementById("close-modal").addEventListener("click", function () {
    const modal = document.getElementById("account-modal");
    modal.style.display = "none"; // Закрываем модальное окно
});

// Закрытие окна при клике вне его
window.addEventListener("click", function (event) {
    const modal = document.getElementById("account-modal");
    if (event.target === modal) {
        modal.style.display = "none";
    }
});
