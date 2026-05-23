/**
 * @praxis/ir — TypeScript types and zod schema mirroring schemas/praxis-ir.schema.json.
 *
 * The JSON Schema is authoritative. This module mirrors it for ergonomics in
 * TypeScript editor tooling and the CLI wrapper.
 */
import { z } from "zod";

export const NodeKind = z.enum([
  "tool",
  "skill",
  "workflow",
  "prompt",
  "memory_store",
  "scheduler",
  "service",
  "secret",
  "env",
]);
export type NodeKind = z.infer<typeof NodeKind>;

export const Capability = z.enum([
  "sequenceable",
  "branchable",
  "retriable",
  "scheduled",
  "stateful",
  "side_effecting",
  "llm_invoking",
  "http_callable",
  "memory_reading",
  "memory_writing",
  "user_facing",
  "external_dependency",
]);
export type Capability = z.infer<typeof Capability>;

export const EdgeKind = z.enum([
  "data",
  "control",
  "dependency",
  "trigger",
  "reads",
  "writes",
]);
export type EdgeKind = z.infer<typeof EdgeKind>;

export const PortabilityTier = z.enum([
  "portable",
  "partial",
  "needs_review",
  "unsupported",
]);
export type PortabilityTier = z.infer<typeof PortabilityTier>;

export const PortSpec = z.object({
  name: z.string(),
  type: z.string().optional(),
  required: z.boolean().default(true),
  default: z.unknown().optional(),
  env: z.string().optional(),
  description: z.string().optional(),
});
export type PortSpec = z.infer<typeof PortSpec>;

export const SideEffect = z.object({
  kind: z.enum(["network", "filesystem", "subprocess", "database", "messaging", "secret_access", "unknown"]),
  target: z.string().optional(),
  description: z.string().optional(),
});
export type SideEffect = z.infer<typeof SideEffect>;

export const Intent = z.object({
  description: z.string(),
  confidence: z.number().min(0).max(1),
  evidence: z.array(z.string()).default([]),
  source: z.string().default("static"),
});
export type Intent = z.infer<typeof Intent>;

export const Provenance = z.object({
  framework: z.string(),
  source_file: z.string().optional(),
  source_span: z
    .object({ start_line: z.number().int().optional(), end_line: z.number().int().optional() })
    .optional(),
  original_kind: z.string().optional(),
});
export type Provenance = z.infer<typeof Provenance>;

export const Portability = z.object({
  score: z.number().min(0).max(1),
  tier: PortabilityTier,
  rationale: z.string().optional(),
  blockers: z.array(z.string()).default([]),
});
export type Portability = z.infer<typeof Portability>;

export const Node = z.object({
  id: z.string().regex(/^[a-zA-Z_][a-zA-Z0-9_:.-]*$/),
  kind: NodeKind,
  name: z.string(),
  description: z.string().optional(),
  capabilities: z.array(Capability).default([]),
  inputs: z.array(PortSpec).default([]),
  outputs: z.array(PortSpec).default([]),
  side_effects: z.array(SideEffect).default([]),
  intent: Intent.optional(),
  provenance: Provenance,
  portability: Portability.optional(),
  metadata: z.record(z.unknown()).default({}),
});
export type Node = z.infer<typeof Node>;

export const Edge = z.object({
  from: z.string(),
  to: z.string(),
  kind: EdgeKind,
  condition: z.string().optional(),
  label: z.string().optional(),
});
export type Edge = z.infer<typeof Edge>;

export const Diagnostic = z.object({
  level: z.enum(["info", "warn", "error"]),
  message: z.string(),
  node_id: z.string().optional(),
  code: z.string().optional(),
  hint: z.string().optional(),
});
export type Diagnostic = z.infer<typeof Diagnostic>;

export const IRGraph = z.object({
  praxis_ir_version: z.literal("0.1"),
  project: z
    .object({
      name: z.string().optional(),
      source_framework: z.enum(["openclaw", "hermes", "unknown"]).optional(),
      source_root: z.string().optional(),
      analyzed_at: z.string().optional(),
    })
    .optional(),
  nodes: z.array(Node).default([]),
  edges: z.array(Edge).default([]),
  diagnostics: z.array(Diagnostic).default([]),
});
export type IRGraph = z.infer<typeof IRGraph>;

export const IR_VERSION = "0.1" as const;
