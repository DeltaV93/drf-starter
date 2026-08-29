// Metro, taught about the workspace.
//
// Without the two settings below, `@app/shared` resolves to a symlink Metro
// does not watch and whose TypeScript it will not transform -- so the app
// builds once and then never picks up an edit to the shared route table, or
// fails outright on the first import. Neither failure names the monorepo.

const path = require('path');

const { getDefaultConfig } = require('expo/metro-config');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..');

const config = getDefaultConfig(projectRoot);

// Watch the whole workspace so an edit in packages/shared triggers a reload.
config.watchFolders = [workspaceRoot];

// Look in both places for modules: npm hoists most of the tree to the root,
// but anything version-pinned differently stays nested under mobile/.
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

// Resolve from those two paths only. Left on, Metro also walks every parent
// directory, which in a monorepo is how you end up with two copies of React
// loaded at once -- and the error that produces talks about hooks, not paths.
config.resolver.disableHierarchicalLookup = true;

module.exports = config;
