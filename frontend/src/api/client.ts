import axios from 'axios';

export const isDemoMode = (): boolean =>
  import.meta.env.VITE_DEMO_MODE === 'true';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request interceptor
client.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

// Response interceptor — normalize errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.warn(`[API] ${error.response.status} ${error.config?.url}`);
    } else if (error.request) {
      console.warn(`[API] No response from server — demo mode will activate`);
    }
    return Promise.reject(error);
  },
);

export default client;
