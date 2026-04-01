const runtimeConfig = globalThis.__RUNTIME_CONFIG__ || {};

export function getRuntimeConfig(key, fallback = "") {
  const value = runtimeConfig[key];
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  return fallback;
}
