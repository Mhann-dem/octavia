package handlers

import (
	"errors"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"github.com/LunarTechAI/octavia/api-gateway/config"
	"github.com/LunarTechAI/octavia/api-gateway/internal/models"
)

type BillingHandler struct {
	db  *gorm.DB
	cfg *config.Config
}

func NewBillingHandler(db *gorm.DB, cfg *config.Config) *BillingHandler {
	return &BillingHandler{db: db, cfg: cfg}
}

type CreditRequest struct {
	UserID        uuid.UUID `json:"user_id"`
	Amount        float64   `json:"amount"`
	TransactionID string    `json:"transaction_id"`
	Source        string    `json:"source"`
}

func (h *BillingHandler) AddCredit(c *fiber.Ctx) error {
	var req CreditRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request")
	}

	var existing models.Transaction
	if h.db.Where("transaction_id = ?", req.TransactionID).First(&existing).Error == nil {
		return c.JSON(fiber.Map{"success": true, "message": "Idempotent"})
	}

	return h.db.Transaction(func(tx *gorm.DB) error {
		var user models.User
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&user, "id = ?", req.UserID).Error; err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				return fiber.NewError(fiber.StatusNotFound, "User not found")
			}
			return fiber.NewError(fiber.StatusInternalServerError, "Query failed")
		}

		prevCredits := user.Credits
		user.Credits += req.Amount
		tx.Save(&user)

		transaction := models.Transaction{
			ID:             uuid.New(),
			UserID:         req.UserID,
			Amount:         req.Amount,
			TransactionID:  req.TransactionID,
			Source:         req.Source,
			PreviousAmount: prevCredits,
			NewAmount:      user.Credits,
			CreatedAt:      time.Now(),
		}
		tx.Create(&transaction)

		return c.JSON(fiber.Map{
			"success": true,
			"credits": user.Credits,
			"amount":  req.Amount,
		})
	})
}
