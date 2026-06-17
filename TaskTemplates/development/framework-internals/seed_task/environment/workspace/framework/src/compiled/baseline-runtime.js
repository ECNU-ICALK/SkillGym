export function describeRouteGroups(routes, runtimeConfig) {
  const visibleRoutes = routes.slice(0, runtimeConfig.render.articleLimit);
  return {
    mode: "baseline",
    groupCount: visibleRoutes.length,
    reusedSegmentCount: 0,
    groupKeys: visibleRoutes.map((route) => route.route),
    topGroups: visibleRoutes.map((route) => ({
      key: route.route,
      size: 1
    }))
  };
}
