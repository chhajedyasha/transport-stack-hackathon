/**
 * CrowdWise API Client
 * Centralized API calls with consistent error handling and standard envelope unwrapping.
 */

const BASE_URL = '/api';

export async function fetchApi(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    const json = await res.json();
    if (!res.ok || json.ok === false) {
      throw new Error(json.error?.message || `API error: ${res.status}`);
    }
    return json;
  } catch (err) {
    console.error(`API Request to ${url} failed:`, err);
    throw err;
  }
}

export async function checkHealth() {
  return fetchApi('/health');
}

export async function searchStops(query, limit = 8) {
  if (!query || query.trim().length === 0) return [];
  const res = await fetchApi(`/stops/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  if (Array.isArray(res.data)) return res.data;
  return res.data?.matches || [];
}

export async function planJourney({ originId, destId, departureTime, preference, date }) {
  const params = new URLSearchParams({
    origin_id: originId,
    dest_id: destId,
  });
  if (departureTime) params.append('departure_time', departureTime);
  if (preference) params.append('preference', preference);
  if (date) params.append('date', date);

  return fetchApi(`/journey/plan?${params.toString()}`);
}

export async function getRouteDetails(routeId) {
  return fetchApi(`/routes/${encodeURIComponent(routeId)}`);
}

export async function getRouteCrowdProfile(routeId, dayType = 'WEEKDAY') {
  return fetchApi(`/crowd/profile/${encodeURIComponent(routeId)}?day_type=${dayType}`);
}

export async function getAnalyticsSummary() {
  return fetchApi('/analytics/summary');
}

