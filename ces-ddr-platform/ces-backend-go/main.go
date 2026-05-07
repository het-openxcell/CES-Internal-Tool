package main

import (
	"context"
	"fmt"

	"ces-backend-go/internal/api"
	"ces-backend-go/internal/config"
	"ces-backend-go/internal/db"
	"ces-backend-go/internal/db/queries"
)

func main() {
	appConfig := config.Load()
	pool, err := db.PoolFactory{}.New(context.Background(), appConfig.PostgresDSN)
	if err != nil {
		panic(err)
	}
	defer pool.Close()

	router := api.NewRouterWithDependencies(api.RouterDependencies{
		Config:    appConfig,
		UserStore: queries.UserQueries{Pool: pool},
	})

	if err := router.Run(fmt.Sprintf("%s:%s", appConfig.Host, appConfig.Port)); err != nil {
		panic(err)
	}
}
