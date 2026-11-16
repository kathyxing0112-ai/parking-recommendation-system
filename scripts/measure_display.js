// Lab Manual §10.4 / SR-13: time from sending the confirmed trip request to
// the primary and backup recommendations being painted on the page.
//
// scripts/measure_uc1.py --http stops when the client has read the reply.
// SR-13 ends when both options are displayed, so this script measures the
// same interval in a real browser, through the page's own code path:
// search(trip) -> POST /api/confirm -> renderResults(result).
//
// How to run (no product code changes):
//   1. python web_app.py, open http://127.0.0.1:8000 in a browser, and open
//      the Plan Your Trip popup so the results view is on screen.
//   2. Paste this file into the browser console, then run, for example:
//        await measureDisplay(REQUESTS, { runs: 50, gapMs: 2000 })
//      where REQUESTS is the "requests" array of measurements/uc1_requests.json.
//   3. The function returns one row per run; copy them out as JSON.
//
// Per run:
//   fetch_ms    request start to last response byte (Resource Timing for /api/confirm)
//   dom_ms      search() called until renderResults() has written the cards
//   display_ms  search() called until the browser has painted the frame with
//               the cards: two requestAnimationFrame callbacks, the second of
//               which runs after the frame containing the new cards was drawn
//   cards       number of recommendation cards on the page after the run
// gapMs waits before each run, so requests are spaced like a driver's
// (Section 4.4 of the report: spacing changes server time).
async function measureDisplay(requests, { runs = 50, gapMs = 0 } = {}) {
  const pad = (n) => String(n).padStart(2, "0");
  const isoLocal = (d) => {
    const off = -d.getTimezoneOffset();
    const sign = off >= 0 ? "+" : "-";
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00` +
      `${sign}${pad(Math.floor(Math.abs(off) / 60))}:${pad(Math.abs(off) % 60)}`;
  };
  const nextPaint = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const cards = document.getElementById("cards");
  const rows = [];
  for (let i = 0; i < runs; i++) {
    const request = requests[i % requests.length];
    const form = request.form;
    const start = new Date();
    start.setSeconds(0, 0);
    const arrive = new Date(start.getTime() + form.arrive_in_minutes * 60000);
    const leave = new Date(arrive.getTime() + form.stay_minutes * 60000);
    const trip = {
      destination: form.destination,
      arrival_time: isoLocal(arrive),
      departure_time: isoLocal(leave),
      vehicle_category: form.vehicle_category,
      declared_eligibility: form.declared_eligibility,
      access_needs: form.access_needs,
    };
    if (gapMs) await new Promise((resolve) => setTimeout(resolve, gapMs));
    cards.innerHTML = "";
    performance.clearResourceTimings();
    const t0 = performance.now();
    await search(trip); // the page's own function: POST /api/confirm, then renderResults
    const tDom = performance.now();
    await nextPaint();
    const tPaint = performance.now();
    const res = performance.getEntriesByType("resource").filter((e) => e.name.endsWith("/api/confirm")).pop();
    rows.push({
      run: i + 1,
      request_id: request.id,
      fetch_ms: res ? +(res.responseEnd - res.startTime).toFixed(1) : null,
      dom_ms: +(tDom - t0).toFixed(1),
      display_ms: +(tPaint - t0).toFixed(1),
      cards: cards.querySelectorAll("article.card").length,
      results_visible: !document.getElementById("results-view").hidden && !document.getElementById("plan-overlay").hidden,
    });
  }
  return rows;
}
