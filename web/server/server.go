package server

import (
	"encoding/json"
	"fmt"
	"html/template"
	"net/http"

	"main.go/data"
	"main.go/slotmachine"
)

// TemplateData содержит данные для шаблона
type TemplateData struct {
	TelegramID string
	Balance    float64
}

// calcStars рассчитывает количество звёзд
func calcStars(balance float64) float64 {
	return balance / 0.013 // 1 звезда = 0.013 USDT
}

// ServeIndex рендерит HTML с данными баланса и Telegram ID
func ServeIndex(w http.ResponseWriter, r *http.Request) {
	telegramID := r.URL.Query().Get("telegram_id")
	if telegramID == "" {
		http.Error(w, "telegram_id is required", http.StatusBadRequest)
		return
	}

	var balance float64
	err := data.DB.QueryRow("SELECT balance FROM user WHERE telegram_id = ?", telegramID).Scan(&balance)
	if err != nil {
		fmt.Println("Error fetching balance:", err) // Добавьте логирование для отладки
		balance = 0.0
	}

	// Рендеринг шаблона
	tmpl, err := template.New("index.html").Funcs(template.FuncMap{
		"calcStars": calcStars,
	}).ParseFiles("web/static/index.html")

	if err != nil {
		http.Error(w, "Error loading template", http.StatusInternalServerError)
		return
	}

	data := TemplateData{
		TelegramID: telegramID,
		Balance:    balance,
	}

	err = tmpl.Execute(w, data)
	if err != nil {
		http.Error(w, "Error rendering template", http.StatusInternalServerError)
	}
}

// UpdateBalanceHandler обновляет баланс пользователя
func UpdateBalanceHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}

	// Разбираем JSON тело запроса
	var requestData struct {
		TelegramID string  `json:"telegram_id"`
		Amount     float64 `json:"amount"`
	}
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, "Failed to parse request body", http.StatusBadRequest)
		return
	}

	// Обновляем баланс в базе данных
	_, err := data.DB.Exec("UPDATE user SET balance = balance + ? WHERE telegram_id = ?", requestData.Amount, requestData.TelegramID)
	if err != nil {
		http.Error(w, "Failed to update balance", http.StatusInternalServerError)
		return
	}

	// Ответ об успешной операции
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "success"}`))
}

func ServeFreeSpin(w http.ResponseWriter, r *http.Request) {
	telegramID := r.URL.Query().Get("telegram_id")
	if telegramID == "" {
		http.Error(w, "telegram_id is required", http.StatusBadRequest)
		return
	}

	// Получаем баланс из базы данных
	var balance float64
	err := data.DB.QueryRow("SELECT balance FROM user WHERE telegram_id = ?", telegramID).Scan(&balance)
	if err != nil {
		fmt.Println("Error fetching balance:", err)
		balance = 0.0 // Если ошибка, баланс по умолчанию
	}

	// Рендерим шаблон freespin.html
	tmpl, err := template.New("freespin.html").ParseFiles("./web/static/freespin.html")
	if err != nil {
		fmt.Println("Error loading template:", err)
		http.Error(w, "Error loading template", http.StatusInternalServerError)
		return
	}

	// Передача данных в шаблон
	data := struct {
		Balance    float64
		TelegramID string
	}{
		Balance:    balance,
		TelegramID: telegramID,
	}

	err = tmpl.Execute(w, data)
	if err != nil {
		fmt.Println("Error rendering template:", err)
		http.Error(w, "Error rendering template", http.StatusInternalServerError)
	}
}

// StartServer запускает HTTP сервер и регистрирует все обработчики, включая новые для слотов.
func StartServer() {

	// Обработка статических файлов
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("./web/static"))))

	http.HandleFunc("/", ServeIndex)

	http.HandleFunc("/freespin", ServeFreeSpin)

	http.HandleFunc("/update_balance", UpdateBalanceHandler)

	// Регистрируем обработчики для слотов:
	sm := slotmachine.New()
	http.HandleFunc("/slots/", sm.GamePageHandler)      // Страница игры: /slots/?telegram_id=...
	http.HandleFunc("/slots/play", sm.Play)             // Endpoint для вращения
	http.HandleFunc("/slots/top", sm.TopPlayersHandler) // Топ-10 игроков

	fmt.Println("SlotMachine endpoints registered under /slots/")

	fmt.Println("Starting server on :8080")
	err := http.ListenAndServe(":8080", nil)
	if err != nil {
		fmt.Println("Error starting server:", err)
	}
}
