// Глобальные переменные для фриспинов
let selectedFS = 0;
let visualChanceBonus = 0;

// Функция расчёта визуального бонуса (пример: 1 FS = +2%, 10 FS = +20%, 30 FS = +60%)
function calculateVisualChance(fsCount) {
  return fsCount * 2;
}

// Обработчики для кнопок фриспинов
document.querySelectorAll('.fs-btn').forEach(button => {
  button.addEventListener('click', (e) => {
    selectedFS = parseInt(e.target.getAttribute('data-fs'));
    // Обновляем отображение выбранного количества FS
    document.getElementById('fs-counter').textContent = selectedFS;
    // Пересчитываем визуальный бонус
    visualChanceBonus = calculateVisualChance(selectedFS);
    document.getElementById('fs-visual-chance').textContent = `Дополнительный шанс: +${visualChanceBonus}%`;
  });
});

// Изменённая функция игры с учетом FS
async function playGame() {
  const betInput = document.getElementById("bet");
  const bet = parseFloat(betInput.value);
  if (isNaN(bet) || bet < 0.1 || bet > 30) {
    alert("Введите корректную ставку (0.1-30)");
    return;
  }
  // Определяем, используется ли режим FS
  const fsMode = selectedFS > 0;
  
  // Отправляем на сервер все необходимые параметры
  const response = await fetch("/slots/play", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      telegram_id: telegramID, 
      bet: bet, 
      fsMode: fsMode, 
      fsCount: selectedFS, 
      visualChance: visualChanceBonus 
    })
  });
  const data = await response.json();
  
  // Обновляем баланс
  document.getElementById("balance").textContent = data.new_balance.toFixed(2);
  // Обновляем оставшиеся FS, если сервер возвращает обновлённое значение
  document.getElementById("fs-counter").textContent = data.remaining_fs;
  
  // Обновляем отображение барабанов
  const reelsDiv = document.getElementById("reels");
  reelsDiv.innerHTML = "";
  data.reels.forEach(symbol => {
    const reelDiv = document.createElement("div");
    reelDiv.className = "reel";
    reelDiv.textContent = symbol;
    reelsDiv.appendChild(reelDiv);
  });
  
  // Формируем текст результата
  let resultText = "";
  if (data.message === "loss") {
    resultText = `Вы проиграли ставку ${bet} JPC. ${data.visualChanceText || ''}`;
  } else if (data.message === "micro_win") {
    resultText = `Микро-выигрыш! Вы получили ${data.win_amount.toFixed(2)} JPC.`;
  } else if (data.message === "jackpot") {
    resultText = `Джекпот! Вы выиграли ${data.win_amount.toFixed(2)} JPC. ${data.jackpot_text}`;
  } else {
    resultText = `Вы выиграли ${data.win_amount.toFixed(2)} JPC (тип: ${data.message}).`;
  }
  document.getElementById("result").textContent = resultText;
  
  // Сброс выбора FS после игры
  selectedFS = 0;
  document.getElementById('fs-visual-chance').textContent = `Дополнительный шанс: 0%`;
}

