package main

import (
	"fmt"

	"ces-backend-go/internal/api"
	"ces-backend-go/internal/config"
)

func main() {
	appConfig := config.Load()
	router := api.NewRouter()

	if err := router.Run(fmt.Sprintf("%s:%s", appConfig.Host, appConfig.Port)); err != nil {
		panic(err)
	}
}
