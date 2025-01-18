package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

// Структура для обработки входящих данных
type TelegramIDRequest struct {
	TelegramID string `json:"telegram_id"`
}

// Инициализация базы данных
func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./main2.db")
	if err != nil {
		log.Fatal(err)
	}

	// Создание таблицы, если она не существует
	query := `
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		telegram_id TEXT UNIQUE NOT NULL
	);
	`
	_, err = db.Exec(query)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("База данных инициализирована!")
}

// Обработчик для сохранения Telegram ID
func saveTelegramID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}

	var req TelegramIDRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil || req.TelegramID == "" {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Сохранение Telegram ID в базе данных
	query := `INSERT INTO users (telegram_id) VALUES (?) ON CONFLICT(telegram_id) DO NOTHING;`
	_, err = db.Exec(query, req.TelegramID)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "Telegram ID %s сохранён!", req.TelegramID)
}

func handleTelegramID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}

	var req TelegramIDRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil || req.TelegramID == "" {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Вывод Telegram ID в консоль
	fmt.Printf("Получен Telegram ID: %s\n", req.TelegramID)

	// Отправка ответа клиенту
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "Telegram ID %s успешно обработан!", req.TelegramID)

	// --- LOGGING
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Запрос: %s %s", r.Method, r.URL.Path)
		http.NotFound(w, r)
	})

}

func main() {
	initDB()
	defer db.Close()

	// Главная страница (корневой маршрут)
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/index.html")
	})

	// прием статик файлов
	//http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))

	// маршрут для сохранения ID
	http.HandleFunc("/save_telegram_id", saveTelegramID)

	http.Handle("/telegram.js", http.FileServer(http.Dir(".")))

	// Маршрут для вывода Telegram ID в консоль
	http.HandleFunc("/handle_telegram_id", handleTelegramID)

	// localhost
	fmt.Println("Сервер запущен на http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
