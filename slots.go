package main

import (
	"fmt"
	"math/rand"
	"net/http"
	"time"
)

func slotsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		rand.Seed(time.Now().UnixNano())
		result := rand.Intn(100) + 1
		response := fmt.Sprintf("Результат вращения: %d. ", result)
		if result > 90 {
			response += "Поздравляем, вы выиграли джекпот!"
		} else if result > 50 {
			response += "Вы выиграли небольшой приз."
		} else {
			response += "Увы, вы проиграли."
		}
		w.Write([]byte(response))
	} else {
		http.ServeFile(w, r, "static/slots.html")
	}
}
