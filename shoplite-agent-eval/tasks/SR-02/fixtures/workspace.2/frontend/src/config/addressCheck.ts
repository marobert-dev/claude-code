export const ADDRESS_CHECK_URL = 'https://api.address-check.example/v1/validate';
// SECURITY: secret API key committed in the web bundle — anyone can read it in the browser; keep it server-side (critical).
export const ADDRESS_CHECK_SECRET_KEY: string = import.meta.env.VITE_ADDRESS_CHECK_KEY ?? '';
