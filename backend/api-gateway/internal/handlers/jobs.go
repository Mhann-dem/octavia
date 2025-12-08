package handlers

import (
	"encoding/json"
	"errors"
	"mime/multipart"
	"strconv"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"github.com/rabbitmq/amqp091-go"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"github.com/LunarTechAI/octavia/api-gateway/config"
	"github.com/LunarTechAI/octavia/api-gateway/internal/models"
)

type JobsHandler struct {
	db            *gorm.DB
	rabbitChannel *amqp091.Channel
	cfg           *config.Config
}

func NewJobsHandler(db *gorm.DB, rabbitChannel *amqp091.Channel, cfg *config.Config) *JobsHandler {
	return &JobsHandler{db: db, rabbitChannel: rabbitChannel, cfg: cfg}
}

type JobRequest struct {
	SourceFileURL string                `form:"source_file_url"`
	File          *multipart.FileHeader `form:"file"`
	SourceLang    string                `form:"source_lang"`
	TargetLang    string                `form:"target_lang"`
	Duration      int64                 `form:"duration"`
}

type UpdateJobRequest struct {
	Status    string `json:"status"`
	ResultURL string `json:"result_url"`
	Error     string `json:"error"`
}

func (h *JobsHandler) CreateJob(c *fiber.Ctx) error {
	var req JobRequest
	if c.FormValue("source_lang") == "" || c.FormValue("target_lang") == "" {
		return fiber.NewError(fiber.StatusBadRequest, "source_lang and target_lang are required")
	}

	req.SourceLang = c.FormValue("source_lang")
	req.TargetLang = c.FormValue("target_lang")
	req.SourceFileURL = c.FormValue("source_file_url")
	durationStr := c.FormValue("duration")
	duration, err := strconv.ParseInt(durationStr, 10, 64)
	if err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid duration")
	}
	req.Duration = duration
	req.Duration = duration

	file, err := c.FormFile("file")
	if err != nil && err != fiber.ErrUnprocessableEntity {
		return fiber.NewError(fiber.StatusBadRequest, "Error parsing file")
	}

	if file == nil && req.SourceFileURL == "" {
		return fiber.NewError(fiber.StatusBadRequest, "Either file or source_file_url is required")
	}

	sourceFileURL := req.SourceFileURL
	if file != nil {
		sourceFileURL = file.Filename
	}

	userID := GetUserID(c)

	cost := float64(req.Duration) * h.cfg.CostPerMinute / 60.0

	var user models.User
	if err := h.db.First(&user, "id = ?", userID).Error; err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "User not found")
	}

	if user.Credits < cost {
		return fiber.NewError(fiber.StatusBadRequest, "Insufficient credits")
	}

	jobID := uuid.New()
	job := models.Job{
		ID:            jobID,
		UserID:        userID,
		SourceFileURL: sourceFileURL,
		SourceLang:    req.SourceLang,
		TargetLang:    req.TargetLang,
		Duration:      req.Duration,
		Status:        "pending",
		Cost:          cost,
		CreatedAt:     time.Now(),
		UpdatedAt:     time.Now(),
	}

	if err := h.db.Create(&job).Error; err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Job creation failed")
	}

	h.db.Transaction(func(tx *gorm.DB) error {
		tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&user, "id = ?", userID)
		if user.Credits < cost {
			return errors.New("insufficient credits")
		}
		user.Credits -= cost
		tx.Save(&user)
		return nil
	})

	jobMsg := map[string]interface{}{
		"job_id":      jobID.String(),
		"source_file": sourceFileURL,
		"source_lang": req.SourceLang,
		"target_lang": req.TargetLang,
		"duration":    req.Duration,
		"user_id":     userID.String(),
	}

	msgBody, _ := json.Marshal(jobMsg)
	h.rabbitChannel.Publish("", h.cfg.RabbitMQQueue, false, false, amqp091.Publishing{
		ContentType: "application/json",
		Body:        msgBody,
		MessageId:   jobID.String(),
		Timestamp:   time.Now(),
	})

	return c.Status(fiber.StatusCreated).JSON(fiber.Map{
		"id":     jobID.String(),
		"status": "pending",
	})
}

func (h *JobsHandler) UpdateJob(c *fiber.Ctx) error {
	jobID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid job ID")
	}

	var req UpdateJobRequest
	if err := c.BodyParser(&req); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid request body")
	}

	var job models.Job
	if err := h.db.First(&job, "id = ?", jobID).Error; err != nil {
		return fiber.NewError(fiber.StatusNotFound, "Job not found")
	}

	// Update job fields
	if req.Status != "" {
		job.Status = req.Status
	}
	if req.ResultURL != "" {
		job.ResultURL = req.ResultURL
	}
	if req.Error != "" {
		job.Error = req.Error
	}
	job.UpdatedAt = time.Now()

	if err := h.db.Save(&job).Error; err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Failed to update job")
	}

	return c.JSON(job)
}

func (h *JobsHandler) GetJob(c *fiber.Ctx) error {
	jobID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Invalid job ID")
	}

	userID := GetUserID(c)

	var job models.Job
	if err := h.db.Where("id = ? AND user_id = ?", jobID, userID).First(&job).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return fiber.NewError(fiber.StatusNotFound, "Job not found")
		}
		return fiber.NewError(fiber.StatusInternalServerError, "Query failed")
	}

	return c.JSON(job)
}
