const { HttpError, dataPath } = require("./shared");
const { loadProvider } = require("./provider_loader");
const { createDemoStaticProvider } = require("./providers/demo_static");
const { createCityReferenceProvider } = require("./providers/city_reference");
const { createMtaStaticProvider } = require("./providers/mta_static");

function createRegistry({ dataRoot }) {
  const providers = [
    loadProvider("demo_static", dataPath(dataRoot, "providers/demo_static.json"), () =>
      createDemoStaticProvider({ filePath: dataPath(dataRoot, "providers/demo_static.json") })
    ),
    loadProvider("city_reference", dataPath(dataRoot, "providers/city_reference.json"), () =>
      createCityReferenceProvider({ filePath: dataPath(dataRoot, "providers/city_reference.json") })
    ),
    loadProvider("mta_static", dataPath(dataRoot, "gtfs"), () =>
      createMtaStaticProvider({ dataRoot: dataPath(dataRoot, "gtfs") })
    ),
  ];

  const byId = new Map();
  for (const provider of providers) {
    byId.set(provider.id, provider);
  }

  return {
    listProviders() {
      return Array.from(byId.values());
    },
    mustGetProvider(id) {
      const provider = byId.get(id);
      if (!provider) {
        throw new HttpError(404, `unknown provider: ${id}`);
      }
      return provider;
    },
  };
}

module.exports = {
  createRegistry,
};
