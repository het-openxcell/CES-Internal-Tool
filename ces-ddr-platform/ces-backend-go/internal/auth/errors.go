package auth

import "github.com/gin-gonic/gin"

type ErrorResponse struct {
	Error   string         `json:"error"`
	Code    string         `json:"code"`
	Details map[string]any `json:"details"`
}

func Unauthorized(message string) ErrorResponse {
	return ErrorResponse{Error: message, Code: "UNAUTHORIZED", Details: gin.H{}}
}

func Internal(message string) ErrorResponse {
	return ErrorResponse{Error: message, Code: "INTERNAL_ERROR", Details: gin.H{}}
}
