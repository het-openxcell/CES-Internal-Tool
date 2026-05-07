package models

type User struct {
	ID           string
	Username     string
	PasswordHash string
	CreatedAt    int64
	UpdatedAt    int64
}
