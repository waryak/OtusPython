#!/usr/bin/env bash
docker run --rm --name otus_redis -p 6379:6379 -d redis
docker run -it --rm --network host redis redis-cli -h 0.0.0.0