package auth

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

type JWTMiddleware struct {
	Manager     JWTManager
	PublicPaths map[string]map[string]bool
}

func (middleware JWTMiddleware) Middleware() gin.HandlerFunc {
	return func(context *gin.Context) {
		if middleware.isPublic(context.Request.Method, context.Request.URL.Path) {
			context.Next()
			return
		}

		authorization := context.GetHeader("Authorization")
		if !strings.HasPrefix(authorization, "Bearer ") {
			context.AbortWithStatusJSON(http.StatusUnauthorized, Unauthorized("Authentication required"))
			return
		}

		token := strings.TrimSpace(strings.TrimPrefix(authorization, "Bearer "))
		claims, err := middleware.Manager.Validate(token)
		if err != nil {
			context.AbortWithStatusJSON(http.StatusUnauthorized, Unauthorized("Authentication required"))
			return
		}

		context.Set("user_id", claims.UserID)
		context.Next()
	}
}

func (middleware JWTMiddleware) isPublic(method string, path string) bool {
	paths, ok := middleware.PublicPaths[method]
	return ok && paths[path]
}
