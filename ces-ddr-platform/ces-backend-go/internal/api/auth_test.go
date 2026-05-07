package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	authcore "ces-backend-go/internal/auth"
	"ces-backend-go/internal/config"
	"ces-backend-go/internal/models"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
)

type fakeUserStore struct {
	user *models.User
	err  error
}

func (store fakeUserStore) FindByUsername(ctx context.Context, username string) (*models.User, error) {
	return store.user, store.err
}

func TestLoginReturnsSignedJWT(t *testing.T) {
	hash, err := authcore.PasswordVerifier{}.Hash("correct-password")
	if err != nil {
		t.Fatal(err)
	}

	router := NewRouterWithDependencies(RouterDependencies{
		Config: config.Config{JWTSecret: "test-jwt-secret"},
		UserStore: fakeUserStore{user: &models.User{
			ID:           "11111111-1111-1111-1111-111111111111",
			Username:     "ces.staff",
			PasswordHash: hash,
		}},
		LogWriter: bytes.NewBuffer(nil),
	})
	response := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/auth/login", strings.NewReader(`{"username":"ces.staff","password":"correct-password"}`))
	request.Header.Set("Content-Type", "application/json")

	router.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d with %s", http.StatusOK, response.Code, response.Body.String())
	}

	var body struct {
		Token     string `json:"token"`
		ExpiresAt int64  `json:"expires_at"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Token == "" || body.ExpiresAt == 0 {
		t.Fatalf("expected token and expires_at, got %+v", body)
	}

	claims, err := authcore.NewJWTManager("test-jwt-secret", 8*time.Hour).Validate(body.Token)
	if err != nil {
		t.Fatal(err)
	}
	if claims.UserID != "11111111-1111-1111-1111-111111111111" {
		t.Fatalf("expected user_id claim, got %s", claims.UserID)
	}
	if body.ExpiresAt < time.Now().UTC().Add(7*time.Hour+59*time.Minute).Unix() || body.ExpiresAt > time.Now().UTC().Add(8*time.Hour+time.Minute).Unix() {
		t.Fatalf("expected epoch expires_at roughly 8 hours ahead, got %d", body.ExpiresAt)
	}
}

func TestCORSPreflightAllowsConfiguredFrontendOrigin(t *testing.T) {
	router := NewRouterWithDependencies(RouterDependencies{
		Config:    config.Config{JWTSecret: "test-jwt-secret", CORSAllowedOrigin: "http://localhost:5173"},
		UserStore: fakeUserStore{},
		LogWriter: bytes.NewBuffer(nil),
	})
	response := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodOptions, "/auth/login", nil)
	request.Header.Set("Origin", "http://localhost:5173")
	request.Header.Set("Access-Control-Request-Method", "POST")
	request.Header.Set("Access-Control-Request-Headers", "content-type")

	router.ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("expected preflight status %d, got %d", http.StatusNoContent, response.Code)
	}
	if response.Header().Get("Access-Control-Allow-Origin") != "http://localhost:5173" {
		t.Fatalf("expected CORS origin header, got %s", response.Header().Get("Access-Control-Allow-Origin"))
	}
	if !strings.Contains(response.Header().Get("Access-Control-Allow-Headers"), "Content-Type") {
		t.Fatalf("expected content-type CORS header, got %s", response.Header().Get("Access-Control-Allow-Headers"))
	}
}

func TestLoginWrongUsernameAndPasswordReturnSameUnauthorizedBody(t *testing.T) {
	hash, err := authcore.PasswordVerifier{}.Hash("correct-password")
	if err != nil {
		t.Fatal(err)
	}

	router := NewRouterWithDependencies(RouterDependencies{
		Config: config.Config{JWTSecret: "test-jwt-secret"},
		UserStore: fakeUserStore{user: &models.User{
			ID:           "11111111-1111-1111-1111-111111111111",
			Username:     "ces.staff",
			PasswordHash: hash,
		}},
		LogWriter: bytes.NewBuffer(nil),
	})

	wrongPassword := httptest.NewRecorder()
	wrongPasswordRequest := httptest.NewRequest(http.MethodPost, "/auth/login", strings.NewReader(`{"username":"ces.staff","password":"wrong-password"}`))
	wrongPasswordRequest.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(wrongPassword, wrongPasswordRequest)

	missingUserRouter := NewRouterWithDependencies(RouterDependencies{
		Config:    config.Config{JWTSecret: "test-jwt-secret"},
		UserStore: fakeUserStore{},
		LogWriter: bytes.NewBuffer(nil),
	})
	missingUser := httptest.NewRecorder()
	missingUserRequest := httptest.NewRequest(http.MethodPost, "/auth/login", strings.NewReader(`{"username":"missing","password":"wrong-password"}`))
	missingUserRequest.Header.Set("Content-Type", "application/json")
	missingUserRouter.ServeHTTP(missingUser, missingUserRequest)

	if wrongPassword.Code != http.StatusUnauthorized || missingUser.Code != http.StatusUnauthorized {
		t.Fatalf("expected unauthorized statuses, got %d and %d", wrongPassword.Code, missingUser.Code)
	}
	assertErrorBody(t, wrongPassword.Body.Bytes(), "Invalid credentials")
	assertErrorBody(t, missingUser.Body.Bytes(), "Invalid credentials")
	if wrongPassword.Body.String() != missingUser.Body.String() {
		t.Fatalf("expected same body, got %s and %s", wrongPassword.Body.String(), missingUser.Body.String())
	}
}

func TestJWTMiddlewareRejectsMissingMalformedBadSignatureAndExpiredTokens(t *testing.T) {
	router := NewRouterWithDependencies(RouterDependencies{
		Config:    config.Config{JWTSecret: "test-jwt-secret"},
		UserStore: fakeUserStore{},
		LogWriter: bytes.NewBuffer(nil),
	})
	router.GET("/protected-test", func(context *gin.Context) {
		context.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	cases := []struct {
		name   string
		header string
	}{
		{name: "missing"},
		{name: "malformed", header: "Bearer no"},
		{name: "bad signature", header: "Bearer " + mustToken(t, "other-secret", time.Hour)},
		{name: "expired", header: "Bearer " + mustToken(t, "test-jwt-secret", -time.Hour)},
		{name: "missing exp", header: "Bearer " + mustTokenWithoutExp(t, "test-jwt-secret")},
	}

	for _, current := range cases {
		t.Run(current.name, func(t *testing.T) {
			response := httptest.NewRecorder()
			request := httptest.NewRequest(http.MethodGet, "/protected-test", nil)
			if current.header != "" {
				request.Header.Set("Authorization", current.header)
			}

			router.ServeHTTP(response, request)

			if response.Code != http.StatusUnauthorized {
				t.Fatalf("expected unauthorized, got %d %s", response.Code, response.Body.String())
			}
			assertErrorBody(t, response.Body.Bytes(), "Authentication required")
		})
	}
}

func TestLoginReturnsInfrastructureErrorWhenUserStoreFails(t *testing.T) {
	router := NewRouterWithDependencies(RouterDependencies{
		Config:    config.Config{JWTSecret: "test-jwt-secret"},
		UserStore: fakeUserStore{err: errors.New("database unavailable")},
		LogWriter: bytes.NewBuffer(nil),
	})
	response := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/auth/login", strings.NewReader(`{"username":"ces.staff","password":"correct-password"}`))
	request.Header.Set("Content-Type", "application/json")

	router.ServeHTTP(response, request)

	if response.Code != http.StatusInternalServerError {
		t.Fatalf("expected status %d, got %d with %s", http.StatusInternalServerError, response.Code, response.Body.String())
	}
	var parsed map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &parsed); err != nil {
		t.Fatal(err)
	}
	if parsed["code"] != "INTERNAL_ERROR" {
		t.Fatalf("expected internal error body, got %v", parsed)
	}
}

func TestRequestLoggingIncludesRequestIDAndExcludesSecrets(t *testing.T) {
	logs := bytes.NewBuffer(nil)
	router := NewRouterWithDependencies(RouterDependencies{
		Config: config.Config{
			JWTSecret:        "super-secret-value",
			PostgresPassword: "postgres-secret-value",
		},
		UserStore: fakeUserStore{},
		LogWriter: logs,
	})
	request := httptest.NewRequest(http.MethodGet, "/health", nil)
	request.Header.Set("Authorization", "Bearer should-not-log")
	request.URL.Path = "/health/super-secret-value/postgres-secret-value/JWT_SECRET/POSTGRES_PASSWORD/Authorization"
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	line := logs.String()
	for _, required := range []string{"timestamp", "level", "service", "request_id", "message"} {
		if !strings.Contains(line, required) {
			t.Fatalf("expected log to contain %s, got %s", required, line)
		}
	}
	for _, secret := range []string{"Authorization", "should-not-log", "super-secret-value", "postgres-secret-value", "JWT_SECRET", "POSTGRES_PASSWORD"} {
		if strings.Contains(line, secret) {
			t.Fatalf("log leaked %s in %s", secret, line)
		}
	}
}

func TestJWTManagerRejectsMissingPlaceholderAndNoExpTokens(t *testing.T) {
	for _, secret := range []string{"", "placeholder-jwt-secret"} {
		t.Run(secret, func(t *testing.T) {
			defer func() {
				if recover() == nil {
					t.Fatal("expected panic")
				}
			}()
			_ = authcore.NewJWTManager(secret, time.Hour)
		})
	}

	_, err := authcore.NewJWTManager("test-jwt-secret", time.Hour).Validate(mustTokenWithoutExp(t, "test-jwt-secret"))
	if err == nil {
		t.Fatal("expected missing exp token to fail")
	}
}

func TestSharedJWTFixtureValidatesWithGoManager(t *testing.T) {
	fixture := sharedUserFixture(t)
	claims, err := authcore.NewJWTManager(fixture["jwt_secret"], 8*time.Hour).Validate(fixture["valid_token"])
	if err != nil {
		t.Fatal(err)
	}
	if claims.UserID != fixture["id"] {
		t.Fatalf("expected fixture user id, got %s", claims.UserID)
	}
	if !(authcore.PasswordVerifier{}).Verify(context.Background(), fixture["password"], fixture["password_hash"]) {
		t.Fatal("expected shared password hash to verify")
	}
}

func mustToken(t *testing.T, secret string, lifetime time.Duration) string {
	t.Helper()
	token, _, err := authcore.NewJWTManager(secret, lifetime).Generate("11111111-1111-1111-1111-111111111111")
	if err != nil {
		t.Fatal(err)
	}
	return token
}

func mustTokenWithoutExp(t *testing.T, secret string) string {
	t.Helper()
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{"user_id": "11111111-1111-1111-1111-111111111111"})
	signed, err := token.SignedString([]byte(secret))
	if err != nil {
		t.Fatal(err)
	}
	return signed
}

func sharedUserFixture(t *testing.T) map[string]string {
	t.Helper()
	path := filepath.Join("..", "..", "..", "shared", "test-fixtures", "auth", "shared-user.json")
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var fixture map[string]string
	if err := json.Unmarshal(body, &fixture); err != nil {
		t.Fatal(err)
	}
	return fixture
}

func assertErrorBody(t *testing.T, body []byte, message string) {
	t.Helper()
	var parsed map[string]any
	if err := json.Unmarshal(body, &parsed); err != nil {
		t.Fatal(err)
	}
	if parsed["error"] != message || parsed["code"] != "UNAUTHORIZED" {
		t.Fatalf("unexpected error body %v", parsed)
	}
	if details, ok := parsed["details"].(map[string]any); !ok || len(details) != 0 {
		t.Fatalf("unexpected details %v", parsed["details"])
	}
}
