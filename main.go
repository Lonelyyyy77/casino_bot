package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"

	_ "github.com/mattn/go-sqlite3"
)

// User представляет структуру данных из таблицы user
type User struct {
	ID             int
	LocalIP        string
	Username       string
	TelegramID     int
	Language       string
	Device         string
	Balance        int
	HasAgreedRules int
}

func handler(w http.ResponseWriter, r *http.Request) {
	// Получение данных из базы
	users, err := getAllUsersFromDB()
	if err != nil {
		http.Error(w, "Ошибка при получении данных из базы", http.StatusInternalServerError)
		log.Println("Ошибка:", err)
		return
	}

	// Вывод данных на страницу в текстовом формате
	fmt.Fprintf(w, "Данные пользователей:\n")
	for _, user := range users {
		fmt.Fprintf(w, "ID: %d, Local IP: %s, Username: %s, Telegram ID: %d, Language: %s, Device: %s, Balance: %d, Agreed Rules: %d\n",
			user.ID, user.LocalIP, user.Username, user.TelegramID, user.Language, user.Device, user.Balance, user.HasAgreedRules)
	}
}

func main() {
	// Установка обработчика для корневого пути
	http.HandleFunc("/", handler)

	// Запуск сервера
	fmt.Println("Сервер запущен на http://localhost:8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal("Ошибка запуска сервера:", err)
	}
}

// getAllUsersFromDB получает все данные из таблицы user
func getAllUsersFromDB() ([]User, error) {
	db, err := sql.Open("sqlite3", "main2.db")
	if err != nil {
		return nil, fmt.Errorf("ошибка подключения к базе данных: %w", err)
	}
	defer db.Close()

	// SQL-запрос для получения всех данных
	query := `
	SELECT id, local_ip, username, telegram_id, language_layout, device, balance, has_agreed_rules
	FROM user;
	`

	rows, err := db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer rows.Close()

	// Парсинг данных в структуру User
	var users []User
	for rows.Next() {
		var user User
		err := rows.Scan(&user.ID, &user.LocalIP, &user.Username, &user.TelegramID, &user.Language, &user.Device, &user.Balance, &user.HasAgreedRules)
		if err != nil {
			return nil, fmt.Errorf("ошибка при чтении строки: %w", err)
		}
		users = append(users, user)
	}

	return users, nil
}
