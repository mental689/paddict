stop_and_remove:
	docker-compose stop; docker-compose rm -fv; rm -rf db/mariadb/

stop:
	docker-compose stop

runall:
	docker-compose up -d --force-recreate --build


# Sometimes prunning may be helpful to find an efficient architecture
prune:
	docker image prune
	docker container prune
