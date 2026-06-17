const providerCache = new Map();

function loadProvider(cacheKey, buildProvider) {
  if (providerCache.has(cacheKey)) {
    return providerCache.get(cacheKey);
  }

  const provider = buildProvider();
  providerCache.set(cacheKey, provider);
  return provider;
}

module.exports = {
  loadProvider,
};
