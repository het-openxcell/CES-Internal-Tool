package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type HealthHandler struct{}

func (handler HealthHandler) Register(router *gin.Engine) {
	router.GET("/health", handler.Read)
}

func (handler HealthHandler) Read(context *gin.Context) {
	context.JSON(http.StatusOK, gin.H{"status": "ok"})
}
