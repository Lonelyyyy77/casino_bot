const telegramId = "{{.TelegramID}}";
let isSpinning = false;
let currentMode = "normal";
let selectedFSCount = 0;

async function spin() {
    if (isSpinning) return;
    
    const betAmount = parseFloat(document.getElementById('betAmount').value);
    
    if (currentMode === "normal" && (betAmount < 0.1 || betAmount > 30)) {
        alert('Ставка должна быть от 0.1 до 30 USDT');
        return;
    }

    isSpinning = true;
    document.getElementById('spinButton').disabled = true;
    document.getElementById('freespinButton').disabled = true;

    try {
        const response = await fetch('/slots/play', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                telegram_id: telegramId,
                bet: betAmount,
                mode: currentMode,
                fsCount: selectedFSCount,
                visualChance: Math.floor(Math.random() * 5) + 1
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const result = await response.json();
        
        // Animate reels
        const reels = document.querySelectorAll('.reel-container');
        const symbols = result.reels;
        
        reels.forEach((reel, index) => {
            // Create animation effect
            const symbolsToShow = ['🐬', '🐟', '🐙', '💎', '🌊'];
            let currentPos = 0;
            
            const interval = setInterval(() => {
                reel.textContent = symbolsToShow[currentPos];
                currentPos = (currentPos + 1) % symbolsToShow.length;
            }, 100);

            // Stop animation after delay
            setTimeout(() => {
                clearInterval(interval);
                reel.textContent = symbols[index];
                
                // If this is the last reel, show results
                if (index === 2) {
                    showResults(result);
                }
            }, 1000 + (index * 500));
        });

    } catch (error) {
        console.error('Error:', error);
        alert('Произошла ошибка при вращении');
    } finally {
        setTimeout(() => {
            isSpinning = false;
            document.getElementById('spinButton').disabled = false;
            document.getElementById('freespinButton').disabled = false;
        }, 2500);
    }
}

function showResults(result) {
    const winMessage = document.getElementById('winMessage');
    let message = '';

    switch(result.message) {
        case 'jackpot':
            message = `🎉 ДЖЕКПОТ! Выигрыш: ${result.win_amount.toFixed(2)} USDT`;
            break;
        case 'normal_win':
            message = `🎉 Выигрыш: ${result.win_amount.toFixed(2)} USDT`;
            break;
        case 'micro_win':
            message = `✨ Маленький выигрыш: ${result.win_amount.toFixed(2)} USDT`;
            break;
        case 'extra_spins':
            message = '🎁 Вы выиграли Free Spin!';
            break;
        default:
            if (result.visualChanceText) {
                message = result.visualChanceText;
            }
    }

    if (message) {
        winMessage.textContent = message;
        winMessage.style.display = 'block';
        setTimeout(() => {
            winMessage.style.display = 'none';
        }, 3000);
    }

    // Update balance and free spins after showing the result
    document.getElementById('balance').textContent = result.new_balance.toFixed(2);
    document.getElementById('freeSpins').textContent = result.free_spins;
    
    // Update jackpot if needed
    if (result.jackpot_text) {
        document.getElementById('jackpot').textContent = '0.00';
    }
}

async function updateTopPlayers() {
    try {
        const response = await fetch('/slots/top');
        const players = await response.json();
        
        const list = document.getElementById('topPlayersList');
        list.innerHTML = players.map(player => `
            <div class="player-item">
                <span>${player.username}</span>
                <span>${player.total_win.toFixed(2)} USDT</span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error updating top players:', error);
    }
}

document.getElementById('spinButton').addEventListener('click', () => {
    currentMode = "normal";
    spin();
});

document.getElementById('freespinButton').addEventListener('click', () => {
    const fsControls = document.querySelector('.fs-controls');
    fsControls.style.display = fsControls.style.display === 'none' ? 'flex' : 'none';
});

document.querySelectorAll('.fs-button').forEach(button => {
    button.addEventListener('click', () => {
        currentMode = "fs";
        selectedFSCount = parseInt(button.dataset.fs);
        spin();
    });
});

// Update top players every 30 seconds
updateTopPlayers();
setInterval(updateTopPlayers, 30000);