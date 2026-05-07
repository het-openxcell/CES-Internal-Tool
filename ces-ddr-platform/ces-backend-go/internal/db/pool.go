package db

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
)

type PoolFactory struct{}

func (factory PoolFactory) New(ctx context.Context, postgresDSN string) (*pgxpool.Pool, error) {
	return pgxpool.New(ctx, postgresDSN)
}
