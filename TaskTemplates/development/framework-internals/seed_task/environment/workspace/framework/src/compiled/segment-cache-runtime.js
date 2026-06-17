function buildGroupKey(route) {
  const boundary = route.pathSegments.length > 4 ? 5 : route.pathSegments.length - 1;
  return route.pathSegments.slice(0, Math.max(boundary, 1)).join("/");
}

export function describeRouteGroups(routes, runtimeConfig) {
  const visibleRoutes = routes.slice(0, runtimeConfig.render.articleLimit);
  const groups = new Map();

  for (const route of visibleRoutes) {
    const key = buildGroupKey(route);
    const current = groups.get(key) || [];
    current.push(route.route);
    groups.set(key, current);
  }

  const topGroups = [...groups.entries()]
    .map(([key, members]) => ({
      key,
      size: members.length
    }))
    .sort((left, right) => right.size - left.size || left.key.localeCompare(right.key));

  const reusedSegmentCount = topGroups.reduce((sum, group) => sum + Math.max(group.size - 1, 0), 0);

  return {
    mode: "segment-cache",
    groupCount: topGroups.length,
    reusedSegmentCount,
    groupKeys: topGroups.map((group) => group.key),
    topGroups
  };
}
