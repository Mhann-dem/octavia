package db

import (
	"context"
	"time"

	"github.com/LunarTechAI/octavia/api-gateway/internal/models"
	"github.com/rabbitmq/amqp091-go"
	"github.com/redis/go-redis/v9"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func InitDB(url string) (*gorm.DB, error) {
	db, err := gorm.Open(postgres.Open(url), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	sqlDB, _ := db.DB()
	sqlDB.SetMaxOpenConns(25)
	sqlDB.SetMaxIdleConns(5)
	sqlDB.SetConnMaxLifetime(5 * time.Minute)

	db.AutoMigrate(&models.User{}, &models.Job{}, &models.Transaction{})

	return db, nil
}

func InitRedis(url string) (*redis.Client, error) {
	client := redis.NewClient(&redis.Options{Addr: url})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, err := client.Ping(ctx).Result()
	return client, err
}

func InitRabbitMQ(url, queue, dlq string) (*amqp091.Connection, *amqp091.Channel, error) {
	conn, err := amqp091.Dial(url)
	if err != nil {
		return nil, nil, err
	}

	ch, err := conn.Channel()
	if err != nil {
		return nil, nil, err
	}

	ch.QueueDeclare(queue, true, false, false, false, nil)
	ch.QueueDeclare(dlq, true, false, false, false, nil)

	return conn, ch, nil
}
