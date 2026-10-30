// openapi-typescript prints its output through the TypeScript 5 compiler API, which TypeScript 7
// (the app's compiler) no longer ships. Its `typescript` peer would resolve to the app's 7, so the
// generator gets a TypeScript 5 of its own instead (scripts/generate-api.sh).
module.exports = {
  hooks: {
    readPackage(pkg) {
      if (pkg.name === "openapi-typescript") {
        delete pkg.peerDependencies.typescript;
        pkg.dependencies = { ...pkg.dependencies, typescript: "^5.9.3" };
      }
      return pkg;
    },
  },
};
