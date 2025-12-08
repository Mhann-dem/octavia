package handlers

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"time"

	"github.com/LunarTechAI/octavia/api-gateway/config"
	"github.com/LunarTechAI/octavia/api-gateway/internal/models"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

type AuthHandler struct {
	db        *gorm.DB
	redis     *redis.Client
	cfg       *config.Config
	validator *validator.Validate
}

func NewAuthHandler(db *gorm.DB, redis *redis.Client, cfg *config.Config) *AuthHandler {
	return &AuthHandler{
		db:        db,
		redis:     redis,
		cfg:       cfg,
		validator: validator.New(),
	}
}

type SignupRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required,min=8"`
	Name     string `json:"name" validate:"required"`
}

type LoginRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required"`
}

func (h *AuthHandler) Signup(c *fiber.Ctx) error {
	var req SignupRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	// Validate request
	if err := h.validator.Struct(req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, fmt.Sprintf("Validation error: %v", err))
	}

	// Check if user exists
	var existing models.User
	if h.db.Where("email = ?", req.Email).First(&existing).Error == nil {
		return fiber.NewError(fiber.StatusBadRequest, "User already exists")
	}

	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)

	user := models.User{
		ID:        uuid.New(),
		Email:     req.Email,
		Password:  string(hashedPassword),
		Name:      req.Name,
		Credits:   0,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	if err := h.db.Create(&user).Error; err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to create user")
	}

	sessionID := generateSessionID()
	h.setSession(c, sessionID, user.ID)
	h.setSessionCookie(c, sessionID)

	return c.Status(fiber.StatusCreated).JSON(fiber.Map{
		"id":    user.ID.String(),
		"email": user.Email,
		"name":  user.Name,
	})
}

func (h *AuthHandler) Login(c *fiber.Ctx) error {
	var req LoginRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	// Validate request
	if err := h.validator.Struct(req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, fmt.Sprintf("Validation error: %v", err))
	}

	var user models.User
	if err := h.db.Where("email = ?", req.Email).First(&user).Error; err != nil {
		return fiber.NewError(fiber.StatusUnauthorized, "Invalid credentials")
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(req.Password)); err != nil {
		return fiber.NewError(fiber.StatusUnauthorized, "Invalid credentials")
	}

	sessionID := generateSessionID()
	h.setSession(c, sessionID, user.ID)
	h.setSessionCookie(c, sessionID)

	return c.JSON(fiber.Map{
		"id":         user.ID.String(),
		"email":      user.Email,
		"name":       user.Name,
		"credits":    user.Credits,
		"session_id": sessionID,
	})
}

func (h *AuthHandler) Logout(c *fiber.Ctx) error {
	sessionID := c.Cookies(h.cfg.SessionCookieName)
	if sessionID != "" {
		key := fmt.Sprintf("sess:%s", sessionID)
		h.redis.Del(c.Context(), key)
	}
	c.ClearCookie(h.cfg.SessionCookieName)
	return c.JSON(fiber.Map{"success": true})
}

func (h *AuthHandler) setSession(c *fiber.Ctx, sessionID string, userID uuid.UUID) {
	sessionData := map[string]interface{}{
		"user_id":    userID.String(),
		"created_at": time.Now().Format(time.RFC3339),
	}
	data, _ := json.Marshal(sessionData)
	key := fmt.Sprintf("sess:%s", sessionID)
	h.redis.Set(c.Context(), key, data, time.Duration(h.cfg.SessionTTL)*time.Second)
}

func (h *AuthHandler) setSessionCookie(c *fiber.Ctx, sessionID string) {
	c.Cookie(&fiber.Cookie{
		Name:     h.cfg.SessionCookieName,
		Value:    sessionID,
		Expires:  time.Now().Add(time.Duration(h.cfg.SessionTTL) * time.Second),
		HTTPOnly: true,
		Path:     "/",
	})
}

func generateSessionID() string {
	b := make([]byte, 32)
	rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}

func (h *AuthHandler) GetMe(c *fiber.Ctx) error {
	sessionID := c.Cookies(h.cfg.SessionCookieName)
	if sessionID == "" {
		return fiber.NewError(fiber.StatusUnauthorized, "No session cookie found")
	}

	key := fmt.Sprintf("sess:%s", sessionID)
	data, err := h.redis.Get(c.Context(), key).Result()
	if err != nil {
		return fiber.NewError(fiber.StatusUnauthorized, "Invalid session")
	}

	var sessionData map[string]interface{}
	if err := json.Unmarshal([]byte(data), &sessionData); err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to parse session data")
	}

	userIDStr, ok := sessionData["user_id"].(string)
	if !ok {
		return fiber.NewError(fiber.StatusInternalServerError, "Invalid session data")
	}

	var user models.User
	if err := h.db.Where("id = ?", userIDStr).First(&user).Error; err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "User not found")
	}

	return c.JSON(fiber.Map{
		"id":      user.ID.String(),
		"email":   user.Email,
		"name":    user.Name,
		"credits": user.Credits,
	})
}
