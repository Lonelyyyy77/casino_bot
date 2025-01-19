package main

import (
	"fmt"
	"os"

	"main.go/data"

	"main.go/server"
)

func main() {
	// Установить рабочую директорию
	err := os.Chdir("/Users/admin/Documents/work/casino_bot_alisha/casino_bot")
	if err != nil {
		fmt.Printf("Error changing working directory: %v\n", err)
		return
	}

	fmt.Println("- - - Code in main is active.")
	data.InitializeDB("./bot.db") // Используйте относительный путь
	server.StartServer()
}
