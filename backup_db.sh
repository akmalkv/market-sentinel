FILENAME="backup_$(date +%Y%m%d).sql"

docker exec sentinel_db pg_dump -U admin_sentinel sentinel_core > ~/market-sentinel/backups/$FILENAME

find ~/market-sentinel/backups -type f -mtime +7 -name "*.sql" -delete
