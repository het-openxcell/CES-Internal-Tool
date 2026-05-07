package api

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestGoMigrationFilesCreateCanonicalUsersSchema(t *testing.T) {
	root := filepath.Join("..", "..")
	upSQL := readMigrationFile(t, root, "migrations", "001_initial_schema.up.sql")
	downSQL := readMigrationFile(t, root, "migrations", "001_initial_schema.down.sql")
	baselineSQL := readMigrationFile(t, root, "..", "shared", "schema", "baseline.sql")

	requiredFragments := []string{
		"CREATE EXTENSION IF NOT EXISTS pgcrypto;",
		"CREATE TABLE IF NOT EXISTS users (",
		"id UUID PRIMARY KEY DEFAULT gen_random_uuid(),",
		"username VARCHAR(255) UNIQUE NOT NULL,",
		"password_hash TEXT NOT NULL,",
		"created_at TIMESTAMPTZ NOT NULL DEFAULT now(),",
		"updated_at TIMESTAMPTZ NOT NULL DEFAULT now()",
	}

	for _, fragment := range requiredFragments {
		if !strings.Contains(upSQL, fragment) {
			t.Fatalf("up migration missing %q", fragment)
		}
	}

	if !strings.Contains(downSQL, "DROP TABLE IF EXISTS users;") {
		t.Fatalf("down migration must drop users idempotently")
	}

	epochMigration := readMigrationFile(t, root, "migrations", "002_datetime_epoch.up.sql")
	for _, fragment := range []string{
		"ALTER COLUMN created_at TYPE BIGINT USING EXTRACT(EPOCH FROM created_at)::BIGINT",
		"ALTER COLUMN updated_at TYPE BIGINT USING EXTRACT(EPOCH FROM updated_at)::BIGINT",
	} {
		if !strings.Contains(epochMigration, fragment) {
			t.Fatalf("epoch migration missing %q", fragment)
		}
	}

	for _, fragment := range []string{
		"created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::BIGINT,",
		"updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM now())::BIGINT",
	} {
		if !strings.Contains(baselineSQL, fragment) {
			t.Fatalf("baseline schema missing %q", fragment)
		}
	}
}

func readMigrationFile(t *testing.T, parts ...string) string {
	t.Helper()

	content, err := os.ReadFile(filepath.Join(parts...))
	if err != nil {
		t.Fatalf("read migration file: %v", err)
	}

	return strings.TrimSpace(string(content))
}
