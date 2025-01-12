package main

import (
	"fmt"
	"math/rand"
	"net/http"
	"strconv"
	"time"
)

func rouletteHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		bet := r.FormValue("bet")
		rand.Seed(time.Now().UnixNano())
		result := rand.Intn(37) // Roulette numbers from 0 to 36
		response := fmt.Sprintf("Вы поставили на %s. Выпало число %d.", bet, result)
		if bet == strconv.Itoa(result) {
			response += " Поздравляем, вы выиграли!"
		} else {
			response += " Увы, вы проиграли."
		}
		w.Write([]byte(response))
	} else {
		http.ServeFile(w, r, "static/roulette.html")
	}
}
