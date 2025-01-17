// main.go
package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"net/http"

	_ "github.com/mattn/go-sqlite3"
)

type User struct {
	TelegramID string
	Balance    float64
}

func getUserBalance(db *sql.DB, telegramID string) (*User, error) {
	var user User
	err := db.QueryRow("SELECT telegram_id, balance FROM user WHERE telegram_id = ?", telegramID).Scan(&user.TelegramID, &user.Balance)
	if err == sql.ErrNoRows {
		return nil, fmt.Errorf("user with telegram_id %s not found", telegramID)
	} else if err != nil {
		return nil, err
	}
	return &user, nil
}

func handler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		telegramID := r.URL.Query().Get("telegram_id")
		if telegramID == "" {
			http.Error(w, "Missing telegram_id parameter", http.StatusBadRequest)
			return
		}

		user, err := getUserBalance(db, telegramID)
		if err != nil {
			http.Error(w, fmt.Sprintf("Error retrieving user: %v", err), http.StatusInternalServerError)
			return
		}

		tmpl, err := template.ParseFiles("static/index.html")
		if err != nil {
			http.Error(w, fmt.Sprintf("Error loading template: %v", err), http.StatusInternalServerError)
			return
		}

		err = tmpl.Execute(w, user)
		if err != nil {
			http.Error(w, fmt.Sprintf("Error rendering template: %v", err), http.StatusInternalServerError)
		}
	}
}

func main() {
	db, err := sql.Open("sqlite3", "main2.db")
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	http.HandleFunc("/", handler(db))
	log.Println("Server is running on http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
