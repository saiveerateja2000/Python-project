FROM postgres:15-alpine

# Copy initialization script
COPY database/init.sql /docker-entrypoint-initdb.d/

# Expose port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD pg_isready -U postgres || exit 1
