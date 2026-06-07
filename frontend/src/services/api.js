const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

export function getInitialBackendUrl() {
  return import.meta.env.VITE_BACKEND_URL || DEFAULT_BACKEND_URL;
}

async function request(baseUrl, path, options = {}) {
  const { token, headers, ...fetchOptions } = options;
  const url = `${baseUrl.replace(/\/$/, "")}${path}`;
  let response;

  try {
    response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(headers || {}),
      },
      ...fetchOptions,
    });
  } catch (error) {
    throw new Error(
      `Cannot connect to backend at ${baseUrl}. Check VITE_BACKEND_URL, backend deployment, and CORS settings.`,
    );
  }

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

export function forgotPassword(baseUrl, payload) {
  return request(baseUrl, "/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resetPassword(baseUrl, payload) {
  return request(baseUrl, "/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMe(baseUrl, token) {
  return request(baseUrl, "/api/auth/me", { token });
}

export function updateProfile(baseUrl, payload, token) {
  return request(baseUrl, "/api/auth/profile", {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
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

export function searchIndiaLocations(baseUrl, search, limit = 8) {
  return request(baseUrl, `/api/location-search?${query({ q: search, limit })}`);
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

export function syncPrimeSubscription(baseUrl, token, subscriptionId = "") {
  return request(baseUrl, "/api/subscriptions/prime/sync", {
    method: "POST",
    token,
    body: JSON.stringify(subscriptionId ? { subscription_id: subscriptionId } : {}),
  });
}

export function activatePrimeDemo(baseUrl, token) {
  return request(baseUrl, "/api/subscriptions/prime/activate-demo", {
    method: "POST",
    token,
    body: JSON.stringify({}),
  });
}
