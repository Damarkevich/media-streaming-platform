.PHONY: coverage-functional

coverage-functional:
	# Build/start containers and execute functional tests in `tests` service.
	docker compose up --build tests

	# Send USR1 to PID 1 inside `test-fastapi` to persist `.coverage.fastapi*`.
	docker compose exec -T test-fastapi sh -lc 'kill -USR1 1'
	
	# Merge coverage artifacts and generate HTML/text reports.
	docker compose run --rm coverage-report

	# Stop and remove all containers after report generation.
	docker compose down
