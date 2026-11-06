export const reply = (data: unknown, status = 200) => Response.json(data, {
  status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
});
export const fallback = (message: string, status = 503) => reply({
  status: 'unavailable', fallback: 'static_daily', message,
}, status);
