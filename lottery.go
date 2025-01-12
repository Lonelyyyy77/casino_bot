package main

import (
	"fmt"
	"math/rand"
	"net/http"
	"time"
)

func lotteryHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		rand.Seed(time.Now().UnixNano())
		ticket := rand.Intn(1000) + 1
		response := fmt.Sprintf("Ваш билет номер: %d. ", ticket)
		if ticket == 777 {
			response += "Поздравляем, вы выиграли главный приз!"
		} else {
			response += "Увы, не повезло. Попробуйте еще раз."
		}
		w.Write([]byte(response))
	} else {
		http.ServeFile(w, r, "static/lottery.html")
	}
}
