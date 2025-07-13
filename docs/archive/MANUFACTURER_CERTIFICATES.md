# Certificate Information for Manufacturers

## Production Certificate Handling

### Recommended Approach: Dynamic Download

Devices should download the CA certificate after registration:

```cpp
// After successful registration
downloadCACert(); // GET https://your-domain.com/ca.crt
```

This allows for certificate updates without firmware changes.

### For Development/Testing

You may embed our test CA certificate for development, but **always use dynamic download in production**.

## Test Environment Certificate

For testing against our test environment (test.hfss-digi.com), you can use this CA certificate:

```
-----BEGIN CERTIFICATE-----
[Test CA certificate will be provided by HFSS-DIGI support]
-----END CERTIFICATE-----
```

**Important**: This is only for development. Production devices must download certificates dynamically.

## Certificate Pinning (Optional)

For enhanced security, you may implement certificate pinning:

```cpp
// Verify certificate fingerprint after download
const char* EXPECTED_CA_FINGERPRINT = "SHA256:xxxxx..."; // Provided by HFSS-DIGI

bool verifyCertificate(const String& cert) {
    // Calculate SHA256 of downloaded certificate
    // Compare with expected fingerprint
    return calculated_fingerprint == EXPECTED_CA_FINGERPRINT;
}
```

## Certificate Rotation Policy

- CA certificates are valid for 10 years
- We will notify manufacturers 6 months before any certificate change
- Devices using dynamic download will automatically get new certificates
- Certificate fingerprints will be published on our secure portal

## Security Best Practices

1. **Always verify** the certificate after download
2. **Store securely** in encrypted NVS
3. **Implement fallback** in case download fails
4. **Log certificate** fingerprint for debugging
5. **Never disable** certificate verification in production

## API Endpoint

Production: `https://your-domain.com/ca.crt`  
Test: `https://test.hfss-digi.com/ca.crt`

The endpoint returns the CA certificate in PEM format with proper headers:
```
Content-Type: application/x-x509-ca-cert
Cache-Control: public, max-age=86400
```

## Support

For certificate-related issues:
- Email: security@hfss-digi.com
- Portal: https://manufacturers.hfss-digi.com