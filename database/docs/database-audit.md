# Database Audit

## Overview

The database component of the PGS Search Engine project provides the data storage and management layer for the system. It uses PostgreSQL, SQLAlchemy, Alembic, and PostGIS.

## Database Components

The database package contains:

- SQLAlchemy models
- Pydantic schemas
- Repository classes
- PostgreSQL configuration
- Alembic migrations
- Database seed scripts
- Database tests
- Geography data
- Bronze, Silver, and Gold data layers
- Quarantine and error logging
- Database health checks
- ERD and database documentation

## Geography

The project contains geographical information for Nepal, including:

- 7 provinces
- 77 districts
- 753 local bodies

The geography data uses hierarchical relationships between provinces, districts, and local bodies.

## Data Pipeline

The database supports a Bronze, Silver, and Gold architecture.

### Bronze

The Bronze layer preserves data received from the scraper before further processing.

### Silver

The Silver layer contains normalized and processed records such as pages, geographical information, contacts, sources, media, and embeddings.

### Gold

The Gold layer contains processed information used for ranking, regional analysis, and search-related functionality.

## Security

The database includes support for:

- Password hashing
- Database roles and permissions
- Error tracking
- Data validation
- Quarantine of problematic records

Admin passwords are stored using password hashing rather than plain text.

## PostGIS

PostGIS is used for geographical operations such as administrative boundaries, geometry intersections, and GeoJSON generation.

## Current Risks and Improvements

The following areas require further verification or improvement:

1. Geography data provenance should be verified against authoritative sources.
2. Database migrations should be tested against a PostgreSQL database.
3. Seed validation should verify hierarchy and data consistency before insertion.
4. Bronze ingestion error handling should be tested.
5. Database documentation should remain consistent with the implemented ETL pipeline.

## Scope of Database Work

The database work on the `purnika` branch will focus on database schema, validation, seed data, migrations, repositories, testing, and database documentation.
