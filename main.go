package main

import (
	"log"
	"net/http"
)

func main() {
	// File server to serve static files
	fs := http.FileServer(http.Dir("static"))

	// Route to serve index.html
	http.Handle("/", fs)

	// Start the server
	log.Println("Starting server on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal(err)
	}
}
