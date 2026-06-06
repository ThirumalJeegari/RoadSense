const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

export function getInitialBackendUrl() {
  return import.meta.env.VITE_BACKEND_URL || DEFAULT_BACKEND_URL;
}

async function request(baseUrl, path, options = {}) {
  const { token, headers, ...fetchOptions } = options;
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers || {}),
    },
    ...fetchOptions,
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }

  return response.json();
}

function query(params) {
  return new URLSearchParams(params).toString();
}

export function getHealth(baseUrl) {
  return request(baseUrl, "/api/health");
}

export function login(baseUrl, payload) {
  return request(baseUrl, "/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function signup(baseUrl, payload) {
  return request(baseUrl, "/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMe(baseUrl, token) {
  return request(baseUrl, "/api/auth/me", { token });
}

export function logout(baseUrl, token) {
  return request(baseUrl, "/api/auth/logout", {
    method: "POST",
    token,
    body: JSON.stringify({}),
  });
}

export function getIndiaLocations(baseUrl) {
  return request(baseUrl, "/api/india-locations");
}

export function getParking(baseUrl, params) {
  return request(baseUrl, `/api/parking?${query(params)}`);
}

export function getTrafficRoute(baseUrl, start, end) {
  return request(baseUrl, `/api/traffic-route?${query({ start, end })}`);
}

export function createPrimeSubscription(baseUrl, payload, token) {
  return request(baseUrl, "/api/subscriptions/prime", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function activatePrimeDemo(baseUrl, token) {
  return request(baseUrl, "/api/subscriptions/prime/activate-demo", {
    method: "POST",
    token,
    body: JSON.stringify({}),
  });
}
