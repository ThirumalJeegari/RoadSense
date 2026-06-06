import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Building2,
  Construction,
  Crown,
  LogIn,
  LogOut,
  Navigation,
  ParkingCircle,
  RefreshCcw,
  Route,
  ShieldCheck,
  UserCircle,
} from "lucide-react";
import MapPanel from "./components/MapPanel.jsx";
import {
  activatePrimeDemo,
  createPrimeSubscription,
  getMe,
  getIndiaLocations,
  getInitialBackendUrl,
  getParking,
  getTrafficRoute,
  login,
  logout,
  searchIndiaLocations,
  signup,
} from "./services/api.js";
import { routeDamageReport } from "./utils/roadDamage.js";
import "./styles.css";

const FALLBACK_LOCATIONS = [
  { name: "Bengaluru", state: "Karnataka", latitude: 12.9716, longitude: 77.5946 },
  { name: "Chennai", state: "Tamil Nadu", latitude: 13.0827, longitude: 80.2707 },
  { name: "Delhi", state: "Delhi", latitude: 28.6139, longitude: 77.209 },
  { name: "Hyderabad", state: "Telangana", latitude: 17.385, longitude: 78.4867 },
  { name: "Mumbai", state: "Maharashtra", latitude: 19.076, longitude: 72.8777 },
  { name: "Pune", state: "Maharashtra", latitude: 18.5204, longitude: 73.8567 },
];

const tabs = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "traffic", label: "Traffic Management", icon: Route },
  { id: "parking", label: "Smart Parking", icon: ParkingCircle },
  { id: "damage", label: "Road Damage Detection", icon: Construction },
];

const pages = ["home", "dashboard", "login", "signup", "subscription"];

const primeFeatureLabels = [
  "Predictive traffic risk",
  "Expanded parking coverage",
  "Road repair priority queue",
  "Operations playbook",
];

function pageFromHash() {
  const page = window.location.hash.replace(/^#\/?/, "") || "home";
  return pages.includes(page) ? page : "home";
}

function navigateToPage(page) {
  window.location.hash = `#/${page}`;
}

function locationLabel(location) {
  return `${location.name}, ${location.state}`;
}

function uniqueLocationName(name, fallback) {
  return name?.trim() || fallback;
}

function getStoredAuth() {
  try {
    return JSON.parse(localStorage.getItem("roadSenseAuth") || "null");
  } catch {
    return null;
  }
}

function saveStoredAuth(auth) {
  localStorage.setItem("roadSenseAuth", JSON.stringify(auth));
}

function clearStoredAuth() {
  localStorage.removeItem("roadSenseAuth");
}

function profileValue(value, fallback = "Not set") {
  return value ? String(value) : fallback;
}

function titleValue(value) {
  return profileValue(value)
    .split(" ")
    .map((part) => (part ? `${part[0].toUpperCase()}${part.slice(1)}` : part))
    .join(" ");
}

function locationOptionLabel(location) {
  return location.display_name || [location.name, location.admin1, location.country].filter(Boolean).join(", ");
}

function LocationDatalist({ id, suggestions }) {
  return (
    <datalist id={id}>
      {suggestions.map((location) => {
        const label = locationOptionLabel(location);
        return (
          <option
            value={label}
            key={`${label}-${location.latitude}-${location.longitude}`}
          />
        );
      })}
    </datalist>
  );
}

function useIndiaLocationSuggestions(backendUrl, search, enabled) {
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    const query = search.trim();
    if (!enabled || query.length < 3) {
      setSuggestions([]);
      return undefined;
    }

    let cancelled = false;
    const id = window.setTimeout(async () => {
      try {
        const response = await searchIndiaLocations(backendUrl, query, 8);
        if (!cancelled) {
          setSuggestions(response.locations || []);
        }
      } catch {
        if (!cancelled) {
          setSuggestions([]);
        }
      }
    }, 450);

    return () => {
      cancelled = true;
      window.clearTimeout(id);
    };
  }, [backendUrl, enabled, search]);

  return suggestions;
}

function MetricCard({ icon: Icon, label, value, note, tone = "blue" }) {
  return (
    <section className={`metric-card tone-${tone}`}>
      <div className="metric-icon">
        <Icon size={18} strokeWidth={2.3} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{note}</span>
      </div>
    </section>
  );
}

function DataPanel({ title, rows, note }) {
  return (
    <section className="data-panel">
      <h3>{title}</h3>
      <div className="data-rows">
        {rows.map(([label, value]) => (
          <div className="data-row" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      {note ? <p className="panel-note">{note}</p> : null}
    </section>
  );
}

function SegmentBars({ summary }) {
  const values = [
    { label: "Normal", value: summary?.normal_segments || 0, color: "#2563eb" },
    { label: "Moderate", value: summary?.moderate_segments || 0, color: "#d97706" },
    { label: "Heavy", value: summary?.heavy_segments || 0, color: "#dc2626" },
  ];
  const max = Math.max(1, ...values.map((item) => item.value));

  return (
    <section className="data-panel segment-panel">
      <h3>Traffic Segment Mix</h3>
      {values.map((item) => (
        <div className="segment-bar" key={item.label}>
          <div className="segment-label">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
          <div className="bar-track">
            <div style={{ width: `${(item.value / max) * 100}%`, background: item.color }} />
          </div>
        </div>
      ))}
    </section>
  );
}

function PrimeInsightsPanel({
  isPrime,
  trafficSummary,
  parking,
  damageReport,
  selectedStart,
  selectedEnd,
  selectedParkingCity,
  onGoSubscription,
}) {
  const projectedCongestion = Math.min(98, Number(trafficSummary.congestion_score || 0) + 12);
  const reserveSlots = Math.max(0, Math.round(Number(parking.vacant_spaces || 0) * 0.35));
  const topDamage = damageReport.detections?.[0];

  if (!isPrime) {
    return (
      <section className="prime-insights locked">
        <div className="prime-insights-head">
          <div>
            <span>Prime Locked</span>
            <h3>Subscriber Operations Layer</h3>
            <p>Prime users get prediction, priority, and response planning on top of the live map.</p>
          </div>
          <Crown size={22} />
        </div>
        <div className="prime-feature-grid">
          {primeFeatureLabels.map((feature) => (
            <div className="prime-feature-card" key={feature}>
              <ShieldCheck size={17} />
              <strong>{feature}</strong>
              <span>Upgrade required</span>
            </div>
          ))}
        </div>
        <button className="primary-button compact-button" onClick={onGoSubscription}>
          <Crown size={16} />
          Upgrade to Prime
        </button>
      </section>
    );
  }

  return (
    <section className="prime-insights active">
      <div className="prime-insights-head">
        <div>
          <span>Prime Active</span>
          <h3>Subscriber Operations Layer</h3>
          <p>Priority intelligence for traffic, parking, and maintenance decisions.</p>
        </div>
        <Crown size={22} />
      </div>
      <div className="prime-feature-grid">
        <div className="prime-feature-card">
          <Activity size={17} />
          <strong>{projectedCongestion}%</strong>
          <span>Predicted next-hour congestion</span>
        </div>
        <div className="prime-feature-card">
          <ParkingCircle size={17} />
          <strong>{reserveSlots}</strong>
          <span>Reserve slots near {selectedParkingCity}</span>
        </div>
        <div className="prime-feature-card">
          <Construction size={17} />
          <strong>{topDamage?.priority || damageReport.severity}</strong>
          <span>{topDamage?.road_segment || `${selectedStart} to ${selectedEnd}`}</span>
        </div>
        <div className="prime-feature-card">
          <Route size={17} />
          <strong>Dispatch Ready</strong>
          <span>Open route, parking, and repair playbook</span>
        </div>
      </div>
    </section>
  );
}

function Legend({ type }) {
  if (type === "parking") {
    return (
      <div className="legend">
        <span><i className="dot green" />Available</span>
        <span><i className="dot red" />Full</span>
      </div>
    );
  }
  if (type === "damage") {
    return (
      <div className="legend">
        <span><i className="dot red" />High</span>
        <span><i className="dot amber" />Moderate</span>
        <span><i className="dot blue" />Low</span>
      </div>
    );
  }
  return (
    <div className="legend">
      <span><i className="dot blue" />Normal</span>
      <span><i className="dot amber" />Moderate</span>
      <span><i className="dot red" />Heavy</span>
    </div>
  );
}

function ParkingTable({ stalls }) {
  if (!stalls?.length) {
    return <div className="empty-state">No parking slot data returned for this city.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Available</th>
            <th>Capacity</th>
            <th>Status</th>
            <th>Access</th>
          </tr>
        </thead>
        <tbody>
          {stalls.slice(0, 80).map((stall) => (
            <tr key={stall.id || `${stall.name}-${stall.latitude}-${stall.longitude}`}>
              <td>{stall.name || "Parking point"}</td>
              <td>{stall.parking_type || "Parking"}</td>
              <td>{stall.available_slots ?? "-"}</td>
              <td>{stall.capacity ?? "-"}</td>
              <td>
                <span className={`status-pill ${Number(stall.available_slots || 0) > 0 ? "available" : "full"}`}>
                  {Number(stall.available_slots || 0) > 0 ? "Available" : "Full"}
                </span>
              </td>
              <td>{stall.access || "Public"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DamageTable({ detections }) {
  if (!detections?.length) {
    return <div className="empty-state">No damaged road points found for this route.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Road Segment</th>
            <th>Severity</th>
            <th>Type</th>
            <th>Location</th>
            <th>Length</th>
            <th>Priority</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {detections.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.road_segment}</td>
              <td>
                <span className={`severity ${item.severity.toLowerCase()}`}>{item.severity}</span>
              </td>
              <td>{item.type}</td>
              <td>{item.damage_location}</td>
              <td>{item.estimated_length_m} m</td>
              <td>{item.priority}</td>
              <td>{item.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AccountPanel({ auth, onLogin, onLogout, loading }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await onLogin({ email, password });
      setPassword("");
    } catch (loginError) {
      setError(loginError.message);
    }
  }

  if (auth?.user) {
    return (
      <section className="account-card">
        <div className="account-title">
          <UserCircle size={18} />
          <div>
            <h3>{auth.user.name}</h3>
            <p>{auth.user.email}</p>
          </div>
        </div>
        <div className="account-badge">Logged in</div>
        <button className="secondary-button" onClick={onLogout} disabled={loading}>
          <LogOut size={16} />
          Log out
        </button>
      </section>
    );
  }

  return (
    <section className="account-card">
      <div className="account-title">
        <LogIn size={18} />
        <div>
          <h3>Login</h3>
          <p>Access Prime checkout</p>
        </div>
      </div>
      <form className="login-form" onSubmit={submit}>
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email address" />
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
        />
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
      {error ? <p className="mini-error">{error}</p> : null}
    </section>
  );
}

function SignupPanel({ auth, onSignup, loading, onGoLogin }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    try {
      await onSignup({ name, email, password });
      setPassword("");
      setConfirmPassword("");
    } catch (signupError) {
      setError(signupError.message);
    }
  }

  if (auth?.user) {
    return (
      <section className="account-card">
        <div className="account-title">
          <UserCircle size={18} />
          <div>
            <h3>Account Ready</h3>
            <p>{auth.user.email}</p>
          </div>
        </div>
        <div className="account-badge">Signed up</div>
      </section>
    );
  }

  return (
    <section className="account-card">
      <div className="account-title">
        <UserCircle size={18} />
        <div>
          <h3>Signup</h3>
          <p>Create operator account</p>
        </div>
      </div>
      <form className="login-form" onSubmit={submit}>
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Full name" />
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email address" />
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
        />
        <input
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          placeholder="Confirm password"
        />
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>
      <button className="text-button" type="button" onClick={onGoLogin}>
        Already have an account? Login
      </button>
      {error ? <p className="mini-error">{error}</p> : null}
    </section>
  );
}

function PrimePanel({ backendUrl, auth, onAuthUpdate }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const isPrime = auth?.user?.plan === "prime";

  async function subscribe() {
    if (!auth?.user) {
      setResult({ error: "Login before starting Prime subscription." });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      setResult(
        await createPrimeSubscription(
          backendUrl,
          {
            name: auth.user.name,
            email: auth.user.email,
          },
          auth.token,
        ),
      );
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function activateDemo() {
    if (!auth?.token) {
      setResult({ error: "Login before activating Prime." });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const response = await activatePrimeDemo(backendUrl, auth.token);
      onAuthUpdate(response);
      setResult({ activated: true, message: "Prime features activated for this account." });
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={`prime-card ${isPrime ? "prime-active-card" : ""}`}>
      <div className="prime-title">
        <Crown size={18} />
        <div>
          <h3>{isPrime ? "Prime Active" : "Prime"}</h3>
          <p>{isPrime ? "Subscriber benefits unlocked" : "Razorpay subscription"}</p>
        </div>
      </div>
      <div className="prime-features">
        {primeFeatureLabels.map((feature) => (
          <span key={feature}>{feature}</span>
        ))}
      </div>
      {isPrime ? <div className="account-badge">Prime subscriber</div> : null}
      {!isPrime ? (
        <button className="primary-button" onClick={subscribe} disabled={loading || !auth?.user}>
          {loading ? "Creating link..." : "Subscribe with Razorpay"}
        </button>
      ) : null}
      {!isPrime && auth?.user ? (
        <button className="secondary-button" onClick={activateDemo} disabled={loading}>
          <ShieldCheck size={16} />
          Activate Prime Demo
        </button>
      ) : null}
      {result?.short_url ? (
        <a className="checkout-link" href={result.short_url} target="_blank" rel="noreferrer">
          Open Razorpay Checkout
        </a>
      ) : null}
      {result?.activated ? <p className="mini-warning">{result.message}</p> : null}
      {!auth?.user ? <p className="mini-warning">Login to continue with Prime.</p> : null}
      {result?.mode === "demo" ? (
        <p className="mini-warning">Add Razorpay keys and Prime plan ID in Render for live payments.</p>
      ) : null}
      {result?.error ? <p className="mini-error">{result.error}</p> : null}
    </section>
  );
}

function LoginPage({ auth, onLogin, onLogout, loading, onGoSignup, onGoSubscription }) {
  return (
    <section className="page-grid">
      <div className="page-card login-hero-card">
        <span className="page-kicker">Secure Access</span>
        <h3>Login to manage RoadSense Prime</h3>
        <p>
          Sign in with your operator account before starting the Razorpay Prime subscription.
        </p>
        {auth?.user ? (
          <button className="primary-button compact-button" onClick={onGoSubscription}>
            <Crown size={16} />
            Go to Subscription
          </button>
        ) : null}
      </div>
      <AccountPanel auth={auth} onLogin={onLogin} onLogout={onLogout} loading={loading} />
      {!auth?.user ? (
        <button className="text-button page-switch-link" type="button" onClick={onGoSignup}>
          New here? Create account
        </button>
      ) : null}
    </section>
  );
}

function SignupPage({ auth, onSignup, loading, onGoLogin, onGoSubscription }) {
  return (
    <section className="page-grid">
      <div className="page-card signup-hero-card">
        <span className="page-kicker">New Operator</span>
        <h3>Create your RoadSense account</h3>
        <p>
          Register once, then use the same account for dashboard access and Razorpay Prime subscription.
        </p>
        {auth?.user ? (
          <button className="primary-button compact-button" onClick={onGoSubscription}>
            <Crown size={16} />
            Continue to Prime
          </button>
        ) : null}
      </div>
      <SignupPanel auth={auth} onSignup={onSignup} loading={loading} onGoLogin={onGoLogin} />
    </section>
  );
}

function SubscriptionPage({ backendUrl, auth, onGoLogin, onAuthUpdate }) {
  const isPrime = auth?.user?.plan === "prime";

  return (
    <section className="page-grid">
      <div className="page-card subscription-hero-card">
        <span className="page-kicker">{isPrime ? "Prime Active" : "Prime Plan"}</span>
        <h3>{isPrime ? "Subscriber features are unlocked" : "Subscribe with Razorpay"}</h3>
        <p>
          {isPrime
            ? "Your account now includes the Prime operations layer for prediction, priority, and response planning."
            : "Unlock the Prime checkout flow for live traffic operations, expanded parking intelligence, and road survey planning."}
        </p>
        <div className="subscription-list">
          {primeFeatureLabels.map((feature) => (
            <span key={feature}>{feature}</span>
          ))}
        </div>
        {!auth?.user ? (
          <button className="primary-button compact-button" onClick={onGoLogin}>
            <LogIn size={16} />
            Login First
          </button>
        ) : null}
      </div>
      <PrimePanel backendUrl={backendUrl} auth={auth} onAuthUpdate={onAuthUpdate} />
    </section>
  );
}

function AccessRequiredPage({ onGoLogin, onGoSignup }) {
  return (
    <section className="page-grid">
      <div className="page-card access-hero-card">
        <span className="page-kicker">Login Required</span>
        <h3>Login before opening the operations dashboard</h3>
        <p>
          RoadSense dashboard data is protected. Use your operator account to access live traffic,
          parking, and road damage controls.
        </p>
        <div className="welcome-actions">
          <button className="primary-button compact-button" onClick={onGoLogin}>
            <LogIn size={16} />
            Login
          </button>
          <button className="secondary-button compact-button" onClick={onGoSignup}>
            <UserCircle size={16} />
            Sign Up
          </button>
        </div>
      </div>
      <section className="account-card profile-action-card">
        <div className="account-title">
          <ShieldCheck size={18} />
          <div>
            <h3>Protected Dashboard</h3>
            <p>Authentication is required before city data loads.</p>
          </div>
        </div>
        <div className="prime-features">
          <span>Traffic Management</span>
          <span>Smart Parking</span>
          <span>Road Damage Detection</span>
        </div>
        <p className="mini-warning">No dashboard API calls are started until login is completed.</p>
      </section>
    </section>
  );
}

function HomePage({ auth, onGoDashboard, onGoSignup, onGoSubscription, onLogout, loading, dashboardLabel }) {
  const isLoggedIn = Boolean(auth?.user);
  const profileRows = isLoggedIn
    ? [
        ["Name", profileValue(auth.user.name)],
        ["Email", profileValue(auth.user.email)],
        ["Role", titleValue(auth.user.role || "operator")],
        ["Plan", `${titleValue(auth.user.plan || "free")} plan`],
        ["Subscription", titleValue(auth.user.subscription_status || "inactive")],
        ["Session", "Logged in"],
      ]
    : [];

  return (
    <>
      {isLoggedIn ? (
        <section className="page-grid welcome-grid home-welcome">
          <div className="page-card welcome-hero-card">
            <span className="page-kicker">Welcome</span>
            <h3>Welcome, {profileValue(auth.user.name, "Operator")}</h3>
            <p>
              Your RoadSense operator profile is active. Continue from here to monitor routes,
              parking slots, and road damage data.
            </p>
            <div className="welcome-actions">
              <button className="primary-button compact-button" onClick={onGoDashboard}>
                <Route size={16} />
                Open Dashboard
              </button>
              <button className="secondary-button compact-button" onClick={onGoSubscription}>
                <Crown size={16} />
                View Prime
              </button>
            </div>
          </div>
          <div className="side-stack">
            <DataPanel
              title="Profile Details"
              rows={profileRows}
              note="This profile is used for dashboard access and Prime subscription checkout."
            />
            <section className="account-card profile-action-card">
              <div className="account-title">
                <UserCircle size={18} />
                <div>
                  <h3>{auth.user.name}</h3>
                  <p>{auth.user.email}</p>
                </div>
              </div>
              <div className="account-badge">Authenticated operator</div>
              <button className="secondary-button" onClick={onLogout} disabled={loading}>
                <LogOut size={16} />
                Log out
              </button>
            </section>
          </div>
        </section>
      ) : null}

      <section className="home-hero">
        <div className="home-copy">
          <span className="home-kicker">Smart city operations platform</span>
          <h1>Manage traffic, parking, and road damage from one city command center</h1>
          <p>
            A professional operations website for Indian city routes with live maps, satellite views,
            manual locality search, and Razorpay Prime subscription.
          </p>
          <div className="home-actions">
            <button className="primary-button compact-button" onClick={onGoDashboard}>
              {dashboardLabel}
            </button>
            <button className="secondary-button compact-button" onClick={isLoggedIn ? onGoSubscription : onGoSignup}>
              {isLoggedIn ? "View Prime" : "Sign Up Free"}
            </button>
          </div>
        </div>
        <div className="home-visual" aria-label="Smart city platform preview">
          <div className="preview-top">
            <span>Live Route</span>
            <strong>Chennai to Bengaluru</strong>
          </div>
          <div className="preview-map">
            <span className="route-line route-blue" />
            <span className="route-line route-amber" />
            <span className="route-line route-red" />
            <i className="preview-pin start-pin" />
            <i className="preview-pin end-pin" />
          </div>
          <div className="preview-grid">
            <div><span>Congestion</span><strong>42%</strong></div>
            <div><span>Vacant Slots</span><strong>128</strong></div>
            <div><span>Road Alerts</span><strong>5</strong></div>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="section-title">
          <span>Platform</span>
          <h2>Built like a real city operations product</h2>
        </div>
        <div className="feature-grid">
          <article>
            <Route size={22} />
            <h3>Traffic Management</h3>
            <p>Route maps with red, yellow, and blue traffic sections for fast decisions.</p>
          </article>
          <article>
            <ParkingCircle size={22} />
            <h3>Smart Parking</h3>
            <p>Parking points, available slots, occupied slots, and real map markers.</p>
          </article>
          <article>
            <Construction size={22} />
            <h3>Road Damage Detection</h3>
            <p>Map-based damage points, severity, affected area, and maintenance action.</p>
          </article>
        </div>
      </section>

      <section className="cta-band">
        <div>
          <span>Prime</span>
          <h2>Upgrade with Razorpay subscription</h2>
          <p>Use Prime checkout for subscription-ready hackathon presentation flow.</p>
        </div>
        <button className="primary-button compact-button" onClick={onGoSubscription}>
          View Subscription
        </button>
      </section>
    </>
  );
}

function SiteHeader({ activePage, auth }) {
  const navItems = [
    ["home", "Home"],
    ["dashboard", "Dashboard"],
    ["subscription", "Subscription"],
  ];

  return (
    <header className="site-header">
      <button className="site-logo" onClick={() => navigateToPage("home")} aria-label="RoadSense home">
        <span><Building2 size={22} /></span>
        <strong>RoadSense</strong>
      </button>
      <nav className="site-nav" aria-label="Main navigation">
        {navItems.map(([page, label]) => (
          <button
            className={activePage === page ? "active" : ""}
            key={page}
            onClick={() => navigateToPage(page)}
          >
            {label}
          </button>
        ))}
      </nav>
      <div className="site-actions">
        <button
          className={
            (auth?.user && activePage === "home") || activePage === "login"
              ? "active text-nav-button"
              : "text-nav-button"
          }
          onClick={() => navigateToPage(auth?.user ? "home" : "login")}
        >
          {auth?.user ? "Profile" : "Login"}
        </button>
        {auth?.user ? (
          <button className="nav-cta" onClick={() => navigateToPage("dashboard")}>
            Dashboard
          </button>
        ) : (
          <button className="nav-cta" onClick={() => navigateToPage("signup")}>
            Sign Up
          </button>
        )}
      </div>
    </header>
  );
}

function App() {
  const backendUrl = getInitialBackendUrl();
  const [auth, setAuth] = useState(getStoredAuth);
  const [authLoading, setAuthLoading] = useState(false);
  const [locations, setLocations] = useState(FALLBACK_LOCATIONS);
  const [startLocation, setStartLocation] = useState("Chennai");
  const [endLocation, setEndLocation] = useState("Bengaluru");
  const [parkingCity, setParkingCity] = useState("Bengaluru");
  const [parkingLimit, setParkingLimit] = useState(160);
  const [locationMode, setLocationMode] = useState("manual");
  const [customStart, setCustomStart] = useState("MG Road, Bengaluru");
  const [customEnd, setCustomEnd] = useState("Indiranagar, Bengaluru");
  const [parkingMode, setParkingMode] = useState("manual");
  const [customParkingCity, setCustomParkingCity] = useState("Commercial Street, Bengaluru");
  const [surveyMode, setSurveyMode] = useState("Routine survey");
  const [surveyPriority, setSurveyPriority] = useState("Priority corridors");
  const [mapStyle, setMapStyle] = useState("satellite");
  const [activePage, setActivePage] = useState(pageFromHash);
  const [activeTab, setActiveTab] = useState("overview");
  const [refreshIntervalSeconds, setRefreshIntervalSeconds] = useState(90);
  const [parkingData, setParkingData] = useState(null);
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const selectedStart = locationMode === "manual" ? uniqueLocationName(customStart, "Chennai") : startLocation;
  const selectedEnd = locationMode === "manual" ? uniqueLocationName(customEnd, "Bengaluru") : endLocation;
  const selectedParkingCity =
    parkingMode === "manual" ? uniqueLocationName(customParkingCity, "Bengaluru") : parkingCity;
  const isAuthenticated = Boolean(auth?.user);
  const isPrime = auth?.user?.plan === "prime";
  const startSuggestions = useIndiaLocationSuggestions(
    backendUrl,
    customStart,
    activePage === "dashboard" && isAuthenticated && locationMode === "manual",
  );
  const endSuggestions = useIndiaLocationSuggestions(
    backendUrl,
    customEnd,
    activePage === "dashboard" && isAuthenticated && locationMode === "manual",
  );
  const parkingSuggestions = useIndiaLocationSuggestions(
    backendUrl,
    customParkingCity,
    activePage === "dashboard" && isAuthenticated && parkingMode === "manual",
  );

  useEffect(() => {
    const syncPage = () => setActivePage(pageFromHash());
    if (!window.location.hash) {
      navigateToPage("home");
    }
    window.addEventListener("hashchange", syncPage);
    syncPage();
    return () => window.removeEventListener("hashchange", syncPage);
  }, []);

  useEffect(() => {
    if (activePage === "dashboard") {
      setActiveTab("overview");
    }
  }, [activePage]);

  useEffect(() => {
    let cancelled = false;
    async function validateSession() {
      if (!auth?.token) return;
      try {
        const response = await getMe(backendUrl, auth.token);
        if (!cancelled) {
          const nextAuth = { token: auth.token, user: response.user };
          setAuth(nextAuth);
          saveStoredAuth(nextAuth);
        }
      } catch {
        if (!cancelled) {
          clearStoredAuth();
          setAuth(null);
        }
      }
    }
    validateSession();
    return () => {
      cancelled = true;
    };
  }, [backendUrl, auth?.token]);

  async function handleLogin(payload) {
    setAuthLoading(true);
    try {
      const response = await login(backendUrl, payload);
      const nextAuth = { token: response.token, user: response.user };
      setAuth(nextAuth);
      saveStoredAuth(nextAuth);
      navigateToPage("home");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleSignup(payload) {
    setAuthLoading(true);
    try {
      const response = await signup(backendUrl, payload);
      const nextAuth = { token: response.token, user: response.user };
      setAuth(nextAuth);
      saveStoredAuth(nextAuth);
      navigateToPage("home");
    } finally {
      setAuthLoading(false);
    }
  }

  function handleAuthUpdate(nextAuth) {
    setAuth(nextAuth);
    saveStoredAuth(nextAuth);
  }

  async function handleLogout() {
    setAuthLoading(true);
    try {
      if (auth?.token) {
        await logout(backendUrl, auth.token);
      }
    } catch {
      // Token is stateless; local logout is enough if the network request fails.
    } finally {
      clearStoredAuth();
      setAuth(null);
      setAuthLoading(false);
      navigateToPage("login");
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function loadLocations() {
      try {
        const response = await getIndiaLocations(backendUrl);
        if (!cancelled) {
          setLocations(response.locations?.length ? response.locations : FALLBACK_LOCATIONS);
        }
      } catch {
        if (!cancelled) setLocations(FALLBACK_LOCATIONS);
      }
    }
    loadLocations();
    return () => {
      cancelled = true;
    };
  }, [backendUrl]);

  const loadOperations = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const [parkingResponse, routeResponse] = await Promise.all([
        getParking(backendUrl, {
          provider: "india",
          city: selectedParkingCity,
          limit: parkingLimit,
        }),
        selectedStart.toLowerCase() !== selectedEnd.toLowerCase()
          ? getTrafficRoute(backendUrl, selectedStart, selectedEnd)
          : Promise.resolve(null),
      ]);

      setParkingData(parkingResponse);
      setRoute(routeResponse);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [backendUrl, isAuthenticated, selectedStart, selectedEnd, selectedParkingCity, parkingLimit]);

  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    loadOperations();
  }, [isAuthenticated, loadOperations]);

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    if (!refreshIntervalSeconds) return undefined;
    const id = window.setInterval(loadOperations, refreshIntervalSeconds * 1000);
    return () => window.clearInterval(id);
  }, [isAuthenticated, refreshIntervalSeconds, loadOperations]);

  const damageReport = useMemo(
    () => routeDamageReport(route, selectedStart, selectedEnd, surveyMode),
    [route, selectedStart, selectedEnd, surveyMode],
  );

  const trafficSummary = route?.summary || {};
  const parking = parkingData || {};

  const metricCards = useMemo(() => {
    if (activeTab === "traffic") {
      return [
        {
          icon: Route,
          label: "Route Mode",
          value: route?.mode || "Route",
          note: `${selectedStart} to ${selectedEnd}`,
          tone: "blue",
        },
        {
          icon: Navigation,
          label: "Distance",
          value: `${trafficSummary.distance_km || 0} km`,
          note: "selected route",
          tone: "teal",
        },
        {
          icon: Activity,
          label: "Congestion",
          value: `${trafficSummary.congestion_score || 0}%`,
          note: `${trafficSummary.moderate_segments || 0} moderate sections`,
          tone: "amber",
        },
        {
          icon: AlertTriangle,
          label: "Heavy Traffic",
          value: trafficSummary.heavy_segments || 0,
          note: "red route sections",
          tone: "red",
        },
      ];
    }

    if (activeTab === "parking") {
      return [
        {
          icon: ParkingCircle,
          label: "Parking Location",
          value: parking.city || selectedParkingCity,
          note: "selected area",
          tone: "blue",
        },
        {
          icon: Building2,
          label: "Parking Points",
          value: parking.total_facilities || 0,
          note: "mapped locations",
          tone: "teal",
        },
        {
          icon: ShieldCheck,
          label: "Vacant Slots",
          value: parking.vacant_spaces || 0,
          note: `${parking.availability_rate || 0}% availability`,
          tone: "amber",
        },
        {
          icon: AlertTriangle,
          label: "Occupied Slots",
          value: parking.occupied_spaces || 0,
          note: `${parking.occupancy_rate || 0}% occupied`,
          tone: "red",
        },
      ];
    }

    if (activeTab === "damage") {
      return [
        {
          icon: Construction,
          label: "Damage Score",
          value: damageReport.score,
          note: damageReport.severity,
          tone: "blue",
        },
        {
          icon: AlertTriangle,
          label: "Damage Points",
          value: damageReport.detection_count,
          note: surveyMode,
          tone: "teal",
        },
        {
          icon: Activity,
          label: "Affected Area",
          value: `${damageReport.damage_area_percent}%`,
          note: "estimated route",
          tone: "amber",
        },
        {
          icon: Route,
          label: "Road Segment",
          value: `${trafficSummary.distance_km || 0} km`,
          note: `${selectedStart} to ${selectedEnd}`,
          tone: "red",
        },
      ];
    }

    return [
      {
        icon: Navigation,
        label: "Traffic Congestion",
        value: `${trafficSummary.congestion_score || 0}%`,
        note: `${trafficSummary.heavy_segments || 0} heavy sections`,
        tone: "blue",
      },
      {
        icon: ParkingCircle,
        label: "Parking Available",
        value: `${parking.availability_rate || 0}%`,
        note: `${parking.vacant_spaces || 0} vacant slots`,
        tone: "teal",
      },
      {
        icon: Construction,
        label: "Road Damage Points",
        value: damageReport.detection_count,
        note: `${damageReport.severity} severity`,
        tone: "amber",
      },
      {
        icon: ShieldCheck,
        label: "Route Distance",
        value: `${trafficSummary.distance_km || 0} km`,
        note: `${selectedStart} to ${selectedEnd}`,
        tone: "red",
      },
    ];
  }, [
    activeTab,
    damageReport,
    parking,
    route,
    selectedEnd,
    selectedParkingCity,
    selectedStart,
    surveyMode,
    trafficSummary,
  ]);

  const operationPanels = (
    <div className="side-stack">
      <DataPanel
        title="Traffic Management"
        rows={[
          ["Starting location", selectedStart],
          ["Destination", selectedEnd],
          ["Distance", `${trafficSummary.distance_km || "-"} km`],
          ["Travel time", `${trafficSummary.travel_time_min || "-"} min`],
          ["Heavy sections", trafficSummary.heavy_segments || 0],
        ]}
        note="Red = heavy, yellow = moderate."
      />
      <DataPanel
        title="Smart Parking"
        rows={[
          ["Parking location", parking.city || selectedParkingCity],
          ["Parking points", parking.total_facilities || 0],
          ["Vacant slots", parking.vacant_spaces || 0],
          ["Occupied slots", parking.occupied_spaces || 0],
          ["Availability", `${parking.availability_rate || 0}%`],
        ]}
        note="Green = available, red = full."
      />
      <DataPanel
        title="Road Damage Detection"
        rows={[
          ["Starting location", selectedStart],
          ["Destination", selectedEnd],
          ["Damage points", damageReport.detection_count],
          ["Severity", damageReport.severity],
          ["Affected area", `${damageReport.damage_area_percent}%`],
        ]}
        note="Map-based survey only."
      />
    </div>
  );

  const isDashboardRoute = activePage === "dashboard";
  const isDashboardPage = isDashboardRoute && isAuthenticated;

  return (
    <div className="site-shell">
      <SiteHeader activePage={activePage} auth={auth} />
      <div className={`app-shell ${isDashboardPage ? "" : "app-shell-full"}`}>
        {isDashboardPage ? (
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-icon">
              <Building2 size={24} />
            </div>
            <div>
              <h1>RoadSense</h1>
              <p>India operations dashboard</p>
            </div>
          </div>

          <section className="control-section">
            <div className="control-heading">
              <Route size={17} />
              <div>
                <h3>Traffic Route</h3>
                <p>Origin, destination, and gully-level routing</p>
              </div>
            </div>
            <label>
              Search mode
              <select value={locationMode} onChange={(event) => setLocationMode(event.target.value)}>
                <option value="manual">Map search</option>
                <option value="city">City quick list</option>
              </select>
            </label>
            <label>
              Origin
              {locationMode === "manual" ? (
                <>
                  <input
                    value={customStart}
                    onChange={(event) => setCustomStart(event.target.value)}
                    list="start-location-suggestions"
                    autoComplete="off"
                    placeholder="Village, road, gully, district"
                  />
                  <LocationDatalist id="start-location-suggestions" suggestions={startSuggestions} />
                </>
              ) : (
                <select value={startLocation} onChange={(event) => setStartLocation(event.target.value)}>
                  {locations.map((location) => (
                    <option value={location.name} key={`${location.name}-${location.state}`}>
                      {locationLabel(location)}
                    </option>
                  ))}
                </select>
              )}
            </label>
            <label>
              Destination
              {locationMode === "manual" ? (
                <>
                  <input
                    value={customEnd}
                    onChange={(event) => setCustomEnd(event.target.value)}
                    list="end-location-suggestions"
                    autoComplete="off"
                    placeholder="Village, road, gully, district"
                  />
                  <LocationDatalist id="end-location-suggestions" suggestions={endSuggestions} />
                </>
              ) : (
                <select value={endLocation} onChange={(event) => setEndLocation(event.target.value)}>
                  {locations.map((location) => (
                    <option value={location.name} key={`${location.name}-${location.state}`}>
                      {locationLabel(location)}
                    </option>
                  ))}
                </select>
              )}
            </label>
          </section>

          <section className="control-section">
            <div className="control-heading">
              <ParkingCircle size={17} />
              <div>
                <h3>Smart Parking</h3>
                <p>Nearby parking points and slot availability</p>
              </div>
            </div>
            <label>
              Parking search
              <select value={parkingMode} onChange={(event) => setParkingMode(event.target.value)}>
                <option value="manual">Map search</option>
                <option value="city">City quick list</option>
              </select>
            </label>
            <label>
              Parking area
              {parkingMode === "manual" ? (
                <>
                  <input
                    value={customParkingCity}
                    onChange={(event) => setCustomParkingCity(event.target.value)}
                    list="parking-location-suggestions"
                    autoComplete="off"
                    placeholder="Village, road, gully, locality"
                  />
                  <LocationDatalist id="parking-location-suggestions" suggestions={parkingSuggestions} />
                </>
              ) : (
                <select value={parkingCity} onChange={(event) => setParkingCity(event.target.value)}>
                  {locations.map((location) => (
                    <option value={location.name} key={`parking-${location.name}-${location.state}`}>
                      {locationLabel(location)}
                    </option>
                  ))}
                </select>
              )}
            </label>
            <label>
              Parking coverage
              <input
                type="range"
                min="40"
                max={isPrime ? "800" : "300"}
                step="20"
                value={parkingLimit}
                onChange={(event) => setParkingLimit(Number(event.target.value))}
              />
              <span className="range-value">
                {parkingLimit} mapped points {isPrime ? "with Prime expansion" : ""}
              </span>
            </label>
          </section>

          <section className="control-section">
            <div className="control-heading">
              <Construction size={17} />
              <div>
                <h3>Road Survey</h3>
                <p>Road damage scenario and inspection priority</p>
              </div>
            </div>
            <label>
              Survey scenario
              <select value={surveyMode} onChange={(event) => setSurveyMode(event.target.value)}>
                <option>Routine survey</option>
                <option>After heavy rain</option>
                <option>Citizen complaints</option>
                <option>Construction zone</option>
              </select>
            </label>
            <label>
              Inspection focus
              <select value={surveyPriority} onChange={(event) => setSurveyPriority(event.target.value)}>
                <option>Priority corridors</option>
                <option>School and hospital roads</option>
                <option>Market and bus-stop areas</option>
                <option>Residential gullies</option>
              </select>
            </label>
          </section>

          <section className="control-section">
            <div className="control-heading">
              <Activity size={17} />
              <div>
                <h3>Live Map Feed</h3>
                <p>Map layer and auto-refresh cadence</p>
              </div>
            </div>
            <label>
              Map layer
              <select value={mapStyle} onChange={(event) => setMapStyle(event.target.value)}>
                <option value="satellite">Satellite</option>
                <option value="street">Street</option>
                <option value="light">Light</option>
              </select>
            </label>
            <label>
              Refresh cadence
              <select
                value={refreshIntervalSeconds}
                onChange={(event) => setRefreshIntervalSeconds(Number(event.target.value))}
              >
                <option value={0}>Manual refresh</option>
                {isPrime ? <option value={15}>Every 15 seconds</option> : null}
                <option value={30}>Every 30 seconds</option>
                <option value={60}>Every 1 minute</option>
                <option value={90}>Every 90 seconds</option>
                <option value={300}>Every 5 minutes</option>
              </select>
            </label>
            <button className="primary-button" onClick={loadOperations} disabled={loading}>
              <RefreshCcw size={16} />
              {loading ? "Refreshing..." : "Refresh live data"}
            </button>
          </section>

        </aside>
        ) : null}

        <main className="main-content">
          {isDashboardPage ? (
            <header className="topbar">
              <div>
                <h2>Operations Dashboard</h2>
                <p>Traffic, parking, and road damage intelligence for Indian city routes.</p>
              </div>
            </header>
          ) : null}

        {isDashboardPage && error ? (
          <div className="error-banner">
            <AlertTriangle size={18} />
            {error}
          </div>
        ) : null}

        {activePage === "home" ? (
          <HomePage
            auth={auth}
            onGoDashboard={() => navigateToPage(isAuthenticated ? "dashboard" : "login")}
            onGoSignup={() => navigateToPage("signup")}
            onGoSubscription={() => navigateToPage("subscription")}
            onLogout={handleLogout}
            loading={authLoading}
            dashboardLabel={isAuthenticated ? "Open Dashboard" : "Login to Dashboard"}
          />
        ) : null}

        {isDashboardRoute && !isAuthenticated ? (
          <AccessRequiredPage
            onGoLogin={() => navigateToPage("login")}
            onGoSignup={() => navigateToPage("signup")}
          />
        ) : null}

        {isDashboardPage ? (
          <>
            <section className="metric-grid">
              {metricCards.map((card) => (
                <MetricCard
                  icon={card.icon}
                  key={card.label}
                  label={card.label}
                  value={card.value}
                  note={card.note}
                  tone={card.tone}
                />
              ))}
            </section>

            <nav className="tabs">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    className={activeTab === tab.id ? "active" : ""}
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    <Icon size={17} />
                    {tab.label}
                  </button>
                );
              })}
            </nav>

            <PrimeInsightsPanel
              isPrime={isPrime}
              trafficSummary={trafficSummary}
              parking={parking}
              damageReport={damageReport}
              selectedStart={selectedStart}
              selectedEnd={selectedEnd}
              selectedParkingCity={selectedParkingCity}
              onGoSubscription={() => navigateToPage("subscription")}
            />

            {activeTab === "overview" ? (
              <section className="workspace-grid">
                <div className="map-card">
                  <div className="section-header">
                    <div>
                      <span>India Route Traffic Map</span>
                      <h3>{selectedStart} to {selectedEnd}</h3>
                    </div>
                    <Legend type="traffic" />
                  </div>
                  <MapPanel type="traffic" route={route} mapStyle={mapStyle} />
                </div>
                {operationPanels}
              </section>
            ) : null}

            {activeTab === "traffic" ? (
              <section className="workspace-grid">
                <div className="map-card">
                  <div className="section-header">
                    <div>
                      <span>Route Traffic Map</span>
                      <h3>{selectedStart} to {selectedEnd}</h3>
                    </div>
                    <Legend type="traffic" />
                  </div>
                  <MapPanel type="traffic" route={route} mapStyle={mapStyle} />
                </div>
                <div className="side-stack">
                  <DataPanel
                    title="Traffic Management"
                    rows={[
                      ["Starting location", selectedStart],
                      ["Destination", selectedEnd],
                      ["Distance", `${trafficSummary.distance_km || "-"} km`],
                      ["Travel time", `${trafficSummary.travel_time_min || "-"} min`],
                      ["Congestion", `${trafficSummary.congestion_score || 0}%`],
                      ["Moderate sections", trafficSummary.moderate_segments || 0],
                      ["Heavy sections", trafficSummary.heavy_segments || 0],
                    ]}
                    note="Red = heavy, yellow = moderate."
                  />
                  <SegmentBars summary={trafficSummary} />
                </div>
              </section>
            ) : null}

            {activeTab === "parking" ? (
              <>
                <section className="workspace-grid">
                  <div className="map-card">
                    <div className="section-header">
                      <div>
                        <span>Parking Map</span>
                        <h3>{parking.city || selectedParkingCity}</h3>
                      </div>
                      <Legend type="parking" />
                    </div>
                    <MapPanel type="parking" parking={parking} mapStyle={mapStyle} />
                  </div>
                  <div className="side-stack">
                    <DataPanel
                      title="Smart Parking"
                      rows={[
                        ["Parking location", parking.city || selectedParkingCity],
                        ["Starting location", selectedStart],
                        ["Destination", selectedEnd],
                        ["Parking points", parking.total_facilities || 0],
                        ["Vacant slots", parking.vacant_spaces || 0],
                        ["Occupied slots", parking.occupied_spaces || 0],
                        ["Availability", `${parking.availability_rate || 0}%`],
                      ]}
                      note="Green = available, red = full."
                    />
                  </div>
                </section>
                <ParkingTable stalls={parking.stalls} />
              </>
            ) : null}

            {activeTab === "damage" ? (
              <>
                <section className="workspace-grid">
                  <div className="map-card">
                    <div className="section-header">
                      <div>
                        <span>Damaged Road Area Map</span>
                        <h3>{selectedStart} to {selectedEnd}</h3>
                      </div>
                      <Legend type="damage" />
                    </div>
                    <MapPanel type="damage" route={route} damageReport={damageReport} mapStyle={mapStyle} />
                  </div>
                  <div className="side-stack">
                    <DataPanel
                      title="Road Damage Detection"
                      rows={[
                        ["Starting location", selectedStart],
                        ["Destination", selectedEnd],
                        ["Survey mode", surveyMode],
                        ["Inspection focus", surveyPriority],
                        ["Damage points", damageReport.detection_count],
                        ["Severity", damageReport.severity],
                        ["Affected area", `${damageReport.damage_area_percent}%`],
                        ["Action", damageReport.recommendation],
                      ]}
                      note="Map-based survey only."
                    />
                  </div>
                </section>
                <DamageTable detections={damageReport.detections} />
              </>
            ) : null}
          </>
        ) : null}

        {activePage === "login" ? (
          <LoginPage
            auth={auth}
            onLogin={handleLogin}
            onLogout={handleLogout}
            loading={authLoading}
            onGoSignup={() => navigateToPage("signup")}
            onGoSubscription={() => navigateToPage("subscription")}
          />
        ) : null}

        {activePage === "signup" ? (
          <SignupPage
            auth={auth}
            onSignup={handleSignup}
            loading={authLoading}
            onGoLogin={() => navigateToPage("login")}
            onGoSubscription={() => navigateToPage("subscription")}
          />
        ) : null}

        {activePage === "subscription" ? (
          <SubscriptionPage
            backendUrl={backendUrl}
            auth={auth}
            onGoLogin={() => navigateToPage("login")}
            onAuthUpdate={handleAuthUpdate}
          />
        ) : null}
      </main>

      {isDashboardPage && loading ? (
        <div className="loading-overlay">
          <div />
          Loading city operations data
        </div>
      ) : null}
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
