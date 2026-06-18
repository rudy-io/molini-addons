# Base image fournie par le superviseur HA (résolue par build.yaml selon arch).
# Alpine 3.20 + Python 3.12 + bashio + s6-overlay déjà inclus.
ARG BUILD_FROM
FROM ${BUILD_FROM}

# Métadonnées de version reportées au central. Le superviseur HA injecte
# BUILD_VERSION (= version de config.yaml) comme build-arg ; on s'en sert pour
# que AGENT_VERSION reflète la vraie version (sinon le heartbeat reste figé).
ARG BUILD_VERSION
ARG MOLINI_AGENT_VERSION=${BUILD_VERSION:-0.5.2}
ENV MOLINI_AGENT_VERSION=${MOLINI_AGENT_VERSION} \
    AGENT_VERSION=${MOLINI_AGENT_VERSION} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MOLINI_RUNTIME=haos

# Outils requis :
# - tar : présent par défaut sur Alpine, on s'assure
# - age : chiffrement des backups
# - ca-certificates : HTTPS sortant
# - tzdata : pour respecter BACKUP_HOUR_LOCAL en heure locale
RUN apk add --no-cache \
        tar \
        age \
        ca-certificates \
        tzdata

# Deps Python
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# Code agent (copie minimaliste, pas de tests embarqués)
WORKDIR /app
COPY molini_agent/ /app/molini_agent/

# Marquage de version pour AGENT_VERSION reporté (compatibilité avec ancien
# mécanisme OTA, ici la version vient du tag d'image add-on)
RUN echo "${MOLINI_AGENT_VERSION}" > /app/.agent_version

# rootfs : entrypoint s6 + permissions
COPY rootfs/ /
RUN chmod a+x /etc/services.d/molini-agent/run \
 && chmod a+x /etc/services.d/molini-agent/finish

# Pas de CMD — s6-overlay (hérité de la base) prend le relais avec /init
