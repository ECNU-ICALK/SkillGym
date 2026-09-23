const providerCache = new Map();

function cacheToken(value) {
  return String(value || "");
}

function loadProvider(cacheKey, instanceKey, buildProvider) {
  const compositeKey = `${cacheKey}::${cacheToken(instanceKey)}`;
  if (providerCache.has(compositeKey)) {
    return providerCache.get(compositeKey);
  }

  const provider = buildProvider();
  providerCache.set(compositeKey, provider);
  return provider;
}

module.exports = {
  loadProvider,
};
