FROM quay.io/keycloak/keycloak:26.2

# Discord Identity Provider extension
ADD --chown=keycloak:keycloak https://github.com/wadahiro/keycloak-discord/releases/download/v0.6.1/keycloak-discord-0.6.1.jar /opt/keycloak/providers/keycloak-discord-0.6.1.jar

RUN /opt/keycloak/bin/kc.sh build
