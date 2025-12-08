package models

import (
	"time"

	"github.com/google/uuid"
)

type Job struct {
	ID            uuid.UUID `gorm:"type:uuid;primary_key"`
	UserID        uuid.UUID `gorm:"not null"`
	SourceFileURL string    `gorm:"not null"`
	SourceLang    string    `gorm:"not null"`
	TargetLang    string    `gorm:"not null"`
	Duration      int64
	Status        string `gorm:"default:'pending'"`
	Cost          float64
	ResultURL     string
	Error         string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}
