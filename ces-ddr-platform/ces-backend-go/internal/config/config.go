package config

import (
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	AppName           string
	Environment       string
	Host              string
	Port              string
	PostgresDSN       string
	PostgresPassword  string
	QdrantHost        string
	QdrantPort        string
	JWTSecret         string
	CORSAllowedOrigin string
}

func Load() Config {
	_ = godotenv.Load(".env", "../.env")

	return Config{
		AppName:           value("APP_NAME", "CES DDR Go Backend"),
		Environment:       value("APP_ENV", "local"),
		Host:              value("GO_BACKEND_HOST", "0.0.0.0"),
		Port:              value("GO_BACKEND_PORT", "8000"),
		PostgresDSN:       value("POSTGRES_DSN", "postgresql://ces:change-me-local-only@localhost:5432/ces_ddr"),
		PostgresPassword:  value("POSTGRES_PASSWORD", ""),
		QdrantHost:        value("QDRANT_HOST", "localhost"),
		QdrantPort:        value("QDRANT_PORT", "6333"),
		JWTSecret:         value("JWT_SECRET", ""),
		CORSAllowedOrigin: value("CORS_ALLOWED_ORIGIN", "http://localhost:5173"),
	}
}

func value(key string, fallback string) string {
	current := os.Getenv(key)
	if current == "" {
		return fallback
	}
	return current
}
