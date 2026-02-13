# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of this project seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

**ar.frappe.dev@gmail.com**

Please include the following information in your report:

- **Type of issue** (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- **Full paths of source file(s)** related to the manifestation of the issue
- **The location of the affected source code** (tag/branch/commit or direct URL)
- **Any special configuration** required to reproduce the issue
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the issue**, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours.
- **Communication**: We will keep you informed of the progress towards a fix and full announcement.
- **Timeline**: We aim to address critical vulnerabilities within 7 days, and less severe issues within 30 days.
- **Credit**: If you would like to be credited for discovering the vulnerability, please let us know how you would like to be identified.

### Safe Harbor

We support safe harbor for security researchers who:

- Make a good faith effort to avoid privacy violations, destruction of data, and interruption or degradation of our services
- Only interact with accounts you own or with explicit permission of the account holder
- Do not exploit a security issue you discover for any reason
- Report any vulnerability you've discovered promptly
- Do not publicly disclose the vulnerability until we've had a chance to address it

We will not pursue civil action or initiate a complaint to law enforcement for accidental, good-faith violations of this policy.

## Security Best Practices for Users

When deploying this application, please ensure:

1. **Keep Dependencies Updated**: Regularly update Frappe, ERPNext, and HRMS to their latest versions
2. **Use Strong Authentication**: Enable two-factor authentication for all admin accounts
3. **Limit Access**: Follow the principle of least privilege when assigning roles
4. **Secure Database**: Use secure passwords and limit database access
5. **Enable HTTPS**: Always use HTTPS in production
6. **Regular Backups**: Maintain regular backups of your data
7. **Monitor Logs**: Regularly review access logs for suspicious activity

## Known Security Considerations

### Data Access

- Overtime entries contain employee attendance data which may be considered sensitive
- Ensure proper role-based access control is configured in Frappe
- The app respects Frappe's built-in permission system

### API Endpoints

- All whitelisted API methods require user authentication
- No guest access is allowed to overtime data

## Contact

For any security-related questions that don't fall under the vulnerability reporting process, please contact:

- **Email**: ar.frappe.dev@gmail.com
- **GitHub Issues**: For non-security-related bugs and feature requests

Thank you for helping keep this project and our users safe!
