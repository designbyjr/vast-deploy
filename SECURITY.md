# Security Notice

## Environment Variables

⚠️ **IMPORTANT SECURITY NOTICE** ⚠️

The actual `.env` file in this repository contains **LIVE PRODUCTION CREDENTIALS** and should **NEVER** be committed to version control or shared.

### What to do:

1. **Immediately rotate credentials** if this repository becomes public
2. **Use `.env.example`** as a template for your own environment setup
3. **Add `.env` to `.gitignore`** (if not already present)
4. **Use proper secrets management** in production environments

### Production Deployment

For production deployments, credentials should be:
- Stored in secure secret management systems (AWS Secrets Manager, HashiCorp Vault, etc.)
- Injected as environment variables at runtime
- Never hardcoded in source code or configuration files

### Files that may contain sensitive information:

- `.env` - **Contains live credentials - DO NOT SHARE**
- `tests/simple_token_test.py` - **REMOVED** (contained hardcoded credentials)
- `app/middleware/auth.py` - **FIXED** (now reads from environment variables)
- `docker-compose.yml` - **NEEDS ATTENTION** (contains live Redis credentials)

### Recommended Actions:

1. Create new Upstash Redis instance with fresh credentials
2. Update environment variables with new credentials
3. Remove old credentials from all files
4. Add proper secrets management for production deployments

## Other Security Considerations

### TLS Certificates
- Self-signed certificates are generated automatically for development
- Use proper CA-signed certificates in production
- Implement certificate rotation procedures

### Authentication
- Implement proper user management system
- Use strong authentication tokens
- Implement token rotation and expiration

### Container Security
- Runs as non-root user
- Uses security options like `no-new-privileges`
- Resource limits applied to prevent DoS

### Network Security
- Only HTTPS port (9443) is exposed
- Implement proper firewall rules
- Use VPN or private networking for internal services