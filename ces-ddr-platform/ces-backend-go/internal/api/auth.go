package api

import (
	"net/http"
	"time"

	authcore "ces-backend-go/internal/auth"

	"github.com/gin-gonic/gin"
)

type AuthHandler struct {
	UserStore        authcore.UserStore
	PasswordVerifier authcore.PasswordVerifier
	JWTManager       authcore.JWTManager
}

type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type LoginResponse struct {
	Token     string `json:"token"`
	ExpiresAt string `json:"expires_at"`
}

func (handler AuthHandler) Register(router *gin.Engine) {
	router.POST("/auth/login", handler.Login)
}

func (handler AuthHandler) Login(context *gin.Context) {
	var request LoginRequest
	if err := context.ShouldBindJSON(&request); err != nil {
		context.JSON(http.StatusUnauthorized, authcore.Unauthorized("Invalid credentials"))
		return
	}

	user, err := handler.UserStore.FindByUsername(context.Request.Context(), request.Username)
	if err != nil {
		context.JSON(http.StatusInternalServerError, authcore.Internal("Authentication service unavailable"))
		return
	}
	passwordHash := handler.PasswordVerifier.DummyHash()
	userID := ""
	if user != nil {
		passwordHash = user.PasswordHash
		userID = user.ID
	}

	if !handler.PasswordVerifier.Verify(context.Request.Context(), request.Password, passwordHash) || userID == "" {
		context.JSON(http.StatusUnauthorized, authcore.Unauthorized("Invalid credentials"))
		return
	}

	token, expiresAt, err := handler.JWTManager.Generate(userID)
	if err != nil {
		context.JSON(http.StatusUnauthorized, authcore.Unauthorized("Invalid credentials"))
		return
	}

	context.JSON(http.StatusOK, LoginResponse{Token: token, ExpiresAt: expiresAt.UTC().Format(time.RFC3339)})
}
