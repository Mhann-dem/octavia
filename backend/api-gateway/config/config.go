package config

import (
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

type Config struct {
	Port              string
	DatabaseURL       string
	RedisURL          string
	RabbitMQURL       string
	RabbitMQQueue     string
	RabbitMQDLQ       string
	SessionSecret     string
	SessionCookieName string
	SessionTTL        int
	ServiceAPIKey     string
	StoragePath       string
	UploadPath        string
	ResultsPath       string
	CostPerMinute     float64
	InternalAPIKey    string
}

func LoadConfig() (*Config, error) {
	godotenv.Load()

	cfg := &Config{
		Port:              getEnv("PORT", "8080"),
		DatabaseURL:       getEnv("DATABASE_URL", "postgres://octavia:octavia@localhost:5432/octavia?sslmode=disable"),
		RedisURL:          getEnv("REDIS_URL", "localhost:6379"),
		RabbitMQURL:       getEnv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
		RabbitMQQueue:     getEnv("RABBITMQ_QUEUE", "jobs.queue"),
		RabbitMQDLQ:       getEnv("RABBITMQ_DLQ", "jobs.dlq"),
		SessionSecret:     getEnv("SESSION_SECRET", "dev_secret"),
		SessionCookieName: getEnv("SESSION_COOKIE_NAME", "octavia_session"),
		SessionTTL:        getIntEnv("SESSION_TTL_SECONDS", 86400),
		ServiceAPIKey:     getEnv("SERVICE_API_KEY", "dev_key"),
		StoragePath:       getEnv("STORAGE_PATH", "./storage"),
		UploadPath:        getEnv("UPLOAD_PATH", "./storage/uploads"),
		ResultsPath:       getEnv("RESULTS_PATH", "./storage/results"),
		CostPerMinute:     getFloatEnv("COST_PER_MINUTE", 0.10),
		InternalAPIKey:    getEnv("INTERNAL_API_KEY", "internal_key_change_in_production"),
	}

	for _, dir := range []string{cfg.StoragePath, cfg.UploadPath, cfg.ResultsPath} {
		os.MkdirAll(dir, 0755)
	}

	return cfg, nil
}

func getEnv(key, def string) string {
	if val, ok := os.LookupEnv(key); ok {
		return val
	}
	return def
}

func getIntEnv(key string, def int) int {
	if val, ok := os.LookupEnv(key); ok {
		if i, err := strconv.Atoi(val); err == nil {
			return i
		}
	}
	return def
}

func getFloatEnv(key string, def float64) float64 {
	if val, ok := os.LookupEnv(key); ok {
		if f, err := strconv.ParseFloat(val, 64); err == nil {
			return f
		}
	}
	return def
}
