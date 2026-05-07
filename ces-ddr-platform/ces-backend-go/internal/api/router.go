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
