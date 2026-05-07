package api

import (
	"io"
	"net/http"
	"os"
	"time"

	authcore "ces-backend-go/internal/auth"
	"ces-backend-go/internal/config"

	"github.com/gin-gonic/gin"
)

type RouterDependencies struct {
	Config    config.Config
	UserStore authcore.UserStore
	LogWriter io.Writer
}

func NewRouter() *gin.Engine {
	return NewRouterWithDependencies(RouterDependencies{Config: config.Load()})
}

func NewRouterWithDependencies(dependencies RouterDependencies) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)

	router := gin.New()
	if dependencies.LogWriter == nil {
		dependencies.LogWriter = os.Stdout
	}
	if dependencies.UserStore == nil {
		dependencies.UserStore = authcore.EmptyUserStore{}
	}

	jwtManager := authcore.NewJWTManager(dependencies.Config.JWTSecret, 8*time.Hour)
	router.Use(CORSMiddleware{AllowedOrigin: dependencies.Config.CORSAllowedOrigin}.Middleware())
	router.Use(authcore.RequestLogger{
		Service:          "ces-backend-go",
		Writer:           dependencies.LogWriter,
		JWTSecret:        dependencies.Config.JWTSecret,
		PostgresPassword: dependencies.Config.PostgresPassword,
	}.Middleware())
	router.Use(authcore.JWTMiddleware{Manager: jwtManager, PublicPaths: map[string]map[string]bool{
		http.MethodGet:  {"/health": true},
		http.MethodPost: {"/auth/login": true},
	}}.Middleware())

	HealthHandler{}.Register(router)
	AuthHandler{
		UserStore:        dependencies.UserStore,
		PasswordVerifier: authcore.PasswordVerifier{},
		JWTManager:       jwtManager,
	}.Register(router)
	return router
}

type CORSMiddleware struct {
	AllowedOrigin string
}

func (middleware CORSMiddleware) Middleware() gin.HandlerFunc {
	return func(context *gin.Context) {
		origin := context.GetHeader("Origin")
		if origin == middleware.AllowedOrigin {
			context.Header("Access-Control-Allow-Origin", origin)
			context.Header("Vary", "Origin")
			context.Header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
			context.Header("Access-Control-Allow-Headers", "Authorization,Content-Type")
		}
		if context.Request.Method == http.MethodOptions {
			context.AbortWithStatus(http.StatusNoContent)
			return
		}
		context.Next()
	}
}
