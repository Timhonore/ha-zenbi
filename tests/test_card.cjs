/* Browser smoke tests with synthetic entities only; no live school data. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.ZENBI_PLAYWRIGHT || "playwright");
const root = path.resolve(__dirname, "..");
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: "chromium",
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({ viewport: { width: 600, height: 950 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("http://zenbi.test/**", (route) =>
    route.fulfill(
      route.request().url().split("?")[0].endsWith("icon.png")
        ? {
            contentType: "image/png",
            body: fs.readFileSync(
              path.join(root, "custom_components/zenbi/brand/icon.png"),
            ),
          }
        : {
            contentType: "text/html",
            body: '<!doctype html><html><body style="margin:0;padding:24px;background:#f0f4f7;font-family:system-ui,sans-serif;--primary-text-color:#193140;--secondary-text-color:#74828d;--divider-color:#e7edf1;"></body></html>',
          },
    ),
  );
  await page.goto("http://zenbi.test/");
  await page.evaluate(() => {
    const paths = {
      refresh: "M17.7 6.3A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.8-4.2L13 11h9V2z",
      "email-outline":
        "M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5-8-5V6l8 5 8-5zm0 10H4v-8l8 5 8-5z",
      "calendar-outline":
        "M19 4h-1V2h-2v2H8V2H6v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 16H5V9h14z",
      "book-open-page-variant":
        "M21 4c-2-1-5-1-9 1-4-2-7-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1zm-10 14c-2-1-4-1-6-1V6c2-.4 4 0 6 1zm8-1c-2 0-4 0-6 1V7c2-1 4-1.4 6-1z",
      "view-week-outline": "M3 4v16h18V4zm5 14H5V6h3zm6 0h-4V6h4zm5 0h-3V6h3z",
      "chevron-down": "m7 10 5 5 5-5-1.4-1.4-3.6 3.6-3.6-3.6z",
      "arrow-top-right": "M5 5v2h10L5 17l2 2L17 9v10h2V5z",
      "bulletin-board":
        "M3 3h18v18H3zm2 2v14h14V5zm2 2h4v4H7zm6 0h4v2h-4zm0 4h4v2h-4zm-6 4h10v2H7z",
    };
    customElements.define(
      "ha-icon",
      class extends HTMLElement {
        connectedCallback() {
          this.innerHTML = `<svg style="display:block;width:var(--mdc-icon-size,20px);height:var(--mdc-icon-size,20px);fill:currentColor" viewBox="0 0 24 24"><path d="${paths[this.getAttribute("icon")?.replace("mdi:", "")] || paths["book-open-page-variant"]}"></path></svg>`;
        }
      },
    );
    window.rows = [];
    window.states = {};
    const day = (n) => {
      const d = new Date();
      d.setDate(d.getDate() + n);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    };
    const add = (kind, id, state, items, name, domain = "sensor") => {
      const entity = `${domain}.demo_${kind}_${id}`;
      rows.push({
        entity_id: entity,
        unique_id: `account:school:${kind}:${id}`,
        platform: "zenbi",
        config_entry_id: "entry-1",
        original_name: name,
      });
      states[entity] = {
        state: String(state),
        attributes: {
          friendly_name: name,
          items,
          senest_opdateret: new Date().toISOString(),
        },
      };
      return entity;
    };
    const hw1 = {
      id: "one",
      title: "Læs kapitel 4 i læsebogen",
      text: "Læs siderne 24–27 sammen med en voksen.\nTal om, hvad hovedpersonen oplever.",
      date: day(1),
    };
    const hw2 = {
      id: "two",
      title: "Matematik · plus og minus",
      text: "Lav opgaverne på side 12. Husk at tage bogen med i skole.",
      date: day(2),
    };
    const task = {
      id: "three",
      title: "Husk tøj til idræt",
      text: "Indendørssko og en drikkedunk.",
      date: day(3),
    };
    const plan = {
      id: "plan",
      title: "weekly_plans",
      text: "Vi arbejder med fortællinger og undersøger efterårets farver.",
      date: day(0),
    };
    add("homework", "all", 2, [hw1, hw2], "Alle lektier");
    add("tasks", "all", 1, [task], "Alle opgaver");
    add("homework", "freja", 1, [hw1], "Freja Testnavn Familienavn Lektier");
    add("tasks", "freja", 0, [], "Freja Opgaver");
    add("weekly_plans", "freja", 1, [plan], "Freja Ugeplaner");
    add("homework", "oscar", 1, [hw2], "Oscar Lektier");
    add("tasks", "oscar", 1, [task], "Oscar Opgaver");
    add("weekly_plans", "oscar", 1, [plan], "Oscar Ugeplaner");
    add(
      "messages",
      "all",
      1,
      [
        {
          id: "message",
          title: "Information om efterårsugen",
          text: "Vi glæder os til en uge med fælles aktiviteter.",
          date: day(0),
        },
      ],
      "Beskeder",
    );
    states["sensor.demo_homework_freja"].attributes.klasse = "2.A";
    states["sensor.demo_homework_freja"].attributes.entity_picture = "/zenbi-card/icon.png?zenbi";
    states["person.demo_freja"] = {state:"home",attributes:{friendly_name:"Freja",entity_picture:"/zenbi-card/icon.png"}};
    add("unread", "all", 2, [], "Ulæste beskeder");
    add("posts", "all", 0, [], "Opslag");
    add("status", "all", "ok", [], "Datastatus");
    for (const id of ["all", "freja", "oscar"]) {
      const e = `calendar.demo_${id}`;
      rows.push({
        entity_id: e,
        unique_id: `account:school:calendar:${id === "all" ? "calendar" : "child_calendar"}:${id}`,
        platform: "zenbi",
        config_entry_id: "entry-1",
        original_name: `${id} Kalender`,
      });
      states[e] = { state: "off", attributes: {} };
    }
    rows.push({
      entity_id: "button.demo_refresh",
      unique_id: "account:school:refresh",
      platform: "zenbi",
      config_entry_id: "entry-1",
    });
    states["button.demo_refresh"] = { state: "unknown", attributes: {} };
    // HA buttons have a timestamp or unknown before first use; unknown is still pressable.
    window.calls = [];
    window.hass = {
      connection: {},
      states,
      config: { time_zone: "Europe/Copenhagen" },
      callWS: async request => {
        if (!["zenbi/weekly_plans","zenbi/timetable"].includes(request.type)) return rows;
        if (request.type === "zenbi/timetable") return {week:request.week,unmapped:0,clipped:false,items:[
          {id:"danish",title:"Dansk",text:"Husk læsebogen",date:request.week+"T08:00:00+02:00",end:request.week+"T08:45:00+02:00",children:["freja"],all_day:false},
          {id:"support",title:"0A støtte",text:"Ekstra voksen",date:request.week+"T06:00:00Z",end:request.week+"T06:45:00Z",children:["freja"],all_day:false},
          {id:"math",title:"Matematik",text:"",date:request.week+"T09:00:00+02:00",end:request.week+"T09:45:00+02:00",children:["oscar"],all_day:false}]};
        window.weekCalls ||= [];
        weekCalls.push(request);
        return {week:request.week,items:[{...plan,date:request.week,children:["freja","oscar"]}],unmapped:0,clipped:false};
      },
      callService: async (...args) => {
        calls.push(args);
      },
      callApi: async (method, url) => [
        {
          summary: "Fælles morgenmad",
          description: "Tag en kop med.",
          start: { date: day(2) },
          end: { date: day(3) },
        },
      ],
    };
  });
  await page.addScriptTag({
    content: fs.readFileSync(
      path.join(root, "custom_components/zenbi/frontend/zenbi-card.js"),
      "utf8",
    ),
  });
  await page.evaluate(() => {
    const card = document.createElement("zenbi-card");
    card.id = "card";
    window.card = card;
    card.setConfig({ type: "custom:zenbi-card", max_items: 2 });
    card.hass = hass;
    document.body.append(card);
  });
  const card = page.locator("#card");
  await card.getByRole("button", { name: "Freja", exact: true }).waitFor();
  assert.equal(await card.locator(".number").first().textContent(), "3");
  assert.equal(
    await card.locator(".number").nth(2).textContent(),
    "1",
    "Shared weekly plan is deduplicated",
  );
  await card
    .getByRole("button", { name: "Opdater Zenbi", exact: true })
    .click();
  assert.equal(await page.evaluate(() => calls[0][0]), "button");
  await card.getByRole("button", { name: "Freja", exact: true }).click();
  assert.equal(await card.locator(".number").first().textContent(), "1");
  assert.equal(
    await card.locator(".item-title").first().textContent(),
    "Læs kapitel 4 i læsebogen",
  );
  assert.equal(
    await card.locator(".item").count(),
    1,
    "Other child homework is not displayed",
  );
  await card.locator("summary").click();
  assert.equal(await card.locator("details[open]").count(), 1);
  await page.evaluate(() => {
    card.hass = {
      ...hass,
      states: { ...hass.states, "sensor.unrelated": { state: "on" } },
    };
  });
  assert.equal(
    await card.locator("details[open]").count(),
    1,
    "State updates preserve expanded text",
  );
  await card.locator("nav button[data-tab=messages]").click();
  assert.equal(
    await card.locator(".item-title").textContent(),
    "Information om efterårsugen",
  );
  await card.locator("nav button[data-tab=calendar]").click();
  await card.getByText("Fælles morgenmad", { exact: true }).waitFor();
  await card.getByRole("button", { name: "Oscar", exact: true }).click();
  await card.getByText("Fælles morgenmad", { exact: true }).waitFor();
  // A late response for Freja must not replace Oscar's calendar after a fast switch.
  await page.evaluate(() => {
    window.originalApi = hass.callApi;
    card._hass = {
      ...hass,
      callApi: (method, url) =>
        url.includes("demo_freja")
          ? new Promise((resolve) => (window.resolveFreja = resolve))
          : Promise.resolve([
              {
                summary: "Oscar kalender",
                start: { date: "2026-10-12" },
                end: { date: "2026-10-13" },
              },
            ]),
    };
  });
  await card.getByRole("button", { name: "Freja", exact: true }).click();
  await card.getByRole("button", { name: "Oscar", exact: true }).click();
  await card.getByText("Oscar kalender", { exact: true }).waitFor();
  await page.evaluate(() =>
    resolveFreja([
      {
        summary: "Freja forsinket",
        start: { date: "2026-10-12" },
        end: { date: "2026-10-13" },
      },
    ]),
  );
  assert.equal(
    await card.getByText("Freja forsinket", { exact: true }).count(),
    0,
  );
  await page.evaluate(() => {
    card._hass = hass;
  });
  await card.locator("nav button[data-tab=homework]").click();
  await page.evaluate(() => {
    const next = { ...hass.states };
    next["sensor.demo_homework_oscar"] = {
      ...next["sensor.demo_homework_oscar"],
      state: "unavailable",
    };
    card.hass = { ...hass, states: next };
  });
  assert.equal(await card.locator(".number").first().textContent(), "—");
  assert.match(await card.locator(".notice").textContent(), /utilgængelig/);
  await page.evaluate(() => {
    card.hass = hass;
    states["sensor.demo_homework_oscar"].attributes.items[0].title =
      '<img src=x onerror="window.injected=true">';
    card.hass = {
      ...hass,
      states: {
        ...states,
        "sensor.demo_homework_oscar": {
          ...states["sensor.demo_homework_oscar"],
        },
      },
    };
  });
  assert.equal(
    await card.locator(".item-title img").count(),
    0,
    "API text never renders HTML",
  );
  assert.equal(await page.evaluate(() => window.injected), undefined);
  const supportCases = await page.evaluate(() => {
    const base = {date:"2026-10-12T08:00:00+02:00",end:"2026-10-12T08:45:00+02:00",all_day:false,text:""};
    const input = [{...base,id:"shared",title:"Naturfag",children:["freja","oscar"]},
      {...base,id:"support",title:"0A STØTTE",text:"En voksen hjælper",children:["freja"]},
      {...base,id:"unmatched",title:"2A støtte",date:"2026-10-12T09:00:00+02:00",end:"2026-10-12T09:45:00+02:00",children:["oscar"]}];
    const before = JSON.stringify(input);
    const output = mergeTimetableSupport(input);
    const mismatch = mergeTimetableSupport([{...base,id:"lesson",title:"Musik",children:["freja"]},
      {...base,id:"short",title:"Støtte",end:"2026-10-12T08:15:00+02:00",children:["freja"]}]);
    return {output, unchanged:before===JSON.stringify(input), mismatchCount:mismatch.length};
  });
  assert.equal(supportCases.unchanged, true, "Card does not mutate original calendar data");
  assert.equal(supportCases.output.length, 3);
  assert.deepEqual(supportCases.output.find(row => row.title === "Naturfag m. Støtte").children, ["freja"]);
  assert.deepEqual(supportCases.output.find(row => row.title === "Naturfag").children, ["oscar"]);
  assert.equal(supportCases.output.find(row => row.id === "unmatched").title, "2A støtte");
  assert.equal(supportCases.mismatchCount, 2, "Different end times do not merge");
  // School timetable is a separate topic with timed rows and child filtering.
  await card.getByRole("button", {name:"Alle børn",exact:true}).click();
  await card.locator("nav button[data-tab=timetable]").click();
  await page.evaluate(() => {card._week="2026-10-12";card._render();card._loadWeek(true);});
  await card.getByText("Dansk m. Støtte", {exact:true}).waitFor();
  assert.equal(await card.locator(".lesson").count(), 2, "Support and matching lesson form one row");
  assert.equal(await card.getByText("0A støtte", {exact:true}).count(), 0);
  assert.equal(await card.locator(".lesson-time strong").first().textContent(), "08:00");
  assert.equal(await card.locator(".timetable-day").count(), 5, "Empty school weekdays remain visible");
  await card.getByRole("button", {name:"Freja",exact:true}).click();
  assert.equal(await card.locator(".lesson").count(), 1);
  assert.equal(await card.getByText("Matematik", {exact:true}).count(), 0, "Other child lessons are excluded");
  await card.locator(".lesson summary").click();
  assert.match(await card.locator(".lesson[open] .body").textContent(), /Husk læsebogen/);
  assert.match(await card.locator(".lesson[open] .body").textContent(), /Ekstra voksen/);
  assert.equal(await card.locator(".week-picker").count(), 1);
  if (process.env.ZENBI_SCREENSHOTS) {
    fs.mkdirSync(path.join(root,"docs/images"),{recursive:true});
    await card.screenshot({path:path.join(root,"docs/images/zenbi-timetable.png")});
  }
  await card.getByRole("button", {name:"Oscar",exact:true}).click();
  // Week switching crosses ISO years and fetches data outside the sensor range.
  await card.locator("nav button[data-tab=weekly_plans]").click();
  await card.getByText("Ugeplan", {exact:true}).last().waitFor();
  await page.evaluate(() => {card._week="2026-12-28";card._render();card._loadWeek();});
  await card.locator('.week-chip[aria-pressed=true]').getByText("Uge 53", {exact:true}).waitFor();
  await card.getByRole("button", {name:"Næste uge",exact:true}).click();
  await card.locator('.week-chip[aria-pressed=true]').getByText("Uge 1", {exact:true}).waitFor();
  assert.equal(await page.evaluate(() => weekCalls.at(-1).week), "2027-01-04");
  await card.getByRole("button", {name:"Forrige uge",exact:true}).click();
  await card.locator('.week-chip[aria-pressed=true]').getByText("Uge 53", {exact:true}).waitFor();
  await card.getByRole("button", {name:"Denne uge",exact:true}).click();
  // A late week response must not replace the currently selected week.
  await page.evaluate(() => {
    window.originalWS = hass.callWS;
    card._hass = {...hass,callWS: request => request.week === "2026-12-28"
      ? new Promise(resolve => window.resolveOldWeek = resolve)
      : originalWS(request)};
    card._week="2026-12-28";card._render();card._loadWeek(true);
  });
  await card.getByRole("button", {name:"Næste uge",exact:true}).click();
  await page.evaluate(() => resolveOldWeek({week:"2026-12-28",items:[{id:"old",title:"Gammel uge",children:["oscar"]}]}));
  assert.equal(await card.getByText("Gammel uge", {exact:true}).count(), 0);
  assert.equal(await page.evaluate(() => card._weeklyData.week), "2027-01-04");
  await page.evaluate(() => {card._hass=hass;});
  await card.getByRole("button", {name:"Denne uge",exact:true}).click();
  await card.locator("nav button[data-tab=homework]").click();
  // Editor sends a valid config-changed event.
  await page.evaluate(() => {
    const editor = customElements.get("zenbi-card").getConfigElement();
    editor.setConfig({ type: "custom:zenbi-card" });
    editor.hass = hass;
    editor.addEventListener(
      "config-changed",
      (e) => (window.editorConfig = e.detail.config),
    );
    document.body.append(editor);
  });
  await page
    .locator("zenbi-card-editor input[data-key=title]")
    .fill("Familiens skole");
  await page.evaluate(() => {
    document.querySelector("zenbi-card-editor").hass = { ...hass };
  });
  assert.equal(
    await page.locator("zenbi-card-editor input[data-key=title]").inputValue(),
    "Familiens skole",
  );
  await page.locator("zenbi-card-editor input[data-key=title]").blur();
  assert.equal(
    await page.evaluate(() => editorConfig.title),
    "Familiens skole",
  );
  assert.equal(await card.locator("button[data-child=freja] .avatar img").getAttribute("src"), "/zenbi-card/icon.png?zenbi",
    "Zenbi child picture is used by default");
  await page.locator("zenbi-card-editor select[data-person-child=freja]").selectOption("person.demo_freja");
  assert.equal(await page.evaluate(() => editorConfig.persons.freja), "person.demo_freja",
    "Editor stores the child's selected HA person");
  await page.evaluate(() => {
    card.setConfig({type:"custom:zenbi-card",persons:{freja:"person.demo_freja"}});
    card.hass = hass;
  });
  assert.equal(await card.locator("button[data-child=freja] .avatar img").getAttribute("src"), "/zenbi-card/icon.png");
  assert.equal(await card.locator("button[data-child=freja] .child-class").textContent(), "2.A");
  await page.evaluate(() => {
    const states = {...hass.states,"person.demo_freja":{state:"home",attributes:{entity_picture:"/zenbi-card/icon.png?updated"}}};
    card.hass = {...hass,states};
  });
  assert.equal(await card.locator("button[data-child=freja] .avatar img").getAttribute("src"), "/zenbi-card/icon.png?updated",
    "Person-only state changes update the photo");
  for (const topic of ["homework", "timetable", "messages", "weekly_plans", "posts"])
    await page.locator(`zenbi-card-editor input[data-topic=${topic}]`).uncheck();
  assert.deepEqual(await page.evaluate(() => editorConfig.topics), ["calendar"],
    "Editor saves the selected topics");
  assert.equal(await page.locator("zenbi-card-editor input[data-topic=calendar]").isDisabled(), true,
    "At least one topic must stay selected");
  await page.evaluate(() => {
    card.setConfig({type:"custom:zenbi-card", topics:["calendar", "messages"]});
    card.hass = hass;
  });
  await card.getByText("Fælles morgenmad", {exact:true}).waitFor();
  assert.equal(await card.locator("nav button").count(), 2);
  assert.equal(await card.locator("nav button[aria-pressed=true]").getAttribute("data-tab"), "calendar",
    "A hidden active tab falls back to a visible one");
  assert.equal(await card.locator(".stat").count(), 1, "Hidden topics have no counters");
  await page.evaluate(() => card.setConfig({type:"custom:zenbi-card",topics:["messages"]}));
  assert.equal(await card.locator("nav button").count(), 1);
  assert.equal(await card.locator(".children").count(), 0, "Common-only topics need no child filter");
  await page.evaluate(() => card.setConfig({type:"custom:zenbi-card",topics:["calendar"]}));
  assert.equal(await card.locator(".stats").count(), 0, "No empty stats row on a calendar-only card");
  assert.match(await page.evaluate(() => {
    try {card.setConfig({type:"custom:zenbi-card",topics:[]});}
    catch (error) {return error.message;}
  }), /mindst ét/);
  await page.evaluate(() => card.setConfig({type:"custom:zenbi-card",show_posts:false}));
  assert.equal(await card.locator("nav button[data-tab=posts]").count(), 0,
    "Legacy show_posts remains supported");
  await page.locator("zenbi-card-editor select[data-key=default_child]").selectOption("freja");
  assert.equal(await page.evaluate(() => editorConfig.default_child), "freja");
  await page.evaluate(() => {
    card.setConfig({type:"custom:zenbi-card",default_child:"freja"});
    card._tab = "homework";
    card._render();
  });
  await card.locator("button[data-child=freja].active").waitFor();
  assert.equal(await card.locator("button[data-child=all].active").count(), 0);
  await card.locator("button[data-child=oscar]").click();
  await page.evaluate(() => { card.hass = {...hass}; card._render(); });
  assert.equal(await card.locator("button[data-child=oscar].active").count(), 1,
    "Live updates preserve manual selection");
  await page.evaluate(() => {card.remove(); document.body.append(card);});
  await card.locator("button[data-child=freja].active").waitFor();
  await page.evaluate(() => {
    window.otherCard = document.createElement("zenbi-card");
    otherCard.setConfig({type:"custom:zenbi-card",default_child:"oscar"});
    otherCard.hass = hass;
    document.body.append(otherCard);
  });
  await page.locator("zenbi-card").nth(1).locator("button[data-child=oscar].active").waitFor();
  assert.equal(await card.locator("button[data-child=freja].active").count(), 1,
    "Each popup/card has its own default");
  await page.evaluate(() => otherCard.remove());
  await page.evaluate(() => card.setConfig({type:"custom:zenbi-card",default_child:"missing"}));
  assert.equal(await page.evaluate(() => card._view().active.id), "all",
    "Removed children fall back to all without changing config");
  await page.evaluate(() => card.setConfig({type:"custom:zenbi-card",default_child:"freja",children:[
    {id:"freja",name:"Freja",homework_entity:"sensor.demo_homework_freja"}]}));
  assert.equal(await page.evaluate(() => card._view().active.id), "freja");
  await page.locator("zenbi-card-editor select[data-key=default_child]").selectOption("");
  assert.equal(await page.evaluate(() => editorConfig.default_child), undefined);
  await page.evaluate(() => {
    card.setConfig({type:"custom:zenbi-card",max_items:2});
    card._tab = "homework";
    card._render();
  });
  await page.evaluate(() => {
    document.querySelector("zenbi-card-editor").remove();
    states["sensor.demo_homework_oscar"].attributes.items[0].title =
      "Matematik · plus og minus";
    card.hass = { ...hass, states: { ...states } };
    card._selected = "all";
    card._showAll = true;
    card._render();
  });
  if (process.env.ZENBI_SCREENSHOTS) {
    fs.mkdirSync(path.join(root, "docs/images"), { recursive: true });
    await card.screenshot({
      path: path.join(root, "docs/images/zenbi-card-light.png"),
    });
  }
  await page.setViewportSize({ width: 360, height: 1050 });
  await page.evaluate(() => {
    document.body.style.padding = "12px";
  });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
    true,
    "No mobile page overflow",
  );
  await card.getByRole("button", { name: "Freja", exact: true }).click();
  await page.evaluate(() => {
    document.body.style.setProperty("--ha-card-background", "#19252e");
    document.body.style.setProperty("--primary-text-color", "#e6eef4");
    document.body.style.setProperty("--secondary-text-color", "#98a9b7");
    document.body.style.setProperty("--divider-color", "#2e3c46");
    document.body.style.background = "#101a22";
  });
  if (process.env.ZENBI_SCREENSHOTS)
    await card.screenshot({
      path: path.join(root, "docs/images/zenbi-card-dark-mobile.png"),
    });
  const nav = card.locator("nav");
  assert.equal(await nav.evaluate(node => node.scrollWidth > node.clientWidth), true,
    "Mobile tabs use horizontal scrolling");
  const navTop = (await nav.boundingBox()).y;
  for (const tab of await card.locator("nav button").all()) {
    await tab.click();
    const box = await tab.boundingBox();
    assert.ok(box.x >= 0 && box.x + box.width <= 360, "Each tab can be scrolled into view");
    assert.ok(Math.abs((await nav.boundingBox()).y - navTop) <= 1,
      "Horizontal tab scrolling keeps the page position");
    if (await tab.getAttribute("data-tab") === "weekly_plans")
      assert.equal(await card.locator(".item-title").textContent(), "Ugeplan",
        "Legacy weekly_plans titles display in Danish");
  }
  assert.ok(await nav.evaluate(node => node.scrollLeft) > 0, "The tab row scrolls horizontally");
  assert.equal(
    await card.getByRole("button", { name: "Freja", exact: true }).count(),
    1,
    "Long child names use first name",
  );
  // Regression: tabs below other dashboard cards keep both focus and scroll.
  await page.setViewportSize({ width: 600, height: 950 });
  await page.evaluate(() => {
    const above = document.createElement("div");
    above.style.height = "1400px";
    const below = document.createElement("div");
    below.style.height = "1600px";
    document.body.prepend(above);
    document.body.append(below);
    window.scrollBy(
      0,
      card.shadowRoot.querySelector("nav").getBoundingClientRect().top - 220,
    );
  });
  const checkSwitch = async (tab, nested) => {
    const before = await page.evaluate(
      ({ tab, nested }) => {
        const button = card.shadowRoot.querySelector(
          `nav button[data-tab=${tab}]`,
        );
        window.clickedTab = button;
        return {
          top: button.getBoundingClientRect().top,
          scroll: nested ? window.dashboardScroller.scrollTop : window.scrollY,
        };
      },
      { tab, nested },
    );
    await card.locator(`nav button[data-tab=${tab}]`).click();
    await page.waitForTimeout(80);
    const after = await page.evaluate(
      ({ tab, nested }) => ({
        top: card.shadowRoot
          .querySelector(`nav button[data-tab=${tab}]`)
          .getBoundingClientRect().top,
        scroll: nested ? window.dashboardScroller.scrollTop : window.scrollY,
        sameButton:
          clickedTab ===
          card.shadowRoot.querySelector(`nav button[data-tab=${tab}]`),
        focused: card.shadowRoot.activeElement === clickedTab,
      }),
      { tab, nested },
    );
    assert.equal(after.sameButton, true, "Tab DOM identity survives rendering");
    assert.equal(after.focused, true, "Clicked tab keeps keyboard focus");
    assert.ok(
      Math.abs(after.top - before.top) <= 1,
      `Tab ${tab} stays in view`,
    );
    assert.ok(
      Math.abs(after.scroll - before.scroll) <= 1,
      "Dashboard does not scroll on tab switch",
    );
  };
  for (const tab of [
    "posts",
    "weekly_plans",
    "homework",
    "messages",
    "calendar",
  ])
    await checkSwitch(tab, false);
  await page.evaluate(() => {
    const host = document.createElement("div");
    host.style.cssText = "position:fixed;inset:0;background:white";
    const shadow = host.attachShadow({ mode: "open" });
    const scroller = document.createElement("div");
    scroller.style.cssText =
      "height:100%;overflow:auto;padding:12px;box-sizing:border-box";
    scroller.innerHTML = '<div style="height:1400px"></div>';
    scroller.append(card);
    const below = document.createElement("div");
    below.style.height = "1600px";
    scroller.append(below);
    shadow.append(scroller);
    document.body.append(host);
    window.dashboardScroller = scroller;
    scroller.scrollTop +=
      card.shadowRoot.querySelector("nav").getBoundingClientRect().top - 220;
  });
  for (const tab of ["posts", "weekly_plans", "homework", "messages"])
    await checkSwitch(tab, true);
  await page.evaluate(() => {
    card._calendarKey = null;
    card._hass = {
      ...hass,
      callApi: () =>
        new Promise((resolve) => (window.resolveCalendar = resolve)),
    };
  });
  await checkSwitch("calendar", true);
  // A late API response must preserve where the user has since scrolled.
  const currentScroll = await page.evaluate(() => {
    dashboardScroller.scrollTop += 45;
    const position = dashboardScroller.scrollTop;
    resolveCalendar([
      {
        summary: "Forsinket kalender",
        start: { date: "2026-10-12" },
        end: { date: "2026-10-13" },
      },
    ]);
    return position;
  });
  await card.getByText("Forsinket kalender", { exact: true }).waitFor();
  assert.equal(
    await page.evaluate(() => dashboardScroller.scrollTop),
    currentScroll,
    "Async response preserves current scroll, not the position before the request",
  );
  assert.deepEqual(errors, []);
  await browser.close();
  console.log(
    "Zenbi card: discovery, child filtering, deduplication, calendar, unavailable states, escaping, editor and mobile layout passed.",
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
