# Le binaire publié par le dépôt Moli OS (multi-architecture : x86-64, ARM 64 bits).
# Les ARG utilisés dans un FROM se déclarent avant le premier FROM.
ARG BUILD_FROM
ARG MOLI_IMAGE=ghcr.io/rudy-io/moli-os:main
FROM ${MOLI_IMAGE} AS moli

FROM ${BUILD_FROM}
COPY --from=moli /moli-os /usr/bin/moli-os
COPY run.sh /run.sh
RUN chmod a+x /run.sh
CMD ["/run.sh"]
