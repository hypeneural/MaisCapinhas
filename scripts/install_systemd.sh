#!/usr/bin/env bash
set -euo pipefail

sudo cp scripts/people-worker.service /etc/systemd/system/people-worker.service
sudo cp scripts/people-api.service /etc/systemd/system/people-api.service
sudo systemctl daemon-reload
sudo systemctl enable people-worker.service people-api.service
sudo systemctl restart people-worker.service people-api.service
