# CityShield / VisionScan — convenience targets (Linux / macOS).
# Windows users: use .\start.ps1 and .\stop.ps1 instead.
.PHONY: up start down stop logs ps restart rebuild clean health

up start:        ## Build + start the stack (and bootstrap .env)
	@./start.sh

down stop:       ## Stop containers (data + models preserved)
	docker compose down

logs:            ## Follow container logs
	docker compose logs -f

ps:              ## Show container status
	docker compose ps

restart:         ## Restart containers
	docker compose restart

rebuild:         ## Rebuild images with no cache, then start
	docker compose build --no-cache && docker compose up -d

clean:           ## Stop and DELETE all data/model volumes (full reset)
	docker compose down -v

health:          ## Curl the backend health endpoint
	curl -fsS http://localhost:8000/api/health && echo
