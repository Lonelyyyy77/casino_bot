package data

import (
	"database/sql"
	"fmt"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

var DB *sql.DB

// InitializeDB initializes the database connection
func InitializeDB(dbPath string) {
	var err error
	DB, err = sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}

	// Verify connection
	err = DB.Ping()
	if err != nil {
		log.Fatal("Error connecting to the database:", err)
	}
	fmt.Println("Database connected successfully!")
}
