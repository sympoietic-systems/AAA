// Evaluate in the collaborative browser after a fresh navigation and settled requests.
// Reports bundle metadata only; deliberately excludes API bodies and credentials.
JSON.stringify({
  route: location.pathname,
  javascriptBytes: performance.getEntriesByType("resource")
    .filter(entry => new URL(entry.name).pathname.endsWith(".js"))
    .reduce((total, entry) => total + entry.decodedBodySize, 0),
  resources: performance.getEntriesByType("resource")
    .filter(entry => /\.(js|css)$/.test(new URL(entry.name).pathname))
    .map(entry => ({ file: new URL(entry.name).pathname.split("/").pop(),
      decodedBytes: entry.decodedBodySize, initiator: entry.initiatorType })),
})
