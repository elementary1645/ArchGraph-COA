// Isolated optional parser check, not a browser rendering claim.
// Usage: node check_mermaid.mjs /absolute/path/to/node_modules diagrams.md
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [modules, document] = process.argv.slice(2);
if (!modules || !document) throw new Error('Expected node_modules directory and Markdown document');
const { JSDOM } = await import(pathToFileURL(path.join(modules, 'jsdom/lib/api.js')));
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import(pathToFileURL(path.join(modules, 'mermaid/dist/mermaid.esm.mjs')));
mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
const blocks = [...fs.readFileSync(document, 'utf8').matchAll(/```mermaid\n([\s\S]*?)```/g)];
if (blocks.length !== 7) throw new Error(`Expected seven diagrams, got ${blocks.length}`);
for (const [index, block] of blocks.entries()) {
    await mermaid.parse(block[1]);
    process.stdout.write(`Diagram ${index + 1}: Mermaid syntax accepted\n`);
}
const version = JSON.parse(fs.readFileSync(path.join(modules, 'mermaid/package.json'), 'utf8')).version;
process.stdout.write(`Mermaid ${version}: 7/7 parsed; no visual renderer/browser verification\n`);
