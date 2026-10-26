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
# Secrets déposés par l'installateur (un fichier par secret :
# /config/secrets/<instance>/<nom>) : rangés dans le coffre chiffré, puis effacés.
# Le coffre existe dès le premier démarrage ; un secret déposé avant attend le suivant.
if [ -f /data/master.key ] && [ -d /config/secrets ]; then
  for f in /config/secrets/*/*; do
    [ -f "$f" ] || continue
    instance=$(basename "$(dirname "$f")")
    name=$(basename "$f")
    if /usr/bin/moli-os secrets set "$instance" "$name" < "$f"; then
      rm -f "$f"
      echo "secret rangé : $instance/$name"
    fi
  done
fi
exec /usr/bin/moli-os serve
