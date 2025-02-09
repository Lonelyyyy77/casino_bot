// web/slotmachine/slot_machine.go
package slotmachine

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"math/rand"
	"net/http"
	"time"

	"main.go/data" // используем существующий пакет для доступа к БД (data.DB)
)

// SlotMachine инкапсулирует логику игры и работу с БД.
type SlotMachine struct {
	DB *sql.DB
}

// PlayResponse – структура ответа на игровой запрос.
type PlayResponse struct {
	Status      string   `json:"status"`
	Message     string   `json:"message"` // loss, small, medium, big, jackpot, freespin
	Reels       []string `json:"reels"`
	WinAmount   float64  `json:"win_amount"`
	NewBalance  float64  `json:"new_balance"`
	FreeSpins   int      `json:"free_spins"`
	JackpotText string   `json:"jackpot_text,omitempty"`
}

// User – структура с данными пользователя (из таблицы user).
type User struct {
	TelegramID string
	Balance    float64
	FreeSpins  int
	TotalWin   float64
}

const (
	probLoss     = 85.0
	probSmall    = 7.0
	probMedium   = 2.0
	probBig      = 0.99
	probJackpot  = 0.01
	probFreeSpin = 5.0
)

var baseSymbols = []string{"🐬", "🐟", "🐙", "💎", "🌊"}

// New возвращает новый экземпляр SlotMachine, используя data.DB
func New() *SlotMachine {
	sm := &SlotMachine{
		DB: data.DB,
	}
	sm.initTables()
	rand.Seed(time.Now().UnixNano())
	return sm
}

// initTables выполняет миграции: создаёт таблицу jackpot и пытается добавить недостающие столбцы в user.
func (sm *SlotMachine) initTables() {
	// Создаём таблицу для прогрессивного джекпота
	_, err := sm.DB.Exec(`
		CREATE TABLE IF NOT EXISTS jackpot (
			id INTEGER PRIMARY KEY,
			amount REAL DEFAULT 0
		);
	`)
	if err != nil {
		log.Fatal(err)
	}
	_, err = sm.DB.Exec(`INSERT OR IGNORE INTO jackpot (id, amount) VALUES (1, 0);`)
	if err != nil {
		log.Fatal(err)
	}
	// Попытка добавить столбцы для режима FreeSpin и суммарных выигрышей
	_, _ = sm.DB.Exec(`ALTER TABLE user ADD COLUMN free_spins INTEGER DEFAULT 0;`)
	_, _ = sm.DB.Exec(`ALTER TABLE user ADD COLUMN total_win REAL DEFAULT 0;`)
}

// getUser возвращает данные пользователя по telegram_id.
func (sm *SlotMachine) getUser(telegramID string) (*User, error) {
	row := sm.DB.QueryRow("SELECT balance, free_spins, total_win FROM user WHERE telegram_id = ?", telegramID)
	user := &User{TelegramID: telegramID}
	err := row.Scan(&user.Balance, &user.FreeSpins, &user.TotalWin)
	if err != nil {
		return nil, err
	}
	return user, nil
}

// updateUserBalance обновляет баланс и суммарный выигрыш.
func (sm *SlotMachine) updateUserBalance(telegramID string, delta float64, win float64) error {
	_, err := sm.DB.Exec("UPDATE user SET balance = balance + ?, total_win = total_win + ? WHERE telegram_id = ?", delta, win, telegramID)
	return err
}

// updateFreeSpins устанавливает новое количество бесплатных вращений.
func (sm *SlotMachine) updateFreeSpins(telegramID string, newCount int) error {
	_, err := sm.DB.Exec("UPDATE user SET free_spins = ? WHERE telegram_id = ?", newCount, telegramID)
	return err
}

// getJackpot возвращает текущую сумму прогрессивного джекпота.
func (sm *SlotMachine) getJackpot() (float64, error) {
	var amount float64
	err := sm.DB.QueryRow("SELECT amount FROM jackpot WHERE id = 1").Scan(&amount)
	return amount, err
}

// updateJackpot устанавливает новое значение джекпота.
func (sm *SlotMachine) updateJackpot(newAmount float64) error {
	_, err := sm.DB.Exec("UPDATE jackpot SET amount = ? WHERE id = 1", newAmount)
	return err
}

// generateReels генерирует символы барабанов в зависимости от исхода.
func (sm *SlotMachine) generateReels(outcome string) []string {
	switch outcome {
	case "jackpot":
		sym := baseSymbols[rand.Intn(len(baseSymbols))]
		return []string{sym, sym, sym}
	case "small", "medium", "big":
		sym := baseSymbols[rand.Intn(len(baseSymbols))]
		if rand.Float64() < 0.5 {
			var other string
			for {
				other = baseSymbols[rand.Intn(len(baseSymbols))]
				if other != sym {
					break
				}
			}
			reels := []string{sym, sym, other}
			rand.Shuffle(len(reels), func(i, j int) { reels[i], reels[j] = reels[j], reels[i] })
			return reels
		}
		return []string{sym, sym, sym}
	case "freespin":
		reels := make([]string, 3)
		for i := 0; i < 3; i++ {
			reels[i] = baseSymbols[rand.Intn(len(baseSymbols))]
		}
		pos := rand.Intn(3)
		reels[pos] = "FREESPIN"
		return reels
	default: // loss – все символы различны
		if len(baseSymbols) < 3 {
			return baseSymbols
		}
		reel1 := baseSymbols[rand.Intn(len(baseSymbols))]
		var reel2 string
		for {
			reel2 = baseSymbols[rand.Intn(len(baseSymbols))]
			if reel2 != reel1 {
				break
			}
		}
		var reel3 string
		for {
			reel3 = baseSymbols[rand.Intn(len(baseSymbols))]
			if reel3 != reel1 && reel3 != reel2 {
				break
			}
		}
		return []string{reel1, reel2, reel3}
	}
}

// Play обрабатывает игровой запрос.
// Ожидается JSON с telegram_id, bet и mode ("normal" или "fs").
func (sm *SlotMachine) Play(w http.ResponseWriter, r *http.Request) {
	type PlayRequest struct {
		TelegramID string  `json:"telegram_id"`
		Bet        float64 `json:"bet"`
		Mode       string  `json:"mode"`
	}
	var req PlayRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	if req.Bet < 0.1 || req.Bet > 30 {
		http.Error(w, "Bet must be between 0.1 and 30 USDT", http.StatusBadRequest)
		return
	}

	user, err := sm.getUser(req.TelegramID)
	if err != nil {
		http.Error(w, "User not found", http.StatusBadRequest)
		return
	}

	useFreeSpin := false
	if req.Mode == "fs" {
		if user.FreeSpins > 0 {
			useFreeSpin = true
			user.FreeSpins--
			_ = sm.updateFreeSpins(req.TelegramID, user.FreeSpins)
		}
	}

	if !useFreeSpin {
		if user.Balance < req.Bet {
			http.Error(w, "Insufficient balance", http.StatusBadRequest)
			return
		}
		// Списываем ставку
		_ = sm.updateUserBalance(req.TelegramID, -req.Bet, 0)
		// Обновляем джекпот: 5% от ставки
		jackpot, _ := sm.getJackpot()
		jackpot += req.Bet * 0.05
		_ = sm.updateJackpot(jackpot)
	}

	// Определяем исход игры
	rFloat := rand.Float64() * 100
	outcome := "loss"
	multiplier := 0.0
	if rFloat < probLoss {
		outcome = "loss"
	} else if rFloat < probLoss+probSmall {
		outcome = "small"
		multiplier = 0.3 + rand.Float64()*(1.2-0.3)
	} else if rFloat < probLoss+probSmall+probMedium {
		outcome = "medium"
		multiplier = 1.5 + rand.Float64()*(4-1.5)
	} else if rFloat < probLoss+probSmall+probMedium+probBig {
		outcome = "big"
		multiplier = 5 + rand.Float64()*(30-5)
	} else if rFloat < probLoss+probSmall+probMedium+probBig+probJackpot {
		outcome = "jackpot"
		multiplier = 1500
	} else {
		outcome = "freespin"
		addFS := rand.Intn(3) + 1
		user.FreeSpins += addFS
		_ = sm.updateFreeSpins(req.TelegramID, user.FreeSpins)
	}

	winAmount := 0.0
	jackpotText := ""
	if outcome == "small" || outcome == "medium" || outcome == "big" || outcome == "jackpot" {
		winAmount = req.Bet * multiplier
		_ = sm.updateUserBalance(req.TelegramID, winAmount, winAmount)
	}
	if outcome == "jackpot" {
		jackpotWon, _ := sm.getJackpot()
		winAmount += jackpotWon
		_ = sm.updateUserBalance(req.TelegramID, jackpotWon, jackpotWon)
		jackpotText = fmt.Sprintf("🎉 Jackpot! You won an extra %.2f USDT!", jackpotWon)
		_ = sm.updateJackpot(0)
	}

	reels := sm.generateReels(outcome)
	updatedUser, _ := sm.getUser(req.TelegramID)

	resp := PlayResponse{
		Status:      "ok",
		Message:     outcome,
		Reels:       reels,
		WinAmount:   winAmount,
		NewBalance:  updatedUser.Balance,
		FreeSpins:   updatedUser.FreeSpins,
		JackpotText: jackpotText,
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(resp)
}

// GamePageHandler рендерит страницу слотов.
// Ожидается GET-параметр telegram_id, по которому загружаются данные пользователя.
func (sm *SlotMachine) GamePageHandler(w http.ResponseWriter, r *http.Request) {
	telegramID := r.URL.Query().Get("telegram_id")
	if telegramID == "" {
		http.Error(w, "telegram_id parameter is required", http.StatusBadRequest)
		return
	}
	user, err := sm.getUser(telegramID)
	if err != nil {
		http.Error(w, "User not found", http.StatusBadRequest)
		return
	}
	jackpot, _ := sm.getJackpot()
	dataTpl := struct {
		TelegramID string
		Balance    float64
		FreeSpins  int
		Jackpot    float64
	}{
		TelegramID: telegramID,
		Balance:    user.Balance,
		FreeSpins:  user.FreeSpins,
		Jackpot:    jackpot,
	}
	tmpl, err := template.ParseFiles("web/static/slot_machine.html")
	if err != nil {
		http.Error(w, "Error loading template", http.StatusInternalServerError)
		return
	}
	_ = tmpl.Execute(w, dataTpl)
}

// TopPlayersHandler возвращает JSON с топ-10 игроков по суммарным выигрышам.
func (sm *SlotMachine) TopPlayersHandler(w http.ResponseWriter, r *http.Request) {
	rows, err := sm.DB.Query("SELECT username, total_win FROM user ORDER BY total_win DESC LIMIT 10")
	if err != nil {
		http.Error(w, "Error fetching top players", http.StatusInternalServerError)
		return
	}
	defer rows.Close()
	type Player struct {
		Username string  `json:"username"`
		TotalWin float64 `json:"total_win"`
	}
	players := []Player{}
	for rows.Next() {
		var p Player
		err := rows.Scan(&p.Username, &p.TotalWin)
		if err != nil {
			continue
		}
		players = append(players, p)
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(players)
}
