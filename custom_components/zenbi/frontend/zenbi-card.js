/* Zenbi Card — no external dependencies. MIT; official icon retains Zenbi's rights. */
const VERSION = "1.0.3";
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
// Reuse controls instead of removing the focused button and browser scroll anchor.
function patchChildren(parent, template) {
  const key = (node) =>
    node.nodeType === 1
      ? `${node.tagName}:${node.getAttribute("data-key") || node.getAttribute("data-tab") || node.getAttribute("data-child") || node.getAttribute("data-action") || ""}`
      : String(node.nodeType);
  let current = parent.firstChild;
  for (const wanted of [...template.childNodes]) {
    if (!current || key(current) !== key(wanted)) {
      const match = [...parent.childNodes].find(
        (node) =>
          key(node) === key(wanted) &&
          node !== current &&
          wanted.nodeType === 1 &&
          wanted.hasAttribute("data-key"),
      );
      if (match) parent.insertBefore(match, current);
      else parent.insertBefore(wanted.cloneNode(true), current);
      current = current ? current.previousSibling : parent.lastChild;
    }
    if (wanted.nodeType === 1) {
      for (const attribute of [...current.attributes])
        if (!wanted.hasAttribute(attribute.name))
          current.removeAttribute(attribute.name);
      for (const attribute of wanted.attributes)
        if (current.getAttribute(attribute.name) !== attribute.value)
          current.setAttribute(attribute.name, attribute.value);
      // HA owns its icon internals; only its public attributes belong to the card.
      if (wanted.tagName !== "HA-ICON") patchChildren(current, wanted);
    } else if (current.nodeValue !== wanted.nodeValue)
      current.nodeValue = wanted.nodeValue;
    current = current.nextSibling;
  }
  while (current) {
    const next = current.nextSibling;
    current.remove();
    current = next;
  }
}
function scrollPositions(host) {
  const positions = [];
  // HA dashboards can scroll inside shadow hosts rather than the document.
  for (let node = host; node; node = node.parentNode || node.host) {
    if (
      node.nodeType === 1 &&
      (node.scrollHeight > node.clientHeight ||
        node.scrollWidth > node.clientWidth)
    )
      positions.push([node, node.scrollTop, node.scrollLeft]);
  }
  return positions;
}
const registryCache = new WeakMap();
async function registry(hass) {
  const key = hass.connection;
  if (!key) return [];
  if (!registryCache.has(key)) {
    const request = hass
      .callWS({ type: "config/entity_registry/list" })
      .then((rows) =>
        rows.filter(
          (r) => r.platform === "zenbi" && !r.disabled_by && !r.hidden_by,
        ),
      );
    registryCache.set(key, request);
    request.catch(() => registryCache.delete(key));
  }
  return registryCache.get(key);
}
const tabs = [
  ["homework", "Lektier", "book-open-page-variant"],
  ["calendar", "Kalender", "calendar-outline"],
  ["messages", "Beskeder", "email-outline"],
  ["weekly_plans", "Ugeplan", "view-week-outline"],
  ["posts", "Opslag", "bulletin-board"],
];
function selectedTopics(config) {
  return config.topics || tabs.map(([id]) => id).filter(id => id !== "posts" || config.show_posts !== false);
}
const css = `
:host{display:block;--z-accent:#008cb7;container-type:inline-size;--z-soft:color-mix(in srgb,var(--z-accent) 9%,var(--ha-card-background,var(--card-background-color,#fff)));--z-muted:var(--secondary-text-color,#6b7885)}
*{box-sizing:border-box}ha-card{display:block;overflow:hidden;border-radius:24px;background:var(--ha-card-background,var(--card-background-color,#fff));color:var(--primary-text-color,#172d3c);border:1px solid var(--divider-color,#e6edf0);box-shadow:var(--ha-card-box-shadow,0 5px 24px #17334508)}
button,a,summary,select{font:inherit}button,a,summary{touch-action:manipulation}button{cursor:pointer;color:inherit}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--z-accent);outline-offset:3px}button:disabled{cursor:wait;opacity:.5}button{border:0;background:none}ha-icon{--mdc-icon-size:20px;flex:none}header{padding:24px 24px 20px;background:linear-gradient(125deg,var(--z-soft),transparent 85%)}
.top{display:flex;align-items:center;gap:12px}.logo{width:43px;height:43px;object-fit:contain}.heading{flex:1;min-width:0}h1{font-size:21px;margin:0;letter-spacing:-.5px;font-weight:750}.eyebrow{font-size:10px;letter-spacing:1.7px;font-weight:700;color:var(--z-accent);margin:0 0 5px;text-transform:uppercase}.refresh{padding:10px;border-radius:50%;background:var(--ha-card-background,var(--card-background-color,#fff));display:grid;place-items:center}.sub{font-size:12px;color:var(--z-muted);margin:15px 0 0;display:flex;align-items:center;gap:7px}.dot{width:6px;height:6px;background:#2eb590;border-radius:100%}.dot.warn{background:#e7a244}.children{display:flex;flex-wrap:wrap;gap:8px;overflow:auto;margin-top:20px;padding:3px 2px}.child{display:flex;gap:8px;align-items:center;padding:6px 13px 6px 6px;white-space:nowrap;border:1px solid var(--divider-color,#e6edf0);border-radius:30px;background:var(--ha-card-background,var(--card-background-color,#fff));font-size:13px;font-weight:650}.child.active{background:var(--z-accent);border-color:var(--z-accent);color:#fff}.avatar{height:27px;width:27px;border-radius:50%;display:grid;place-items:center;background:var(--z-soft);color:var(--z-accent);font-size:11px;font-weight:700}.active .avatar{background:#ffffff30;color:#fff}.avatar img{width:100%;height:100%;object-fit:cover;border-radius:50%}.child-copy{display:flex;flex-direction:column;align-items:flex-start;gap:2px}.child-class{font-size:10px;font-weight:400;opacity:.8}.stats{display:grid;grid-template-columns:repeat(var(--z-stat-count,3),minmax(0,1fr));gap:10px;padding:0 24px;margin-top:4px}.stat{background:var(--z-soft);border-radius:16px;padding:14px;text-align:left;display:flex;flex-direction:column;gap:5px}.stat-top{display:flex;align-items:center;justify-content:space-between;color:var(--z-accent)}.number{font-size:26px;font-weight:750;line-height:1}.stat-label{font-size:11px;color:var(--z-muted)}nav{display:flex;gap:5px;overflow:auto;padding:21px 24px 14px;scrollbar-width:thin}.tab{display:flex;flex:none;gap:6px;align-items:center;white-space:nowrap;border-radius:10px;padding:9px 11px;font-size:12px;font-weight:650;color:var(--z-muted)}.tab.active{background:var(--z-soft);color:var(--z-accent)}.tab ha-icon{--mdc-icon-size:16px}.badge{font-size:10px;min-width:17px;padding:2px 4px;background:var(--z-accent);color:white;border-radius:5px;text-align:center}.content{padding:0 24px 20px}.section-title{font-size:11px;color:var(--z-muted);letter-spacing:1.1px;text-transform:uppercase;margin:4px 0 12px;font-weight:700}.item{border:1px solid var(--divider-color,#e6edf0);border-radius:15px;margin-bottom:9px;padding:14px}.item summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:12px}.item summary::-webkit-details-marker{display:none}.item .copy{flex:1;min-width:0}.item-title{font-size:14px;font-weight:650;line-height:1.45;overflow-wrap:anywhere}.item-meta{font-size:11px;color:var(--z-muted);margin-top:4px;line-height:1.5}.date{width:41px;min-height:43px;flex:none;text-align:center;background:var(--z-soft);border-radius:10px;padding:6px 2px;color:var(--z-accent)}.day{font-weight:750;font-size:19px;line-height:1.1}.month{font-size:9px;text-transform:uppercase;margin-top:2px}.chevron{--mdc-icon-size:16px;color:var(--z-muted);transition:transform .15s}.item[open] .chevron{transform:rotate(180deg)}.body{white-space:pre-wrap;font-size:13px;line-height:1.7;margin:13px 0 0;padding-top:13px;border-top:1px solid var(--divider-color,#e6edf0);overflow-wrap:anywhere}.kind{color:var(--z-accent)}.empty{text-align:center;padding:25px 12px 30px;color:var(--z-muted);font-size:13px;line-height:1.6}.empty ha-icon{--mdc-icon-size:30px;color:var(--z-accent);margin-bottom:10px}.empty strong{display:block;color:var(--primary-text-color);font-size:15px;margin-bottom:4px}.notice{font-size:12px;line-height:1.5;padding:12px;border-radius:10px;background:var(--z-soft);margin-bottom:10px;color:var(--z-muted)}footer{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--divider-color,#e6edf0);padding:14px 24px;font-size:11px;color:var(--z-muted);gap:10px}footer a{color:var(--z-accent);text-decoration:none;display:flex;gap:5px;align-items:center;font-weight:650}.more{color:var(--z-accent);width:100%;padding:9px;font-size:12px;font-weight:650}.error{color:var(--error-color,#b74931);font-size:12px;margin:10px 0}.syncing ha-icon{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}@media(max-width:390px){header{padding:19px 16px 16px}.stats{padding:0 16px;gap:7px}.stat{padding:12px 9px}.content{padding:0 16px 16px}nav{padding:18px 16px 12px}footer{padding:14px 16px}.tab{padding:8px}.number{font-size:23px}}
@container(max-width:390px){.tab{padding:9px 8px;font-size:12px}.child{font-size:12px;padding-right:10px}.children{gap:6px}.stat-label{font-size:11px}}
`;
class ZenbiCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "homework";
    this._selected = "all";
    this._events = [];
    this._expanded = new Set();
    this._showAll = false;
    this._calendarGeneration = 0;
    this.shadowRoot.addEventListener("click", (e) => this._click(e));
    this.shadowRoot.addEventListener("error", (event) => {
      if (event.target.matches?.(".avatar img")) {
        const button = event.target.closest(".child");
        event.target.parentElement.textContent = (button?.getAttribute("aria-label") || "")
          .split(/\s+/).map(part => part[0]).slice(0, 2).join("");
      }
    }, true);
    this.shadowRoot.addEventListener(
      "toggle",
      (e) => {
        if (e.target.isConnected && e.target.matches("details[data-key]")) {
          const k = e.target.dataset.key;
          e.target.open ? this._expanded.add(k) : this._expanded.delete(k);
        }
      },
      true,
    );
  }
  static getConfigElement() {
    return document.createElement("zenbi-card-editor");
  }
  static getStubConfig() {
    return { title: "Skoleoverblik", max_items: 5, topics: tabs.map(([id]) => id) };
  }
  setConfig(config) {
    if (config.children && !Array.isArray(config.children))
      throw new Error("children skal være en liste.");
    if (config.topics !== undefined &&
      (!Array.isArray(config.topics) || !config.topics.length ||
        config.topics.some(id => !tabs.some(([key]) => key === id))))
      throw new Error("topics skal være en liste med mindst ét gyldigt emne.");
    this._config = {
      title: "Skoleoverblik",
      max_items: 5,
      show_posts: true,
      ...config,
    };
    this._entryLoaded = false;
    this._calendarKey = null;
    this._calendarGeneration++;
    this._selected = "all";
    this._showAll = false;
    this._render();
    this._discover();
  }
  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    this._discover();
    const ids = [
      ...(this._rows || []).map((r) => r.entity_id),
      ...JSON.stringify(this._config || {}).matchAll(
        /(?:sensor|calendar|button|person)\.[a-z0-9_]+/g,
      ),
    ].map((r) => (Array.isArray(r) ? r[0] : r));
    if (
      !previous ||
      !this._entryLoaded ||
      ids.some((id) => previous.states[id] !== hass.states[id])
    )
      this._render();
    this._loadCalendar();
  }
  getCardSize() {
    return 7;
  }
  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }
  connectedCallback() {
    this._timer = setInterval(() => {
      this._render();
      this._loadCalendar();
    }, 60000);
  }
  disconnectedCallback() {
    clearInterval(this._timer);
  }
  async _discover() {
    if (!this._hass || !this._config || this._entryLoaded || this._discovering)
      return;
    this._discovering = true;
    const config = this._config;
    try {
      const rows = await registry(this._hass);
      if (config !== this._config) return;
      const entry = config.config_entry || rows[0]?.config_entry_id;
      this._rows = rows.filter((r) => r.config_entry_id === entry);
      this._multipleEntries =
        new Set(rows.map((r) => r.config_entry_id)).size > 1 &&
        !config.config_entry;
      this._entryLoaded = true;
      this._discoveryError = false;
    } catch {
      this._discoveryError = true;
      this._entryLoaded = true;
    } finally {
      this._discovering = false;
      this._render();
      if (config !== this._config) this._discover();
      this._loadCalendar();
    }
  }
  _bindings() {
    const all = { id: "all", name: "Alle børn" };
    const children = new Map();
    for (const r of this._rows || []) {
      if (
        r.entity_id.startsWith("button.") &&
        r.unique_id?.endsWith(":refresh")
      ) {
        all.update = r.entity_id;
        continue;
      }
      if (
        !r.entity_id.startsWith("sensor.") &&
        !r.entity_id.startsWith("calendar.")
      )
        continue;
      const match = r.unique_id?.match(
        /:(homework|tasks|weekly_plans|calendar|messages|unread|posts|status|update):([^:]+)$/,
      );
      if (!match) continue;
      let [, kind, id] = match;
      const isCalendar = r.entity_id.startsWith("calendar.");
      // Calendar IDs are account:calendar:calendar:all or account:calendar:child_calendar:child.
      if (isCalendar) {
        const m = r.unique_id.match(
          /:calendar:(calendar|child_calendar):([^:]+)$/,
        );
        if (!m) continue;
        kind = "calendar";
        id = m[2];
      }
      if (id === "all") all[kind] = r.entity_id;
      else {
        if (!children.has(id))
          children.set(id, {
            id,
            name: (r.original_name || r.name || "Barn").replace(
              /\s+(Lektier|Opgaver|Ugeplaner|Kalender)$/i,
              "",
            ),
          });
        children.get(id)[kind] = r.entity_id;
      }
    }
    // child_calendar doesn't match the generic expression above; add these separately.
    for (const r of this._rows || []) {
      const m = r.unique_id?.match(/:calendar:child_calendar:([^:]+)$/);
      if (m && children.has(m[1])) children.get(m[1]).calendar = r.entity_id;
    }
    for (const k of [
      "homework",
      "tasks",
      "weekly_plans",
      "calendar",
      "messages",
      "unread",
      "posts",
      "status",
      "update",
    ])
      if (this._config?.[`${k}_entity`]) all[k] = this._config[`${k}_entity`];
    const custom = this._config?.children;
    const resolvedChildren = custom
      ? custom.map((c, i) => ({
          id: c.id || `custom-${i}`,
          name: c.name || "Barn",
          ...Object.fromEntries(
            Object.keys(c)
              .filter((k) => k.endsWith("_entity"))
              .map((k) => [k.slice(0, -7), c[k]]),
          ),
        }))
      : Array.from(children.values());
    for (const child of resolvedChildren) {
      child.person = this._config.persons?.[child.id];
      child.picture = this._hass?.states[child.person]?.attributes.entity_picture ||
        this._hass?.states[child.homework]?.attributes.entity_picture ||
        this._hass?.states[child.weekly_plans]?.attributes.entity_picture;
      if (child.picture && !/^(\/(?!\/)|https?:\/\/)/.test(child.picture)) child.picture = null;
      child.school_class = this._hass?.states[child.homework]?.attributes.klasse ||
        this._hass?.states[child.weekly_plans]?.attributes.klasse || "";
      child.full_name = child.name;
      if (!this._config.full_names)
        child.name = child.name.trim().split(/\s+/)[0];
    }
    if (!all.weekly_plans)
      all.weekly_plans = resolvedChildren
        .map((c) => c.weekly_plans)
        .filter(Boolean);
    return { all, children: resolvedChildren };
  }
  _view() {
    const b = this._bindings();
    return {
      ...b,
      active:
        this._selected === "all"
          ? b.all
          : b.children.find((c) => c.id === this._selected) || b.all,
    };
  }
  _state(entity) {
    if (Array.isArray(entity)) {
      const states = entity.map((id) => this._hass?.states[id]);
      if (
        !states.length ||
        states.some((s) => !s || ["unknown", "unavailable"].includes(s.state))
      )
        return { state: "unavailable", attributes: {} };
      const rows = new Map();
      for (const s of states)
        for (const row of s.attributes.items || []) rows.set(row.id, row);
      return {
        state: String(rows.size),
        attributes: {
          items: [...rows.values()],
          afkortet: states.some((s) => s.attributes.afkortet),
        },
      };
    }
    return entity ? this._hass?.states[entity] : undefined;
  }
  _available(entity) {
    const s = this._state(entity);
    return !!s && !["unknown", "unavailable"].includes(s.state);
  }
  _items(entity) {
    return this._available(entity) &&
      Array.isArray(this._state(entity).attributes.items)
      ? this._state(entity).attributes.items
      : [];
  }
  _count(entity) {
    return this._available(entity) ? this._state(entity).state : "—";
  }
  _date(value, options) {
    if (!value) return "";
    const d = new Date(
      /^\d{4}-\d{2}-\d{2}$/.test(value) ? value + "T00:00:00" : value,
    );
    if (Number.isNaN(+d)) return "";
    return d.toLocaleDateString("da-DK", {
      ...(options || { day: "numeric", month: "short" }),
      ...(String(value).includes("T")
        ? { timeZone: this._hass?.config?.time_zone }
        : {}),
    });
  }
  _row(row, kind) {
    const date =
      row.start?.dateTime || row.start?.date || row.start || row.date;
    const title =
      row.summary ||
      (row.title !== kind ? row.title : null) ||
      {
        homework: "Lektie",
        tasks: "Opgave",
        weekly_plans: "Ugeplan",
        messages: "Besked",
        posts: "Opslag",
      }[kind] ||
      "Begivenhed";
    const text =
      typeof row.description === "string" ? row.description : row.text || "";
    const key = `${kind}:${row.id || row.uid || title}:${date || ""}`;
    const day = this._date(date, { day: "numeric" });
    const month = this._date(date, { month: "short" });
    const meta = [
      {
        homework: "Lektie",
        tasks: "Opgave",
        weekly_plans: "Ugeplan",
        calendar: "Begivenhed",
        messages: "Besked",
        posts: "Opslag",
      }[kind],
      this._date(date),
      kind === "calendar" && String(date).includes("T")
        ? new Date(date).toLocaleTimeString("da-DK", {
            hour: "2-digit",
            minute: "2-digit",
            timeZone: this._hass?.config?.time_zone,
          })
        : "",
      row.attachment_count ? `${row.attachment_count} vedhæftninger` : null,
    ]
      .filter(Boolean)
      .join(" · ");
    return `<details class="item" data-key="${esc(key)}" ${this._expanded.has(key) ? "open" : ""}><summary>${day ? `<div class="date"><div class="day">${esc(day)}</div><div class="month">${esc(month)}</div></div>` : `<div class="date"><ha-icon icon="mdi:${kind === "messages" ? "email-outline" : "text-box-outline"}"></ha-icon></div>`}<div class="copy"><div class="item-title">${esc(title)}</div><div class="item-meta">${esc(meta)}</div></div><ha-icon class="chevron" icon="mdi:chevron-down"></ha-icon></summary><div class="body">${esc(text || "Ingen yderligere tekst. Se flere detaljer i Zenbi.")}</div></details>`;
  }
  _empty(title, text, icon = "check-circle-outline") {
    return `<div class="empty"><ha-icon icon="mdi:${icon}"></ha-icon><strong>${esc(title)}</strong>${esc(text)}</div>`;
  }
  _content(active, all) {
    const kind = this._tab;
    let rows = [];
    let sources = [];
    if (kind === "calendar") {
      if (!this._available(active.calendar))
        return this._empty(
          "Kalender ikke tilgængelig",
          "Vælg en kalender i konfigurationen, eller kontrollér integrationens datastatus.",
          "calendar-alert",
        );
      if (this._calendarError)
        return this._empty(
          "Kalenderen kunne ikke hentes",
          "Prøv Opdater, eller åbn kalenderentiteten.",
          "calendar-alert",
        );
      if (this._calendarLoading)
        return this._empty(
          "Henter kalender…",
          "Begivenheder de næste 7 dage.",
          "calendar-outline",
        );
      rows = this._events.map((r) => ({ row: r, kind }));
    } else {
      sources = kind === "homework" ? ["homework", "tasks"] : [kind];
      for (const s of sources) {
        const entity = ["messages", "posts"].includes(s) ? all[s] : active[s];
        if (entity && this._available(entity))
          rows.push(...this._items(entity).map((row) => ({ row, kind: s })));
      }
      const missing = sources.filter(
        (s) =>
          !this._available(
            (["messages", "posts"].includes(s) ? all : active)[s],
          ),
      );
      if (
        kind === "posts" &&
        this._state(all.status)?.attributes.datakilder?.posts ===
          "PermissionError"
      )
        return this._empty(
          "Opslag bliver afvist af Zenbi",
          "Kontoen fik HTTP 403 for opslag. De øvrige datakilder virker fortsat.",
          "lock-outline",
        );
      if (missing.length === sources.length)
        return this._empty(
          "Data ikke tilgængelige",
          "Kontrollér Zenbis datastatus og kortets entiteter.",
          "cloud-alert",
        );
      if (kind === "homework" || kind === "weekly_plans")
        rows.sort((a, b) =>
          String(a.row.date || "9999").localeCompare(
            String(b.row.date || "9999"),
          ),
        );
      this._sourceNotice = missing.length
        ? '<div class="notice">En datakilde er utilgængelig. Listen viser kun det, der kunne hentes.</div>'
        : "";
    }
    const titles = {
      homework: [
        "Ingen kommende lektier",
        "Der er ingen lektier eller opgaver i den hentede periode.",
      ],
      calendar: ["En rolig uge", "Ingen begivenheder de næste 7 dage."],
      messages: ["Ingen beskeder", "Der er ingen beskeder i den hentede side."],
      weekly_plans: [
        "Ingen ugeplaner",
        "Der er ingen planer i den hentede periode.",
      ],
      posts: ["Ingen opslag", "Der er ingen opslag i den hentede periode."],
    };
    const limit = Math.max(
      1,
      Math.min(50, Number(this._config.max_items) || 5),
    );
    const notice = kind === "calendar" ? "" : this._sourceNotice || "";
    const clipped = sources.some(
      (s) =>
        this._state((["messages", "posts"].includes(s) ? all : active)[s])
          ?.attributes.afkortet,
    );
    return (
      notice +
      (!rows.length
        ? this._empty(...titles[kind])
        : rows
            .slice(0, this._showAll ? 50 : limit)
            .map((r) => this._row(r.row, r.kind))
            .join("")) +
      (rows.length > limit
        ? `<button class="more" data-action="more">${this._showAll ? "Vis færre" : `Vis flere (${Math.min(rows.length, 50)})`}</button>`
        : "") +
      (clipped
        ? '<div class="notice">Listen er afkortet af integrationen. Se alle elementer i Zenbi.</div>'
        : "")
    );
  }
  _render() {
    if (!this._config || !this._hass) return;
    const { all, children, active } = this._view();
    const status = this._state(all.status);
    const updated = status?.attributes.senest_opdateret;
    const ok = status?.state === "ok";
    const stamp = updated
      ? new Date(updated).toLocaleTimeString("da-DK", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: this._hass.config?.time_zone,
        })
      : "";
    const topics = selectedTopics(this._config);
    const tabList = tabs.filter(([id]) => topics.includes(id));
    if (!topics.includes(this._tab)) this._tab = tabList[0][0];
    const icon = (name) => `<ha-icon icon="mdi:${name}"></ha-icon>`;
    const stat = (value, label, name, tab) =>
      topics.includes(tab) ? `<button class="stat" data-tab="${tab}" aria-label="${esc(label)}: ${esc(value)}"><div class="stat-top"><span class="number">${esc(value)}</span>${icon(name)}</div><span class="stat-label">${label}</span></button>` : "";
    const homework = Number(this._count(active.homework));
    const tasks = Number(this._count(active.tasks));
    const count =
      Number.isFinite(homework) && Number.isFinite(tasks)
        ? homework + tasks
        : "—";
    const statCount = ["homework", "messages", "weekly_plans"].filter(id => topics.includes(id)).length;
    const showChildren = topics.some(id => ["homework", "calendar", "weekly_plans"].includes(id));
    const childButton = (c) =>
      `<button class="child ${this._selected === c.id ? "active" : ""}" data-child="${esc(c.id)}" title="${esc(c.full_name || c.name)}" aria-label="${esc(c.name)}" aria-pressed="${this._selected === c.id}"><span class="avatar">${c.picture ? `<img src="${esc(c.picture)}" alt="" loading="lazy">` : esc(
        c.id === "all"
          ? "★"
          : c.name
              .split(/\s+/)
              .map((w) => w[0])
              .slice(0, 2)
              .join(""),
      )}</span><span class="child-copy">${esc(c.name)}${c.school_class ? `<span class="child-class">${esc(c.school_class)}</span>` : ""}</span></button>`;
    const scrolls = ["nav", ".children"].map((selector) => [
      selector,
      this.shadowRoot.querySelector(selector)?.scrollLeft || 0,
    ]);
    for (const details of this.shadowRoot.querySelectorAll(
      "details[open][data-key]",
    ))
      this._expanded.add(details.dataset.key);
    const positions = scrollPositions(this);
    const template = document.createElement("template");
    template.innerHTML = `<style>${css}</style><ha-card><header><div class="top"><img class="logo" src="/zenbi-card/icon.png" alt="Zenbi"><div class="heading"><p class="eyebrow">Skole & hverdag</p><h1>${esc(this._config.title)}</h1></div>${all.update ? `<button class="refresh ${this._refreshing ? "syncing" : ""}" data-action="refresh" aria-label="Opdater Zenbi" ${this._refreshing || !this._state(all.update) || this._state(all.update).state === "unavailable" ? "disabled" : ""}>${icon("refresh")}</button>` : ""}</div><p class="sub"><span class="dot ${ok ? "" : "warn"}"></span>${ok ? "Opdateret" : status?.state === "delvis" ? "Nogle data mangler" : "Afventer data"}${stamp ? " kl. " + esc(stamp) : ""}</p>${showChildren && children.length ? `<div class="children" aria-label="Vælg barn">${[all, ...children].map(childButton).join("")}</div>` : ""}</header>${statCount ? `<div class="stats" style="--z-stat-count:${statCount}">${stat(count, "Lektier & opgaver", "book-open-page-variant", "homework")}${stat(this._count(all.unread), "Ulæste beskeder", "email-outline", "messages")}${stat(this._count(active.weekly_plans), "Ugeplaner", "view-week-outline", "weekly_plans")}</div>` : ""}<nav aria-label="Vis indhold">${tabList.map(([id, title, name]) => `<button class="tab ${this._tab === id ? "active" : ""}" data-tab="${id}" aria-pressed="${this._tab === id}">${icon(name)}${title}${id === "messages" && Number(this._count(all.unread)) > 0 ? `<span class="badge">${esc(this._count(all.unread))}</span>` : ""}</button>`).join("")}</nav><div class="content">${this._multipleEntries ? '<div class="notice">Flere Zenbi-konti er fundet. Vælg konto i kortets editor.</div>' : ""}${this._discoveryError ? '<div class="notice">Automatisk entitetsvalg fejlede. Vælg entiteter manuelt i YAML, eller genindlæs dashboardet.</div>' : ""}${this._actionError ? `<p class="error" role="alert">${esc(this._actionError)}</p>` : ""}<div class="section-title">${esc(this._tab === "calendar" ? "De næste 7 dage" : ["messages", "posts"].includes(this._tab) ? "Fælles for kontoen" : active.id === "all" ? "Alle børn" : active.name)}</div>${this._content(active, all)}</div><footer><span>${this._tab === "messages" ? "Seneste hentede side · op til 50 beskeder" : "Zenbi · familiens skoleoverblik"}</span><a href="https://app.zenbi.dk/home" target="_blank" rel="noopener noreferrer">Åbn Zenbi ${icon("arrow-top-right")}</a></footer></ha-card>`;
    patchChildren(this.shadowRoot, template.content);
    for (const [node, top, left] of positions) {
      node.scrollTop = top;
      node.scrollLeft = left;
    }
    for (const [selector, left] of scrolls) {
      const node = this.shadowRoot.querySelector(selector);
      if (node) node.scrollLeft = left;
    }
  }
  async _loadCalendar(force = false) {
    if (!this._hass || !this._config || this._tab !== "calendar") return;
    const entity = this._view().active.calendar;
    if (!this._available(entity)) return;
    const key = `${entity}:${this._hass.config?.time_zone}`;
    if (
      !force &&
      key === this._calendarKey &&
      (this._calendarLoading ||
        Date.now() - (this._calendarFetched || 0) < 60000)
    )
      return;
    this._calendarKey = key;
    this._calendarLoading = true;
    this._calendarError = false;
    this._events = [];
    const gen = ++this._calendarGeneration;
    this._render();
    const start = new Date(),
      end = new Date(+start + 7 * 86400000);
    try {
      const result = await this._hass.callApi(
        "GET",
        `calendars/${encodeURIComponent(entity)}?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`,
      );
      if (gen === this._calendarGeneration) {
        if (!Array.isArray(result)) throw new Error("Invalid calendar");
        this._events = result.sort((a, b) =>
          String(a.start?.dateTime || a.start?.date || a.start).localeCompare(
            String(b.start?.dateTime || b.start?.date || b.start),
          ),
        );
      }
    } catch {
      if (gen === this._calendarGeneration) this._calendarError = true;
    } finally {
      if (gen === this._calendarGeneration) {
        this._calendarLoading = false;
        this._calendarFetched = Date.now();
        this._render();
      }
    }
  }
  async _click(event) {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.child) {
      this._selected = button.dataset.child;
      this._showAll = false;
      this._calendarGeneration++;
      this._calendarKey = null;
      this._render();
      this._loadCalendar();
    }
    if (button.dataset.tab) {
      this._tab = button.dataset.tab;
      this._showAll = false;
      this._render();
      this._loadCalendar();
    }
    if (button.dataset.action === "more") {
      this._showAll = !this._showAll;
      this._render();
    }
    if (button.dataset.action === "refresh") {
      const entity = this._view().all.update;
      if (!entity || this._refreshing) return;
      this._refreshing = true;
      this._actionError = "";
      this._render();
      try {
        await this._hass.callService("button", "press", { entity_id: entity });
        await this._loadCalendar(true);
      } catch {
        this._actionError =
          "Opdatering mislykkedes. Kontrollér integrationen og prøv igen.";
      } finally {
        this._refreshing = false;
        this._render();
      }
    }
  }
}
class ZenbiCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("change", (e) => this._change(e));
  }
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    if (!this._rows && !this._loading) {
      this._loading = true;
      registry(hass)
        .then((rows) => {
          this._rows = rows;
          this._render();
        })
        .catch(() => {
          this._rows = [];
          this._render();
        })
        .finally(() => (this._loading = false));
    }
    if (!this.shadowRoot.querySelector("input")) this._render();
  }
  _change(e) {
    const personChild = e.target.dataset.personChild;
    if (personChild) {
      const persons = {...this._config.persons};
      if (e.target.value) persons[personChild] = e.target.value;
      else delete persons[personChild];
      this._config = {...this._config, persons};
      this._emitConfig();
      return;
    }
    const topic = e.target.dataset.topic;
    if (topic) {
      const topics = new Set(selectedTopics(this._config));
      if (e.target.checked) topics.add(topic);
      else topics.delete(topic);
      if (!topics.size) { e.target.checked = true; return; }
      this._config = {...this._config, topics: tabs.map(([id]) => id).filter(id => topics.has(id))};
      delete this._config.show_posts;
      // Keep keyboard focus while updating which checkbox may be cleared.
      for (const input of this.shadowRoot.querySelectorAll("input[data-topic]"))
        input.disabled = topics.size === 1 && input.checked;
      this._emitConfig();
      return;
    }
    const key = e.target.dataset.key;
    if (!key) return;
    const config = { ...this._config };
    const value =
      e.target.type === "checkbox"
        ? e.target.checked
        : key === "max_items"
          ? Math.max(1, Math.min(50, Number(e.target.value) || 5))
          : e.target.value;
    if (value === "") delete config[key];
    else config[key] = value;
    this._config = config;
    this._emitConfig();
  }
  _emitConfig() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
  }
  _entryLabel(id, index) {
    const row = this._rows.find(
      (r) => r.config_entry_id === id && r.unique_id?.endsWith(":status:all"),
    );
    return (
      this._hass?.states[row?.entity_id]?.attributes.friendly_name?.replace(
        /\s+Datastatus$/i,
        "",
      ) || `Zenbi-konto ${index + 1}`
    );
  }
  _render() {
    if (!this._config) return;
    const entries = [
      ...new Set((this._rows || []).map((r) => r.config_entry_id)),
    ];
    const topics = selectedTopics(this._config);
    const people = Object.entries(this._hass?.states || {}).filter(([id]) => id.startsWith("person."));
    const children = (this._rows || []).flatMap(row => {
      if (this._config.config_entry && row.config_entry_id !== this._config.config_entry) return [];
      const match = row.unique_id?.match(/:homework:([^:]+)$/);
      return match && match[1] !== "all" ? [{id:match[1],name:(row.original_name || row.name || "Barn").replace(/\s+Lektier$/i, "")}] : [];
    });
    const uniqueChildren = [...new Map(children.map(child => [child.id,child])).values()];
    this.shadowRoot.innerHTML = `<style>:host{display:block}label{display:block;margin:16px 0;font-size:14px}input:not([type=checkbox]),select{display:block;width:100%;box-sizing:border-box;margin-top:6px;padding:12px;border:1px solid var(--divider-color,#ccc);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}fieldset{border:1px solid var(--divider-color,#ccc);border-radius:8px;margin-top:16px}legend{padding:0 6px}p{font-size:13px;line-height:1.6;color:var(--secondary-text-color)}input:focus,select:focus{outline:2px solid var(--primary-color)}</style><label>Titel<input data-key="title" value="${esc(this._config.title || "Skoleoverblik")}"></label><label>Zenbi-konto<select data-key="config_entry"><option value="">Automatisk (første konto)</option>${entries.map((id, i) => `<option value="${esc(id)}" ${this._config.config_entry === id ? "selected" : ""}>${esc(this._entryLabel(id, i))}</option>`).join("")}</select></label><label>Antal elementer før “Vis flere”<input data-key="max_items" type="number" min="1" max="50" value="${esc(this._config.max_items || 5)}"></label><fieldset><legend>Emner på kortet</legend>${tabs.map(([id, label]) => `<label><input data-topic="${id}" type="checkbox" ${topics.includes(id) ? "checked" : ""} ${topics.length === 1 && topics.includes(id) ? "disabled" : ""}> ${label}</label>`).join("")}</fieldset>${uniqueChildren.length ? `<fieldset><legend>Børnenes profilbilleder</legend>${uniqueChildren.map(child => `<label>${esc(child.name)}<select data-person-child="${esc(child.id)}"><option value="">Zenbi-billede / initialer</option>${people.map(([id, state]) => `<option value="${esc(id)}" ${this._config.persons?.[child.id] === id ? "selected" : ""}>${esc(state.attributes.friendly_name || id)}</option>`).join("")}</select></label>`).join("")}</fieldset><p>Billede og klasse hentes fra Zenbi. Vælg eventuelt en HA-person for at bruge dens billede i stedet. Personens lokation ændres ikke.</p>` : ""}<p>Vælg mindst ét emne. Kun de valgte faner og tilhørende tællere vises.</p><p>Børn og entiteter findes automatisk fra Zenbi-integrationen. Beskeder og opslag er fælles for kontoen. Du kan også angive entiteter og børn manuelt i YAML; se vejledningen på GitHub.</p>`;
  }
}
if (!customElements.get("zenbi-card"))
  customElements.define("zenbi-card", ZenbiCard);
if (!customElements.get("zenbi-card-editor"))
  customElements.define("zenbi-card-editor", ZenbiCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "zenbi-card"))
  window.customCards.push({
    type: "zenbi-card",
    name: "Zenbi · Skoleoverblik",
    description: "Lektier, kalender, beskeder og ugeplaner med børnevælger.",
    preview: true,
    documentationURL: "https://github.com/Timhonore/ha-zenbi#zenbi-card",
  });
console.info(`Zenbi Card ${VERSION}`);
