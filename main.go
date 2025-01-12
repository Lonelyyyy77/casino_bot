package main

import (
	"fmt"
	"net/http"
)

func main() {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/index.html")
	})

	http.HandleFunc("/roulette", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/roulette.html")
	})

	http.HandleFunc("/slots", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/slots.html")
	})

	http.HandleFunc("/lottery", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/lottery.html")
	})

	fmt.Println("Server starting on port 8080...")
	http.ListenAndServe(":8080", nil)
}
