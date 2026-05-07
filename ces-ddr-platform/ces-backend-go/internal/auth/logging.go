package auth

import (
	"encoding/json"
	"io"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type RequestLogger struct {
	Service          string
	Writer           io.Writer
	JWTSecret        string
	PostgresPassword string
}

func (logger RequestLogger) Middleware() gin.HandlerFunc {
	return func(context *gin.Context) {
		requestID := uuid.NewString()
		context.Set("request_id", requestID)
		context.Next()
		logger.write(map[string]any{
			"timestamp":  time.Now().UTC().Unix(),
			"level":      "info",
			"service":    logger.Service,
			"request_id": requestID,
			"message":    logger.sanitize(context.Request.Method + " " + context.Request.URL.Path),
		})
	}
}

func (logger RequestLogger) write(entry map[string]any) {
	for key, value := range entry {
		if text, ok := value.(string); ok {
			entry[key] = logger.sanitize(text)
		}
	}
	body, err := json.Marshal(entry)
	if err != nil || logger.Writer == nil {
		return
	}
	_, _ = logger.Writer.Write(append(body, '\n'))
}

func (logger RequestLogger) sanitize(value string) string {
	replacer := strings.NewReplacer(
		"Authorization", "[redacted]",
		"JWT_SECRET", "[redacted]",
		"POSTGRES_PASSWORD", "[redacted]",
	)
	value = replacer.Replace(value)
	for _, secret := range []string{logger.JWTSecret, logger.PostgresPassword} {
		if secret != "" {
			value = strings.ReplaceAll(value, secret, "[redacted]")
		}
	}
	return value
}
