#!/usr/bin/env node
/**
 * @praxis/cli — thin wrapper that subprocesses `python -m praxis_core` with the same argv.
 *
 * The Python core is the canonical implementation in v0.1. This TS entry exists so that
 * `npm install -g @praxis/cli` provides a recognizable JavaScript entry point and so that
 * editor tooling can import @praxis/ir types alongside it.
 */
import { execa } from "execa";

async function main(): Promise<number> {
  const args = process.argv.slice(2);
  const pythonBin = process.env.PRAXIS_PYTHON ?? "python3";
  try {
    const result = await execa(pythonBin, ["-m", "praxis_core", ...args], {
      stdio: "inherit",
      reject: false,
    });
    return typeof result.exitCode === "number" ? result.exitCode : 1;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    process.stderr.write(
      `praxis: failed to invoke '${pythonBin} -m praxis_core'. ` +
        `Is praxis-core installed? ${message}\n`,
    );
    return 127;
  }
}

main().then((code) => process.exit(code));
