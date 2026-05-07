package api

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthReturnsOkStatus(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-jwt-secret")
	router := NewRouter()
	response := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/health", nil)

	router.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, response.Code)
	}

	expected := `{"status":"ok"}`
	if response.Body.String() != expected {
		t.Fatalf("expected body %s, got %s", expected, response.Body.String())
	}
}
