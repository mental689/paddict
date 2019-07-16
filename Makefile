help:
	echo "Welcome to PADDICT reader v1.0!"
	echo "To start reading offline, you have to follow some guide because some preparations must be done ONLINE."
	echo "Please follow the instruction in an ONLINE environment before turning into OFFLINE mode:"

build:
	# We need to build first
	docker-compose build

SCALE="supervisor=1" # To change the number of each node types, for example, you can choose supervisor=2 to have Two Teachers
run:
	docker-compose up -d --scale ${SCALE}

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
	docker-compose up -d --force-recreate --build  --scale ${SCALE}


# Sometimes prunning may be helpful to find an efficient architecture
prune:
	docker image prune --filter until=`date +%s` --all
	docker container prune --filter until=`date +%s`

# Sometimes we may need to search for a built efficient architecture in Docker Hub
QUERY="paddict"
FILTER="is-automated=true"
search:
	docker search ${QUERY} \
		--no-trunc --limit 100 --filter ${FILTER} --format "{{.Name}}:\t{{.StarCount}}\t{{.Description}}\t{{.IsAutomated}}\t{{.IsOfficial}}"

# Import/export MySQL data
MYSQL_DUMP="${PWD}/paddict20190715.sql"
import_sql:
	docker exec -i paddict_db mysql -uroot -ppaddict paddict < ${MYSQL_DUMP}

export_sql:
	docker exec -i paddict_db /usr/bin/mysqldump -uroot -ppaddict paddict > "./paddict"`date +%F`".sql"

# Import/export Elasticsearch data
# Will pull an image from the Internet
ELASTICSEARCH_DUMP="paddict20190715.data.json"
import_es_data:
	echo "This command will pull an image from Internet. Be sure to pull it when you are ONLINE, because in OFFLINE mode, you will not have Internet access."
	docker exec -it paddict_supervisor python manage.py clear_index
	docker run --rm --network=container:es01 \
		-it -v "${PWD}":/data \
		taskrabbit/elasticsearch-dump \
		--input=/data/${ELASTICSEARCH_DUMP} \
		--output=http://localhost:9200/paddict \
		--type=data
		



