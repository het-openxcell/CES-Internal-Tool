package queries

import (
	"context"

	"ces-backend-go/internal/models"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type UserQueries struct {
	Pool *pgxpool.Pool
}

func (queries UserQueries) FindByUsername(ctx context.Context, username string) (*models.User, error) {
	row := queries.Pool.QueryRow(ctx, `
		SELECT id::text, username, password_hash, created_at, updated_at
		FROM users
		WHERE username = $1
	`, username)

	user := &models.User{}
	if err := row.Scan(&user.ID, &user.Username, &user.PasswordHash, &user.CreatedAt, &user.UpdatedAt); err != nil {
		if err == pgx.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	return user, nil
}
