package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"

	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

// Инициализация базы данных
func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./main2.db") // Используем вашу базу данных
	if err != nil {
		log.Fatal(err)
	}

	// Проверяем подключение к базе
	err = db.Ping()
	if err != nil {
		log.Fatal("Ошибка подключения к базе данных:", err)
	}
	fmt.Println("База данных подключена!")
}

// Главная страница
func mainPageHandler(w http.ResponseWriter, r *http.Request) {
	telegramID := r.URL.Query().Get("telegram_id")
	if telegramID == "" {
		http.Error(w, "telegram_id is required", http.StatusBadRequest)
		return
	}

	// Получаем баланс из базы данных
	var balance float64
	err := db.QueryRow("SELECT balance FROM user WHERE telegram_id = ?", telegramID).Scan(&balance)
	if err != nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	// Передаём данные в HTML
	data := struct {
		TelegramID string
		Balance    float64
	}{
		TelegramID: telegramID,
		Balance:    balance,
	}

	tmpl, err := template.ParseFiles("./static/index.html")
	if err != nil {
		http.Error(w, "Error parsing template", http.StatusInternalServerError)
		return
	}

	tmpl.Execute(w, data)
}

// Обновление баланса
func updateBalanceHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}

	// Парсим данные из запроса
	var req struct {
		TelegramID string  `json:"telegram_id"`
		Amount     float64 `json:"amount"`
	}
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil || req.TelegramID == "" {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Обновляем баланс в базе данных
	_, err = db.Exec("UPDATE user SET balance = balance + ? WHERE telegram_id = ?", req.Amount, req.TelegramID)
	if err != nil {
		http.Error(w, "Failed to update balance", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "Balance updated successfully for Telegram ID %s", req.TelegramID)
}

func main() {
	initDB()
	defer db.Close()

	// Раздача статических файлов
	fs := http.FileServer(http.Dir("./static"))
	http.Handle("/static/", http.StripPrefix("/static/", fs))

	// Основной маршрут
	http.HandleFunc("/", mainPageHandler)

	// Маршрут обновления баланса
	http.HandleFunc("/update_balance", updateBalanceHandler)

	fmt.Println("Сервер запущен на http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
