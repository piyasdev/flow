const BASE = "https://technocore.chat";
const ROOMS = ["lobby", "technocore", "events"];

async function fetchJson(path) {
  const res = await fetch(BASE + path, {
    headers: { Accept: "application/json", "User-Agent": "TechnocorePulse/1.0" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return res.json();
}

async function roomStats(room) {
  try {
    const data = await fetchJson(`/r/${room}?format=json&limit=100`);
    const msgs = Array.isArray(data) ? data : data.messages || [];
    let verified = 0;
    const dids = new Set();
    for (const m of msgs) {
      const from = String(m.from || "");
      if (from.startsWith("did:key:")) {
        verified += 1;
        dids.add(from);
      }
    }
    return {
      room,
      messages_in_window: msgs.length,
      verified_signed: verified,
      unique_dids: dids.size,
      error: null,
    };
  } catch (e) {
    return { room, messages_in_window: 0, verified_signed: 0, unique_dids: 0, error: String(e) };
  }
}

export default async function handler(req, res) {
  // CORS: allow the dashboard (and anyone) to read stats
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=300");

  try {
    const rooms = await Promise.all(ROOMS.map(roomStats));
    res.status(200).json({
      ok: true,
      ts: new Date().toISOString(),
      rooms,
    });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
}
