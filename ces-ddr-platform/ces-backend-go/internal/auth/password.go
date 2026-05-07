package auth

import (
	"context"

	"golang.org/x/crypto/bcrypt"
)

const dummyPasswordHash = "$2a$10$7EqJtq98hPqEX7fNZaFWoOhiZCQGNuCIlnLzKeE/d1qFJKZ0f4uTe"

type PasswordVerifier struct{}

func (verifier PasswordVerifier) Verify(ctx context.Context, password string, passwordHash string) bool {
	_ = ctx
	return bcrypt.CompareHashAndPassword([]byte(passwordHash), []byte(password)) == nil
}

func (verifier PasswordVerifier) Hash(password string) (string, error) {
	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	return string(hash), err
}

func (verifier PasswordVerifier) DummyHash() string {
	return dummyPasswordHash
}
