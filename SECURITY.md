# Security Advisory

## Resolved Vulnerabilities

### aiohttp Security Updates (2026-02-02)

**Previous Version:** 3.9.1  
**Updated Version:** >=3.13.3

#### Vulnerabilities Fixed:

1. **CVE: Zip Bomb Vulnerability**
   - **Severity:** High
   - **Description:** aiohttp's HTTP Parser auto_decompress feature is vulnerable to zip bomb attacks
   - **Affected Versions:** <= 3.13.2
   - **Patched Version:** 3.13.3
   - **Status:** ✅ Fixed

2. **CVE: Denial of Service (DoS)**
   - **Severity:** High
   - **Description:** aiohttp vulnerable to Denial of Service when trying to parse malformed POST requests
   - **Affected Versions:** < 3.9.4
   - **Patched Version:** 3.9.4
   - **Status:** ✅ Fixed

3. **CVE: Directory Traversal**
   - **Severity:** High
   - **Description:** aiohttp is vulnerable to directory traversal attacks
   - **Affected Versions:** >= 1.0.5, < 3.9.2
   - **Patched Version:** 3.9.2
   - **Status:** ✅ Fixed

## Action Required

If you have already installed dependencies with the old version, please update:

```bash
pip install --upgrade aiohttp>=3.13.3
```

Or reinstall all dependencies:

```bash
pip install -r requirements.txt --upgrade
```

## Verification

Verify the installed version:

```bash
pip show aiohttp
```

Expected output should show version 3.13.3 or higher.

## Impact on KWASNY LOG MANAGER

The aiohttp library is used in this project for:
- Proxy testing (async HTTP requests)
- Proxy connectivity verification

While these vulnerabilities are concerning, the specific usage in this project (outbound proxy testing) has limited exposure to:
- Zip bomb attacks (we don't decompress responses from untrusted sources)
- POST request parsing (we only make GET requests for proxy testing)
- Directory traversal (we don't serve files)

However, we've updated to the latest secure version as a precautionary measure and to follow security best practices.

## Security Best Practices

1. Always keep dependencies up to date
2. Regularly check for security advisories
3. Use `pip install --upgrade` to update packages
4. Monitor security bulletins for Python packages
5. Run security scans: `pip-audit` or `safety check`

## Reporting Security Issues

If you discover any security vulnerabilities in this project, please report them privately to the maintainers. Do not open public issues for security vulnerabilities.

---

**Last Updated:** 2026-02-02  
**Status:** All known vulnerabilities resolved ✅
