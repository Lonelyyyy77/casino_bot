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

	"main.go/data" // Используем существующий пакет для доступа к БД (data.DB)
)

// jackpotChance – текущая вероятность джекпота (в процентах).
// Изначально 0.001%, при проигрыше увеличивается на 0.0005% и сбрасывается после джекпота.
var jackpotChance float64 = 0.001

// PlayResponse – структура ответа на игровой запрос.
type PlayResponse struct {
	Status           string   `json:"status"`
	Message          string   `json:"message"` // Возможные значения: "loss", "micro_win", "normal_win", "jackpot", "extra_spins"
	Reels            []string `json:"reels"`
	WinAmount        float64  `json:"win_amount"`
	NewBalance       float64  `json:"new_balance"`
	FreeSpins        int      `json:"free_spins"`
	JackpotText      string   `json:"jackpot_text,omitempty"`
	VisualChanceText string   `json:"visualChanceText,omitempty"`
}

// User – структура с данными пользователя (из таблицы user).
type User struct {
	TelegramID string
	Balance    float64
	FreeSpins  int
	TotalWin   float64
}

// ExtendedPlayRequest – структура запроса, включающая расширенные поля для фриспинов.
type ExtendedPlayRequest struct {
	TelegramID   string  `json:"telegram_id"`
	Bet          float64 `json:"bet"`
	Mode         string  `json:"mode"`         // "normal" или "fs"
	FSCount      int     `json:"fsCount"`      // Количество фриспинов, если Mode == "fs"
	VisualChance int     `json:"visualChance"` // Значение для визуального бонуса (передаётся с клиента)
}

const (
	// Вероятности для обычного режима (в процентах):
	normalJackpotProb = 0.001
	normalWinProb     = 5.0
	microWinProb      = 15.0
	freeSpinProb      = 11.5
)

// baseSymbols – базовые символы для барабанов.
var baseSymbols = []string{"🐬", "🐟", "🐙", "💎", "🌊"}

// SlotMachine инкапсулирует логику игры и работу с БД.
type SlotMachine struct {
	DB *sql.DB
}

// New возвращает новый экземпляр SlotMachine, используя data.DB.
func New() *SlotMachine {
	sm := &SlotMachine{
		DB: data.DB,
	}
	sm.initTables()
	rand.Seed(time.Now().UnixNano())
	return sm
}

// initTables выполняет миграции: создаёт таблицу jackpot и добавляет недостающие столбцы в user.
func (sm *SlotMachine) initTables() {
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
	case "normal_win":
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
	case "micro_win":
		sym := baseSymbols[rand.Intn(len(baseSymbols))]
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
	case "extra_spins":
		reels := make([]string, 3)
		for i := 0; i < 3; i++ {
			reels[i] = baseSymbols[rand.Intn(len(baseSymbols))]
		}
		pos := rand.Intn(3)
		reels[pos] = "FREESPIN"
		return reels
	default: // "loss" – все символы различны.
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
func (sm *SlotMachine) Play(w http.ResponseWriter, r *http.Request) {
	var req ExtendedPlayRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	user, err := sm.getUser(req.TelegramID)
	if err != nil {
		http.Error(w, "User not found", http.StatusBadRequest)
		return
	}

	var bet float64
	var outcome string
	var multiplier float64
	var winAmount float64

	if req.Mode == "fs" {
		if user.FreeSpins < req.FSCount {
			http.Error(w, "Недостаточно фриспинов", http.StatusBadRequest)
			return
		}
		bet = 2.0 // Fixed bet for Freespin mode
		_ = sm.updateFreeSpins(req.TelegramID, user.FreeSpins-req.FSCount)

		// Adjust probabilities based on FSCount
		var microWinProb, normalWinProb, jackpotProb, extraSpinsProb float64
		switch req.FSCount {
		case 1:
			microWinProb = 5.0
			normalWinProb = 2.0
			jackpotProb = 0.0008
			extraSpinsProb = 3.8
		case 10:
			microWinProb = 10.0
			normalWinProb = 4.8
			jackpotProb = 0.0009
			extraSpinsProb = 5.3
		case 30:
			microWinProb = 15.0
			normalWinProb = 10.0
			jackpotProb = 0.001
			extraSpinsProb = 7.3
		default:
			http.Error(w, "Invalid FSCount", http.StatusBadRequest)
			return
		}

		rFloat := rand.Float64() * 100
		switch {
		case rFloat < jackpotProb:
			outcome = "jackpot"
			multiplier = 1500
		case rFloat < jackpotProb+normalWinProb:
			outcome = "normal_win"
			multiplier = 5.0 + rand.Float64()*5.0 // 5x to 10x
		case rFloat < jackpotProb+normalWinProb+microWinProb:
			outcome = "micro_win"
			multiplier = 1.5 + rand.Float64()*1.5 // 1.5x to 3x
		case rFloat < jackpotProb+normalWinProb+microWinProb+extraSpinsProb:
			outcome = "extra_spins"
			user.FreeSpins += 2
			_ = sm.updateFreeSpins(req.TelegramID, user.FreeSpins)
		default:
			outcome = "loss"
		}
	} else {
		bet = req.Bet
		if user.Balance < bet {
			http.Error(w, "Insufficient balance", http.StatusBadRequest)
			return
		}
		_ = sm.updateUserBalance(req.TelegramID, -bet, 0)
		jackpot, _ := sm.getJackpot()
		jackpot += bet * 0.05
		_ = sm.updateJackpot(jackpot)

		rFloat := rand.Float64() * 100
		switch {
		case rFloat < normalJackpotProb:
			outcome = "jackpot"
			multiplier = 1500
		case rFloat < normalJackpotProb+normalWinProb:
			outcome = "normal_win"
			multiplier = 1.05 + rand.Float64()*0.05
		case rFloat < normalJackpotProb+normalWinProb+microWinProb:
			outcome = "micro_win"
			multiplier = 1.3 - (bet-1)*0.008 + rand.Float64()*0.01
		case rFloat < normalJackpotProb+normalWinProb+microWinProb+freeSpinProb:
			outcome = "extra_spins"
			user.FreeSpins++
			_ = sm.updateFreeSpins(req.TelegramID, user.FreeSpins)
		default:
			outcome = "loss"
		}
	}

	// Calculate winAmount and update balance
	jackpotText := ""
	switch outcome {
	case "jackpot":
		jackpotWon, _ := sm.getJackpot()
		winAmount = bet*multiplier + jackpotWon
		_ = sm.updateUserBalance(req.TelegramID, winAmount, winAmount)
		_ = sm.updateJackpot(0)
		jackpotText = fmt.Sprintf("🎉 Jackpot! You won an extra %.2f USDT!", jackpotWon)
		jackpotChance = 0.001
	case "normal_win", "micro_win":
		winAmount = bet * multiplier
		_ = sm.updateUserBalance(req.TelegramID, winAmount, winAmount)
	case "extra_spins":
		winAmount = 0 // No direct monetary win for extra spins
	case "loss":
		winAmount = 0
		if req.Mode != "fs" {
			jackpotChance += 0.0005
		}
	}

	reels := sm.generateReels(outcome)
	updatedUser, _ := sm.getUser(req.TelegramID)
	visualText := ""
	if outcome == "loss" || outcome == "micro_win" {
		visualText = fmt.Sprintf("+%d%% к шансу", req.VisualChance)
	}

	resp := PlayResponse{
		Status:           "ok",
		Message:          outcome,
		Reels:            reels,
		WinAmount:        winAmount,
		NewBalance:       updatedUser.Balance,
		FreeSpins:        updatedUser.FreeSpins,
		JackpotText:      jackpotText,
		VisualChanceText: visualText,
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(resp)
}

// GamePageHandler рендерит страницу слотов по GET-параметру telegram_id.
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
