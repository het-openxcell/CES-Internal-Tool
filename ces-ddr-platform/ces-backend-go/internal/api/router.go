package api

import "github.com/gin-gonic/gin"

func NewRouter() *gin.Engine {
	gin.SetMode(gin.ReleaseMode)

	router := gin.New()
	HealthHandler{}.Register(router)

	return router
}
