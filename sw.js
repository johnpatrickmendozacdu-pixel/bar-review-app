// Offline support. Cache the shell and the corpus so drills work on a plane.
// Bump CACHE when app files change, so browsers pick up the new version.
const CACHE = "barrev-v3";

// Precache only what the app needs to start. corpus/provisions.json is
// several megabytes and is fetched lazily when Search is opened; corpus
// cases are never sent to the browser at all.
const SHELL = [
  "./",
  "./index.html",
  "./app/app.js",
  "./app/sm2.js",
  "./app/store.js",
  "./app/session.js",
  "./app/progress.js",
  "./app/render.js",
  "./app/style.css",
  "./bank/questions.json",
  "./corpus/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

// Network-first, falling back to cache: you get fresh law when online and a
// working app when not. A stale corpus is better than no corpus.
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match("./index.html")))
  );
});
