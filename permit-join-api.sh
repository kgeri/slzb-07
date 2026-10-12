#!/usr/bin/env bash
# Allow Zigbee devices to join without restarting the listener.
#
# Runs the request inside the pod against the loopback-only admin API, so
# nothing is exposed on the network. After this returns, put your device into
# pairing mode within the permit window (max 254s).
#
# Usage: ./permit-join-api.sh [seconds]
# Env:   NAMESPACE, DEPLOYMENT, ADMIN_PORT
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
DEPLOYMENT="${DEPLOYMENT:-zigbee-listener}"
ADMIN_PORT="${ADMIN_PORT:-9103}"
PERMIT_SECONDS="${1:-240}"

if ! [[ "$PERMIT_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "seconds must be an integer" >&2
  exit 2
fi

pod="$(kubectl -n "$NAMESPACE" get pod \
  -l "app=$DEPLOYMENT" \
  -o jsonpath='{.items[0].metadata.name}')"

if [[ -z "$pod" ]]; then
  echo "No pod found for app=$DEPLOYMENT in namespace $NAMESPACE" >&2
  exit 1
fi

api() {
  kubectl -n "$NAMESPACE" exec "$pod" -- \
    curl -fsS "http://127.0.0.1:${ADMIN_PORT}$1"
}

echo "== Devices (age = time since last message) =="
api "/devices"
echo
echo "== Permitting joins for ${PERMIT_SECONDS}s =="
api "/permit?seconds=${PERMIT_SECONDS}"
echo
echo "Now put your device into pairing mode (hold the button 5+ s)."
