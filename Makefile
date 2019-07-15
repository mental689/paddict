build:
	# We need to build first
	docker-compose build

run:
	docker-compose up -d

login_to_supervisor:
	# Login to supervisor node
	docker exec -ti paddict_supervisor bash

stop_and_remove:
	# Stop and remove all instances and data! Use with cautions!
	echo "CAUTION: All instances and their data will be lost!"
	docker-compose stop; docker-compose rm -fv; rm -rf db/

stop:
	docker-compose stop

runall:
	docker-compose up -d --force-recreate --build


# Sometimes prunning may be helpful to find an efficient architecture
prune:
	docker image prune
	docker container prune

MYSQL_DUMP="${PWD}/paddict20190715.sql"
import_sql:
	docker exec -i paddict_db mysql -uroot -ppaddict paddict < ${MYSQL_DUMP}
