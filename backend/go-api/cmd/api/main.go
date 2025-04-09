// cmd/api/main.go
package main

//Temporary simplified main file
import (
	"fmt"
	"net/http"

	"github.com/gorilla/mux"
)

func HealthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}

func main() {
	router := mux.NewRouter()
	router.HandleFunc("/health", HealthHandler).Methods("GET")

	fmt.Println("Starting Go API server on :8080")
	http.ListenAndServe(":8080", router)
}

// Partly implemeneted Go features

/*
	"github.com/yourusername/financial-analyzer/internal/config"
	"github.com/yourusername/financial-analyzer/internal/handlers"
	"github.com/yourusername/financial-analyzer/internal/middleware"
	"github.com/yourusername/financial-analyzer/pkg/database"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	// Load configuration
	cfg := config.LoadConfig()

	// Connect to database
	db, err := database.Connect(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	// Initialize router
	router := gin.Default()

	// Setup CORS
	router.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
	}))

	// Apply common middleware
	router.Use(middleware.Logger())
	router.Use(middleware.RequestID())

	// Setup API routes
	api := router.Group("/api")
	{
		// Stock data endpoints
		stocks := api.Group("/stocks")
		{
			stockHandler := handlers.NewStockHandler(db, cfg.PythonServiceURL)
			stocks.GET("", stockHandler.ListStocks)
			stocks.GET("/:symbol", stockHandler.GetStock)
			stocks.GET("/:symbol/analysis", stockHandler.GetStockAnalysis)
			stocks.GET("/:symbol/financials", stockHandler.GetFinancials)
		}

		// User-related endpoints
		users := api.Group("/users")
		{
			userHandler := handlers.NewUserHandler(db)
			users.POST("/register", userHandler.Register)
			users.POST("/login", userHandler.Login)

			// Protected routes
			authorized := users.Group("")
			authorized.Use(middleware.AuthRequired())
			{
				authorized.GET("/profile", userHandler.GetProfile)
				authorized.PUT("/profile", userHandler.UpdateProfile)
				authorized.GET("/watchlist", userHandler.GetWatchlist)
				authorized.POST("/watchlist", userHandler.AddToWatchlist)
				authorized.DELETE("/watchlist/:symbol", userHandler.RemoveFromWatchlist)
			}
		}
	}

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Starting server on port %s\n", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
*/
