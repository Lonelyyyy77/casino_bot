// modal.js: логика модального окна выбора FS
document.addEventListener("DOMContentLoaded", function() {
    // Глобальные переменные, доступные основному скрипту
    window.selectedFS = 0;
    window.visualChanceBonus = 0;
  
    const fsModal = document.getElementById("fs-modal");
    const fsModalClose = document.getElementById("fs-modal-close");
  
    // Функция расчёта визуального бонуса: 1 FS = 2%, 10 FS = 10%, 30 FS = 23%
    function calculateVisualChance(fsCount) {
      if (fsCount === 1) return 2;
      else if (fsCount === 10) return 10;
      else if (fsCount === 30) return 23;
      else return fsCount * 2;
    }
  
    // Функция обновления состояния кнопок в модальном окне
    function updateFSModalButtons() {
      const freeSpinsElem = document.getElementById("freespins");
      const availableFS = parseInt(freeSpinsElem.textContent) || 0;
      document.querySelectorAll('.fs-modal-btn').forEach(button => {
        const btnFS = parseInt(button.getAttribute('data-fs'));
        if (availableFS < btnFS) {
          button.disabled = true;
        } else {
          button.disabled = false;
        }
      });
    }
  
    // Обработчики для кнопок модального окна
    document.querySelectorAll('.fs-modal-btn').forEach(button => {
      button.addEventListener('click', function(e) {
        const fsValue = parseInt(e.target.getAttribute('data-fs'));
        window.selectedFS = fsValue;
        window.visualChanceBonus = calculateVisualChance(fsValue);
        // Обновляем внешний блок выбора FS
        document.getElementById('fs-counter').textContent = fsValue;
        document.getElementById('fs-visual-chance').textContent = `Дополнительный шанс: +${window.visualChanceBonus}%`;
        console.log("Modal: Selected FS =", fsValue);
        fsModal.style.display = "none"; // Закрываем окно
      });
    });
  
    // Обработчик закрытия модального окна
    fsModalClose.addEventListener('click', function() {
      fsModal.style.display = "none";
    });
  
    // Экспорт функции обновления кнопок для использования в основном скрипте
    window.updateFSModalButtons = updateFSModalButtons;
  });
  