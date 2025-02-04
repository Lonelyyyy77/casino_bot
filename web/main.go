package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"main.go/data"
	"main.go/server"
)

func main() {
	// Устанавливаем рабочую директорию
	err := os.Chdir("/Users/admin/Documents/work/casino_bot_alisha/casino_bot")
	if err != nil {
		fmt.Printf("Error changing working directory: %v\n", err)
		return
	}

	// Инициализируем базу данных (в data.InitializeDB регистрируется подключение)
	data.InitializeDB("./bot.db")

	// Регистрируем все обработчики через пакет server,
	// который сам регистрирует свои маршруты (например, для слотов, freespin, index и т.д.)
	server.StartServer()

	fmt.Println("Сервер запущен на :8080")
	// Запускаем HTTP-сервер на порту 8080 (все маршруты уже зарегистрированы в server.StartServer())
	log.Fatal(http.ListenAndServe(":8080", nil))
}
