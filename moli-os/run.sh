#!/bin/sh
# Moli OS dans Home Assistant OS : configuration dans /config (dossier de l'add-on),
# données, coffre chiffré et clé maître dans /data (privé à l'add-on). Au premier
# démarrage, Moli crée sa clé maître (/data/master.key) : en garder une copie ailleurs.
set -e
export MOLI_CONFIG=/config/moli.toml
if [ ! -f "$MOLI_CONFIG" ]; then
  cat > "$MOLI_CONFIG" <<'TOML'
[server]
listen = "0.0.0.0:8790"
data_dir = "/data"
worker_threads = 2
TOML
fi
cd /data
exec /usr/bin/moli-os serve
