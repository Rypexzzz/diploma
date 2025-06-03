#!/usr/bin/env bash
poetry run pyinstaller -y \
  --name OnlineMeetingOptimizer \
  --onedir --windowed --noconfirm \
  --add-data "app/ui/*.ui;app/ui" \
  --add-data "models/*.gguf;models" \
  -p app \
  app/__main__.py