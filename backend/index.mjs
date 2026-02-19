const SL_BASE = 'https://transport.integration.sl.se/v1';

function respond(statusCode, body) {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(body),
  };
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`SL API returned ${res.status}`);
  return res.json();
}

// GET /api/sites?q=central
export const searchSites = async (event) => {
  const query = event.queryStringParameters?.q;
  if (!query || query.length < 2) {
    return respond(400, { error: 'Query parameter "q" must be at least 2 characters' });
  }

  try {
    const data = await fetchJson(`${SL_BASE}/sites?expand=true`);
    const filtered = data
      .filter((site) => site.name.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 15)
      .map((site) => ({ id: site.id, name: site.name }));
    return respond(200, filtered);
  } catch (err) {
    console.error('searchSites error:', err);
    return respond(502, { error: 'Failed to fetch sites from SL API' });
  }
};

// GET /api/sites/{siteId}/departures
export const getDepartures = async (event) => {
  const siteId = event.pathParameters?.siteId;
  if (!siteId) {
    return respond(400, { error: 'Missing siteId' });
  }

  try {
    const data = await fetchJson(
      `${SL_BASE}/sites/${encodeURIComponent(siteId)}/departures`
    );
    const departures = (data.departures || []).slice(0, 30).map((d) => ({
      line: d.line?.designation || '',
      destination: d.destination || '',
      direction: d.direction,
      displayTime: d.display || '',
      expected: d.expected || d.scheduled || '',
      transportMode: d.line?.transport_mode || '',
      deviations: (d.deviations || []).map((dev) => dev.message),
    }));
    return respond(200, { siteId, departures });
  } catch (err) {
    console.error('getDepartures error:', err);
    return respond(502, { error: 'Failed to fetch departures from SL API' });
  }
};
