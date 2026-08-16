# Cloud Database: Managed vs Self-Hosted

**Managed (RDS, Atlas, Supabase)** costs more per month but removes backup,
patching, and failover work. Good for small teams without dedicated DB ops.

**Self-hosted** (EC2 + Postgres/Mongo yourself) is cheaper at scale but needs
someone to own backups, security patches, and uptime monitoring.

**Rule of thumb**: use managed until you have a dedicated ops person or DB
costs become a real % of your infra bill.
