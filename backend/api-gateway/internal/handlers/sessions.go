package handlers

import (
	"encoding/json"
	"fmt"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

func SessionAuthMiddleware(redisClient *redis.Client, cookieName string, ttl int) fiber.Handler {
	return func(c *fiber.Ctx) error {
		sessionID := c.Cookies(cookieName)
		if sessionID == "" {
			return fiber.NewError(fiber.StatusUnauthorized, "No session")
		}

		key := fmt.Sprintf("sess:%s", sessionID)
		data, err := redisClient.Get(c.Context(), key).Result()
		if err != nil {
			return fiber.NewError(fiber.StatusUnauthorized, "Session expired")
		}

		var session map[string]string
		json.Unmarshal([]byte(data), &session)

		userID := uuid.MustParse(session["user_id"])
		c.Locals("userID", userID)

		return c.Next()
	}
}

func ServiceAuthMiddleware(apiKey string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		if c.Get("X-Service-API-Key") != apiKey {
			return fiber.NewError(fiber.StatusUnauthorized, "Invalid API key")
		}
		return c.Next()
	}
}

func GetUserID(c *fiber.Ctx) uuid.UUID {
	return c.Locals("userID").(uuid.UUID)
}

func WorkerAuthMiddleware(internalAPIKey string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		key := c.Get("X-Internal-API-Key")
		if key != internalAPIKey {
			return fiber.NewError(fiber.StatusUnauthorized, "Invalid internal API key")
		}
		return c.Next()
	}
}
