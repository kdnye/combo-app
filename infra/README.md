# Infrastructure assets

This directory stores shared operational assets for the monorepo. Place
docker-compose bundles, reverse-proxy configuration, and other common
infrastructure files here so that every application can rely on a single
source of truth for local development and deployment orchestration.

- `compose/` — Docker Compose definitions for running the stack locally
  or in ephemeral environments.
- `docker/` — Reserved for base Dockerfiles, health checks, and
  multi-service build contexts as they are introduced.
- `ingress/` — Reserved for Traefik, SWAG, or NGINX configuration once
  public ingress is required.
