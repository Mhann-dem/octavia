package models

import (
	"time"

	"github.com/google/uuid"
)

type Transaction struct {
	ID             uuid.UUID `gorm:"type:uuid;primary_key"`
	UserID         uuid.UUID `gorm:"not null"`
	Amount         float64   `gorm:"not null"`
	TransactionID  string    `gorm:"unique;not null"`
	Source         string
	PreviousAmount float64
	NewAmount      float64
	CreatedAt      time.Time
}
