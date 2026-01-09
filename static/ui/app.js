const CONTRACTS = [
  { key: "accounts", label: "Accounts", url: "/ui/contracts/accounts/" },
  { key: "universities", label: "Universities", url: "/ui/contracts/universities/" },
  { key: "cases", label: "Cases", url: "/ui/contracts/cases/" },
  { key: "appointments", label: "Appointments", url: "/ui/contracts/appointments/" },
  { key: "evaluations", label: "Evaluations", url: "/ui/contracts/evaluations/" },
  { key: "attachments", label: "Attachments", url: "/ui/contracts/attachments/" },
  { key: "messaging", label: "Messaging", url: "/ui/contracts/messaging/" },
  { key: "notifications", label: "Notifications", url: "/ui/contracts/notifications/" },
  { key: "reports", label: "Reports", url: "/ui/contracts/reports/" },
  { key: "community", label: "Community", url: "/ui/contracts/community/" },
  { key: "ai", label: "AI Diagnosis", url: "/ui/contracts/ai/" },
  { key: "audit", label: "Audit", url: "/ui/contracts/audit/" },
  { key: "backup", label: "Backup", url: "/ui/contracts/backup/" },
  { key: "support", label: "Support", url: "/ui/contracts/support/" },
];

const DEFAULT_BASE_URL = "https://medismile1-production.up.railway.app";
const THEME_KEY = "medismile-ui-theme";
const BASE_URL_KEY = "medismile-ui-base-url";

const dom = {
  nav: document.getElementById("section-nav"),
  content: document.getElementById("content"),
  overview: document.getElementById("overview"),
  themeToggle: document.getElementById("theme-toggle"),
  baseUrlInput: document.getElementById("base-url"),
  tokenInput: document.getElementById("auth-token"),
  modal: document.getElementById("detail-modal"),
  modalGroup: document.getElementById("modal-group"),
  modalTitle: document.getElementById("modal-title"),
  modalPath: document.getElementById("modal-path"),
  modalRole: document.getElementById("modal-role"),
  modalScope: document.getElementById("modal-scope"),
  modalEffect: document.getElementById("modal-effect"),
  modalRequest: document.getElementById("modal-request"),
  modalResponse: document.getElementById("modal-response"),
  modalRules: document.getElementById("modal-rules"),
  modalMethod: document.getElementById("modal-method"),
  modalUrl: document.getElementById("modal-url"),
  pathParams: document.getElementById("path-params"),
  queryParams: document.getElementById("query-params"),
  modalBody: document.getElementById("modal-body"),
  runTest: document.getElementById("run-test"),
  testStatus: document.getElementById("test-status"),
  testOutput: document.getElementById("test-output"),
};

const state = {
  contracts: {},
  endpointMap: new Map(),
  activeEndpointId: null,
};

const METHOD_CLASS = {
  GET: "method-get",
  POST: "method-post",
  PATCH: "method-patch",
  DELETE: "method-delete",
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatJson(value) {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch (error) {
    return String(value);
  }
}

function extractResponse(details) {
  if (!details) return null;
  if (details.response !== undefined) return details.response;
  if (details.returns !== undefined) return details.returns;
  const composite = {};
  if (details.response_on_accept !== undefined) {
    composite.response_on_accept = details.response_on_accept;
  }
  if (details.response_on_reject !== undefined) {
    composite.response_on_reject = details.response_on_reject;
  }
  if (details.result !== undefined) {
    composite.result = details.result;
  }
  if (details.note !== undefined) {
    composite.note = details.note;
  }
  return Object.keys(composite).length ? composite : null;
}

function formatValue(value) {
  if (value === undefined || value === null || value === "") return "None";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getCookie(name) {
  const pattern = new RegExp(`(?:^|; )${name.replace(/[-.+*]/g, "\\$&")}=([^;]*)`);
  const match = document.cookie.match(pattern);
  return match ? decodeURIComponent(match[1]) : "";
}

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && meta.content) return meta.content;
  return getCookie("csrftoken");
}

function isSameOrigin(url) {
  try {
    const target = new URL(url, window.location.href);
    return target.origin === window.location.origin;
  } catch (error) {
    return false;
  }
}

function normalizeBaseUrl(value) {
  const raw = value.trim();
  if (!raw) return DEFAULT_BASE_URL;
  if (/^https?:\/\//i.test(raw)) return raw.replace(/\/$/, "");
  if (/^(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$/i.test(raw)) {
    return `http://${raw}`.replace(/\/$/, "");
  }
  return `https://${raw}`.replace(/\/$/, "");
}

function getBaseUrl() {
  return normalizeBaseUrl(dom.baseUrlInput.value || DEFAULT_BASE_URL);
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
  dom.themeToggle.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";
}

function initTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored) {
    setTheme(stored);
    return;
  }
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  setTheme(prefersDark ? "dark" : "light");
}

function initBaseUrl() {
  const stored = localStorage.getItem(BASE_URL_KEY);
  dom.baseUrlInput.value = normalizeBaseUrl(stored || DEFAULT_BASE_URL);
  dom.baseUrlInput.addEventListener("change", () => {
    const normalized = normalizeBaseUrl(dom.baseUrlInput.value);
    dom.baseUrlInput.value = normalized;
    if (normalized) localStorage.setItem(BASE_URL_KEY, normalized);
    updateModalUrl();
  });
}

function flattenEndpoints(endpoints) {
  const items = [];
  Object.entries(endpoints || {}).forEach(([group, groupEndpoints]) => {
    Object.entries(groupEndpoints || {}).forEach(([signature, details]) => {
      const parts = signature.trim().split(" ");
      const method = (parts.shift() || "GET").toUpperCase();
      const path = parts.join(" ");
      items.push({ group, signature, method, path, details: details || {} });
    });
  });
  return items;
}

function resolveEndpointPath(endpoint) {
  const rawPath = endpoint.path || "";
  if (/^https?:\/\//i.test(rawPath)) return rawPath;
  if (rawPath.startsWith("/")) return rawPath;
  const baseUrl = endpoint.contract?.service?.base_url || "";
  if (!baseUrl) return `/${rawPath}`;
  const basePath = baseUrl.startsWith("/") ? baseUrl : `/${baseUrl}`;
  return `${basePath}/${rawPath}`.replace(/\/{2,}/g, "/");
}

function parsePathParams(path) {
  const params = [];
  const regex = /<([^>]+)>/g;
  let match;
  while ((match = regex.exec(path)) !== null) {
    const token = match[0];
    const rawName = match[1];
    const name = rawName.includes(":") ? rawName.split(":").pop() : rawName;
    params.push({ token, name });
  }
  return params;
}

function extractQueryDefinitions(details) {
  if (!details) return [];
  const query = details.query;
  if (Array.isArray(query)) {
    return query.map((name) => ({
      name: String(name).replace(/\?$/, ""),
      hint: "",
    }));
  }
  if (query && typeof query === "object") {
    return Object.entries(query).map(([name, hint]) => ({
      name: String(name).replace(/\?$/, ""),
      hint: formatValue(hint),
    }));
  }
  return [];
}

function renderPathParams(path) {
  dom.pathParams.innerHTML = "";
  const params = parsePathParams(path);
  if (!params.length) {
    dom.pathParams.classList.add("is-empty");
    return;
  }
  dom.pathParams.classList.remove("is-empty");
  params.forEach((param) => {
    const label = el("label", "field");
    label.appendChild(el("span", null, `Path ${param.name}`));
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = param.name;
    input.dataset.placeholder = param.token;
    label.appendChild(input);
    dom.pathParams.appendChild(label);
  });
}

function renderQueryParams(definitions) {
  dom.queryParams.innerHTML = "";
  if (!definitions.length) {
    dom.queryParams.classList.add("is-empty");
    return;
  }
  dom.queryParams.classList.remove("is-empty");
  definitions.forEach((param) => {
    const label = el("label", "field");
    label.appendChild(el("span", null, `Query ${param.name}`));
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = param.hint || param.name;
    input.dataset.key = param.name;
    label.appendChild(input);
    dom.queryParams.appendChild(label);
  });
}

function collectPathParams() {
  return Array.from(dom.pathParams.querySelectorAll("input")).map((input) => ({
    placeholder: input.dataset.placeholder,
    value: input.value.trim(),
  }));
}

function collectQueryParams() {
  return Array.from(dom.queryParams.querySelectorAll("input"))
    .map((input) => [input.dataset.key, input.value.trim()])
    .filter(([, value]) => value);
}

function applyPathParams(path, values) {
  let resolved = path;
  values.forEach(({ placeholder, value }) => {
    if (value) {
      resolved = resolved.replace(placeholder, encodeURIComponent(value));
    }
  });
  return resolved;
}

function appendQueryParams(url, params) {
  if (!params.length) return url;
  const query = new URLSearchParams(params).toString();
  return url.includes("?") ? `${url}&${query}` : `${url}?${query}`;
}

function buildEndpointUrl(endpoint, queryParams) {
  const rawPath = resolveEndpointPath(endpoint);
  const resolvedPath = applyPathParams(rawPath, collectPathParams());
  if (/^https?:\/\//i.test(rawPath)) {
    return appendQueryParams(resolvedPath, queryParams);
  }
  return appendQueryParams(`${getBaseUrl()}${resolvedPath}`, queryParams);
}

function updateModalUrl() {
  const endpoint = state.endpointMap.get(state.activeEndpointId);
  if (!endpoint) return;
  dom.modalUrl.value = buildEndpointUrl(endpoint, collectQueryParams());
}

function renderOverview(counts) {
  dom.overview.innerHTML = "";
  const cards = [
    { title: "Services", value: counts.services, note: "Connected contract files" },
    { title: "Endpoints", value: counts.endpoints, note: "Mapped routes and actions" },
    { title: "Roles", value: counts.roles, note: "Role based access notes" },
  ];
  cards.forEach((card) => {
    const node = el("div", "overview-card");
    node.appendChild(el("h3", null, `${card.title}: ${card.value}`));
    node.appendChild(el("p", null, card.note));
    dom.overview.appendChild(node);
  });
}

function buildNav(contracts) {
  dom.nav.innerHTML = "";
  contracts.forEach(({ key, label, endpoints }) => {
    const link = el("a", "section-link", "");
    link.href = `#${key}`;
    const name = el("span", null, label);
    const count = el("small", null, `${endpoints} endpoints`);
    link.appendChild(name);
    link.appendChild(count);
    dom.nav.appendChild(link);
  });
}

function buildInfoCard(title, items) {
  const card = el("div", "info-card");
  card.appendChild(el("h4", null, title));
  const list = el("ul");
  if (!items.length) {
    list.appendChild(el("li", null, "None"));
  } else {
    items.forEach((item) => {
      list.appendChild(el("li", null, item));
    });
  }
  card.appendChild(list);
  return card;
}

function buildEndpointCard(endpoint, index) {
  const card = el("article", "endpoint-card");
  card.style.animationDelay = `${index * 40}ms`;

  const header = el("div", "endpoint-header");
  const badge = el("span", `method-badge ${METHOD_CLASS[endpoint.method] || ""}`, endpoint.method);
  const path = el("span", "endpoint-path", endpoint.path);
  const group = el("span", "endpoint-group", endpoint.group);
  header.appendChild(badge);
  header.appendChild(path);
  header.appendChild(group);

  const meta = el("div", "endpoint-meta");
  if (endpoint.details.role) {
    meta.appendChild(el("div", null, `Role: ${endpoint.details.role}`));
  }
  if (endpoint.details.scope) {
    meta.appendChild(el("div", null, `Scope: ${endpoint.details.scope}`));
  }
  if (endpoint.details.scope_rule) {
    meta.appendChild(el("div", null, `Scope rule: ${endpoint.details.scope_rule}`));
  }
  if (endpoint.details.filters) {
    meta.appendChild(el("div", null, `Filters: ${formatValue(endpoint.details.filters)}`));
  }
  if (!meta.childNodes.length) {
    meta.appendChild(el("div", null, "Scope: scoped per policy"));
  }

  const bodyValue = endpoint.details.body || endpoint.details.query;
  const responseValue = extractResponse(endpoint.details);
  const bodyBlock = bodyValue ? el("pre", "code-block", formatJson(bodyValue)) : null;
  const responseBlock = responseValue ? el("pre", "code-block", formatJson(responseValue)) : null;

  const actions = el("div", "endpoint-actions");
  const detailsBtn = el("button", "ghost-button", "Details");
  detailsBtn.setAttribute("data-action", "details");
  const testBtn = el("button", "primary-button", "Test");
  testBtn.setAttribute("data-action", "test");
  actions.appendChild(detailsBtn);
  actions.appendChild(testBtn);

  card.appendChild(header);
  card.appendChild(meta);
  if (bodyBlock) {
    card.appendChild(el("div", "endpoint-label", "Request Body"));
    card.appendChild(bodyBlock);
  }
  if (responseBlock) {
    card.appendChild(el("div", "endpoint-label", "Expected Response"));
    card.appendChild(responseBlock);
  }
  card.appendChild(actions);

  return card;
}

function buildSection(contractKey, contract, indexOffset) {
  const section = el("section", "section");
  section.id = contractKey;

  const header = el("div", "section-header");
  const title = el("div");
  const serviceName = contract.service && contract.service.name ? contract.service.name : contractKey;
  title.appendChild(el("div", "section-title", serviceName));
  header.appendChild(title);

  const meta = el("div", "section-meta");
  if (contract.service && contract.service.version) {
    meta.appendChild(el("span", "meta-pill", `Version ${contract.service.version}`));
  }
  if (contract.service && contract.service.base_url) {
    meta.appendChild(el("span", "meta-pill", contract.service.base_url));
  }
  header.appendChild(meta);

  const grid = el("div", "section-grid");
  const permissions = contract.permissions || {};
  const permissionItems = Object.entries(permissions).map(
    ([role, rules]) => `${role}: ${Array.isArray(rules) ? rules.join(", ") : rules}`
  );
  const errorItems = (contract.errors || []).map((error) => `${error.code}: ${error.message}`);
  grid.appendChild(buildInfoCard("Permissions", permissionItems));
  grid.appendChild(buildInfoCard("Errors", errorItems));

  const endpoints = flattenEndpoints(contract.endpoints);
  endpoints.forEach((endpoint, index) => {
    const card = buildEndpointCard(endpoint, index + indexOffset);
    const endpointId = `endpoint-${state.endpointMap.size + 1}`;
    state.endpointMap.set(endpointId, { ...endpoint, contractKey, contract });
    card.dataset.endpointId = endpointId;
    grid.appendChild(card);
  });

  section.appendChild(header);
  section.appendChild(grid);
  return { section, endpointCount: endpoints.length };
}

function renderContracts() {
  dom.content.innerHTML = "";
  state.endpointMap.clear();

  const navInfo = [];
  let totalEndpoints = 0;
  let rolesCount = 0;

  Object.values(state.contracts).forEach((contract) => {
    if (contract.permissions) {
      rolesCount += Object.keys(contract.permissions).length;
    }
  });

  let indexOffset = 0;
  CONTRACTS.forEach(({ key, label }) => {
    const contract = state.contracts[key];
    if (!contract) return;
    const { section, endpointCount } = buildSection(key, contract, indexOffset);
    indexOffset += endpointCount;
    totalEndpoints += endpointCount;
    dom.content.appendChild(section);
    const serviceLabel = contract.service && contract.service.name ? contract.service.name : label;
    navInfo.push({ key, label: serviceLabel, endpoints: endpointCount });
  });

  buildNav(navInfo);
  renderOverview({ services: navInfo.length, endpoints: totalEndpoints, roles: rolesCount });
  setupSectionObserver();
}

async function loadContracts() {
  state.contracts = {};
  dom.overview.innerHTML = "";
  dom.content.innerHTML = "";
  dom.nav.innerHTML = "";

  const loadingCard = el("div", "overview-card");
  loadingCard.appendChild(el("h3", null, "Loading contracts..."));
  loadingCard.appendChild(el("p", null, "Fetching API definitions from the server."));
  dom.overview.appendChild(loadingCard);

  const results = await Promise.allSettled(
    CONTRACTS.map(async (entry) => {
      const response = await fetch(entry.url);
      if (!response.ok) {
        throw new Error(`Failed to load ${entry.key}`);
      }
      const data = await response.json();
      return { key: entry.key, data };
    })
  );

  const failures = [];
  results.forEach((result, index) => {
    const entry = CONTRACTS[index];
    if (result.status === "fulfilled") {
      state.contracts[entry.key] = result.value.data;
    } else {
      failures.push(entry.label);
    }
  });

  if (Object.keys(state.contracts).length) {
    renderContracts();
    if (failures.length) {
      const warnCard = el("div", "overview-card");
      warnCard.appendChild(el("h3", null, "Missing contracts"));
      warnCard.appendChild(el("p", null, failures.join(", ")));
      dom.overview.appendChild(warnCard);
    }
    return;
  }

  dom.overview.innerHTML = "";
  const errorCard = el("div", "overview-card");
  errorCard.appendChild(el("h3", null, "Contracts unavailable"));
  errorCard.appendChild(el("p", null, "No contract files could be loaded."));
  dom.overview.appendChild(errorCard);
}

function openModal(endpointId) {
  const endpoint = state.endpointMap.get(endpointId);
  if (!endpoint) return;
  state.activeEndpointId = endpointId;

  dom.modalGroup.textContent = endpoint.group;
  dom.modalTitle.textContent = `${endpoint.method} ${endpoint.path}`;
  dom.modalPath.textContent = endpoint.signature;
  dom.modalRole.textContent = formatValue(endpoint.details.role);
  dom.modalScope.textContent = formatValue(endpoint.details.scope || endpoint.details.scope_rule);
  dom.modalEffect.textContent = formatValue(endpoint.details.effect);
  dom.modalRequest.textContent = formatJson(endpoint.details.body || endpoint.details.query) || "No request body.";
  dom.modalResponse.textContent = formatJson(extractResponse(endpoint.details)) || "No response sample.";

  dom.modalRules.innerHTML = "";
  if (Array.isArray(endpoint.details.rules) && endpoint.details.rules.length) {
    endpoint.details.rules.forEach((rule) => {
      dom.modalRules.appendChild(el("div", null, rule));
    });
  } else {
    dom.modalRules.textContent = "None";
  }

  dom.modalMethod.value = endpoint.method;
  const resolvedPath = resolveEndpointPath(endpoint);
  renderPathParams(resolvedPath);
  renderQueryParams(extractQueryDefinitions(endpoint.details));
  updateModalUrl();
  const prefersQuery = ["GET", "HEAD"].includes(endpoint.method);
  const defaultBody = endpoint.details.body ?? (prefersQuery ? endpoint.details.query : undefined);
  dom.modalBody.value = formatJson(defaultBody);
  dom.testStatus.textContent = "";
  dom.testOutput.textContent = "";

  dom.modal.classList.add("open");
  dom.modal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  dom.modal.classList.remove("open");
  dom.modal.setAttribute("aria-hidden", "true");
  state.activeEndpointId = null;
}

async function runTest() {
  const endpoint = state.endpointMap.get(state.activeEndpointId);
  if (!endpoint) return;

  const method = endpoint.method.toUpperCase();
  const headers = { "Content-Type": "application/json" };
  const token = dom.tokenInput.value.trim();
  if (token) headers.Authorization = `Bearer ${token}`;

  const options = { method, headers };
  const bodyText = dom.modalBody.value.trim();
  const queryParams = collectQueryParams();

  if (["GET", "HEAD"].includes(method) && bodyText && !queryParams.length) {
    try {
      const parsed = JSON.parse(bodyText);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Query JSON must be an object.");
      }
      Object.entries(parsed).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          queryParams.push([key, String(value)]);
        }
      });
    } catch (error) {
      dom.testStatus.textContent = "Invalid JSON query.";
      dom.testOutput.textContent = error.message;
      return;
    }
  }

  const url = buildEndpointUrl(endpoint, queryParams);
  dom.modalUrl.value = url;
  if (url.includes("<") || url.includes(">")) {
    dom.testStatus.textContent = "Fill path parameters before testing.";
    dom.testOutput.textContent = "";
    return;
  }

  const sameOrigin = isSameOrigin(url);
  options.credentials = sameOrigin ? "same-origin" : "omit";
  const csrfToken = getCsrfToken();
  if (csrfToken && !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method) && sameOrigin) {
    headers["X-CSRFToken"] = csrfToken;
  }

  if (!["GET", "HEAD"].includes(method) && bodyText) {
    try {
      options.body = JSON.stringify(JSON.parse(bodyText));
    } catch (error) {
      dom.testStatus.textContent = "Invalid JSON body.";
      dom.testOutput.textContent = error.message;
      return;
    }
  }

  dom.testStatus.textContent = "Running...";
  dom.testOutput.textContent = "";

  try {
    const response = await fetch(url, options);
    const text = await response.text();
    let output = text;
    try {
      output = JSON.stringify(JSON.parse(text), null, 2);
    } catch (error) {
      output = text || "(empty response)";
    }
    dom.testStatus.textContent = `Status ${response.status} ${response.statusText}`;
    dom.testOutput.textContent = output;
  } catch (error) {
    dom.testStatus.textContent = "Request failed.";
    dom.testOutput.textContent = error.message;
  }
}

function setupSectionObserver() {
  const links = Array.from(dom.nav.querySelectorAll(".section-link"));
  const sections = Array.from(dom.content.querySelectorAll(".section"));
  const linkMap = new Map();
  links.forEach((link) => {
    const id = link.getAttribute("href").slice(1);
    linkMap.set(id, link);
  });

  if (!("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          links.forEach((link) => link.classList.remove("active"));
          const link = linkMap.get(entry.target.id);
          if (link) link.classList.add("active");
        }
      });
    },
    { rootMargin: "-40% 0px -55% 0px" }
  );
  sections.forEach((section) => observer.observe(section));
}

function bindEvents() {
  dom.themeToggle.addEventListener("click", () => {
    const current = document.documentElement.dataset.theme || "light";
    setTheme(current === "dark" ? "light" : "dark");
  });

  dom.content.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const card = event.target.closest(".endpoint-card");
    if (!card) return;
    openModal(card.dataset.endpointId);
    if (button.dataset.action === "test") {
      dom.modalBody.focus();
    }
  });

  dom.runTest.addEventListener("click", runTest);
  dom.pathParams.addEventListener("input", updateModalUrl);
  dom.queryParams.addEventListener("input", updateModalUrl);

  dom.modal.addEventListener("click", (event) => {
    if (event.target.matches("[data-close-modal]")) {
      closeModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && dom.modal.classList.contains("open")) {
      closeModal();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initBaseUrl();
  bindEvents();
  loadContracts();
});
