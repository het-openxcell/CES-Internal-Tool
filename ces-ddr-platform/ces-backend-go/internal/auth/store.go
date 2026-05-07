package auth

import (
	"context"

	"ces-backend-go/internal/models"
)

type UserStore interface {
	FindByUsername(ctx context.Context, username string) (*models.User, error)
}

type EmptyUserStore struct{}

func (store EmptyUserStore) FindByUsername(ctx context.Context, username string) (*models.User, error) {
	_ = ctx
	_ = username
	return nil, nil
}
