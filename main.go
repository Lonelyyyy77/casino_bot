package main

import (
	"fmt"

	"main.go/data"
	"main.go/server"
)

func main() {
	fmt.Println("- - - - Code in main is active.")
	data.InitializeDB("./bot.db")
	server.StartServer()
}
