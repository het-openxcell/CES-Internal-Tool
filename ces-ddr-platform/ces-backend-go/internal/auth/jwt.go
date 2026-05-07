package auth

import (
	"errors"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

const insecurePlaceholderJWTSecret = "placeholder-jwt-secret"

type Claims struct {
	UserID string `json:"user_id"`
	jwt.RegisteredClaims
}

type JWTManager struct {
	secret   string
	lifetime time.Duration
}

func NewJWTManager(secret string, lifetime time.Duration) JWTManager {
	if strings.TrimSpace(secret) == "" || secret == insecurePlaceholderJWTSecret {
		panic("JWT secret is required")
	}
	return JWTManager{secret: secret, lifetime: lifetime}
}

func (manager JWTManager) Generate(userID string) (string, int64, error) {
	expiresAt := time.Now().UTC().Add(manager.lifetime)
	claims := Claims{
		UserID: userID,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expiresAt),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString([]byte(manager.secret))
	return signed, expiresAt.Unix(), err
}

func (manager JWTManager) Validate(tokenValue string) (*Claims, error) {
	if manager.secret == "" {
		return nil, errors.New("jwt secret is required")
	}

	claims := &Claims{}
	token, err := jwt.ParseWithClaims(tokenValue, claims, func(token *jwt.Token) (any, error) {
		if token.Method != jwt.SigningMethodHS256 {
			return nil, errors.New("unexpected signing method")
		}
		return []byte(manager.secret), nil
	})
	if err != nil || !token.Valid || claims.UserID == "" || claims.ExpiresAt == nil {
		return nil, errors.New("invalid token")
	}
	return claims, nil
}
