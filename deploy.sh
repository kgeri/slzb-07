#!/bin/bash

CWD=$(dirname $0)

# Docker cleanup
docker container prune -f
docker image prune -f

# Build
docker build -t zigbee-listener .

# Deploy
export IMAGE_TAG=$(docker images -q zigbee-listener)
docker tag "zigbee-listener" "srvu:5000/zigbee-listener:$IMAGE_TAG"
docker push "srvu:5000/zigbee-listener:$IMAGE_TAG"
envsubst < "$CWD/deployment.yaml" | kubectl apply -f -

echo "Deployment completed"
