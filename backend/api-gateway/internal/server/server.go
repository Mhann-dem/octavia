package server

import (
	"context"
	"log"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/gofiber/fiber/v2/middleware/requestid"
	"github.com/rabbitmq/amqp091-go"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"

	"github.com/LunarTechAI/octavia/api-gateway/config"
	"github.com/LunarTechAI/octavia/api-gateway/internal/db"
	"github.com/LunarTechAI/octavia/api-gateway/internal/handlers"
)

type Server struct {
	app           *fiber.App
	db            *gorm.DB
	redisClient   *redis.Client
	rabbitConn    *amqp091.Connection
	rabbitChannel *amqp091.Channel
	cfg           *config.Config
}

func NewServer(cfg *config.Config) (*Server, error) {
	dbConn, err := db.InitDB(cfg.DatabaseURL)
	if err != nil {
		return nil, err
	}

	redisClient, err := db.InitRedis(cfg.RedisURL)
	if err != nil {
		return nil, err
	}

	rabbitConn, rabbitChannel, err := db.InitRabbitMQ(cfg.RabbitMQURL, cfg.RabbitMQQueue, cfg.RabbitMQDLQ)
	if err != nil {
		return nil, err
	}

	app := fiber.New(fiber.Config{
		AppName:   "Octavia API Gateway",
		BodyLimit: 1024 * 1024 * 100,
	})

	app.Use(requestid.New())
	app.Use(logger.New())
	app.Use(recover.New())
	app.Use(cors.New(cors.Config{
		AllowHeaders: "X-Service-API-Key, X-Internal-API-Key, Content-Type, Accept, Origin",
	}))

	authHandler := handlers.NewAuthHandler(dbConn, redisClient, cfg)
	jobsHandler := handlers.NewJobsHandler(dbConn, rabbitChannel, cfg)
	billingHandler := handlers.NewBillingHandler(dbConn, cfg)

	registerRoutes(app, authHandler, jobsHandler, billingHandler, redisClient, cfg)

	return &Server{
		app:           app,
		db:            dbConn,
		redisClient:   redisClient,
		rabbitConn:    rabbitConn,
		rabbitChannel: rabbitChannel,
		cfg:           cfg,
	}, nil
}

func registerRoutes(
	app *fiber.App,
	authHandler *handlers.AuthHandler,
	jobsHandler *handlers.JobsHandler,
	billingHandler *handlers.BillingHandler,
	redisClient *redis.Client,
	cfg *config.Config,
) {

	// PUBLIC & CLIENT ROUTES
	api := app.Group("/api/v1")

	auth := api.Group("/auth")
	auth.Post("/signup", authHandler.Signup)
	auth.Post("/login", authHandler.Login)

	protected := api.Use(handlers.SessionAuthMiddleware(redisClient, cfg.SessionCookieName, cfg.SessionTTL))
	protected.Post("/auth/logout", authHandler.Logout)
	protected.Get("/auth/me", authHandler.GetMe)
	protected.Post("/jobs", jobsHandler.CreateJob)
	protected.Get("/jobs/:id", jobsHandler.GetJob)

	service := api.Use(handlers.ServiceAuthMiddleware(cfg.ServiceAPIKey))
	service.Post("/billing/credit", billingHandler.AddCredit)

	// INTERNAL WORKER ROUTES - COMPLETELY SEPARATE
	internal := app.Group("/api/internal")
	internal.Use(handlers.WorkerAuthMiddleware(cfg.InternalAPIKey))
	internal.Patch("/jobs/:id", jobsHandler.UpdateJob)

}

func (s *Server) Start(addr string) error {
	return s.app.Listen(addr)
}

func (s *Server) Shutdown(ctx context.Context) error {
	log.Println("Shutting down server...")
	if s.rabbitChannel != nil {
		s.rabbitChannel.Close()
	}
	if s.rabbitConn != nil {
		s.rabbitConn.Close()
	}
	if s.redisClient != nil {
		s.redisClient.Close()
	}
	return s.app.ShutdownWithContext(ctx)
}
