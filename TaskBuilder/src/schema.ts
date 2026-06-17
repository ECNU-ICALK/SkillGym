import { z } from "zod";

type JsonSchemaNode = {
  type?: string;
  properties?: Record<string, JsonSchemaNode>;
  required?: readonly string[];
  items?: JsonSchemaNode | JsonSchemaNode[];
  anyOf?: readonly JsonSchemaNode[];
  oneOf?: readonly JsonSchemaNode[];
  allOf?: readonly JsonSchemaNode[];
};

function assertStructuredOutputCompatible(schema: JsonSchemaNode, label: string, trail = label): void {
  if (schema.type === "object" && schema.properties) {
    const propertyKeys = Object.keys(schema.properties);
    const requiredKeys = schema.required ?? [];
    if (requiredKeys.length !== propertyKeys.length || propertyKeys.some((key) => !requiredKeys.includes(key))) {
      throw new Error(`${trail} 的 required 必须覆盖 properties 中的全部字段: ${propertyKeys.join(", ")}`);
    }

    for (const [key, value] of Object.entries(schema.properties)) {
      assertStructuredOutputCompatible(value, label, `${trail}.properties.${key}`);
    }
  }

  if (schema.items) {
    const items = Array.isArray(schema.items) ? schema.items : [schema.items];
    for (const [index, item] of items.entries()) {
      assertStructuredOutputCompatible(item, label, `${trail}.items[${index}]`);
    }
  }

  for (const [keyword, variants] of [
    ["anyOf", schema.anyOf],
    ["oneOf", schema.oneOf],
    ["allOf", schema.allOf],
  ] as const) {
    for (const [index, variant] of (variants ?? []).entries()) {
      assertStructuredOutputCompatible(variant, label, `${trail}.${keyword}[${index}]`);
    }
  }
}

export const skillModeSchema = z.enum(["all", "per-skill"]);

export const plannedTaskSchema = z.object({
  title: z.string().min(1),
  realWorldContext: z.string().min(1),
  referenceData: z.string().min(1),
  taskGoal: z.string().min(1),
  inputAssets: z.string().min(1),
  requiredOutputs: z.string().min(1),
  verifierFocus: z.string().min(1),
  skillBenefitRationale: z.string().min(1),
  difficulty: z.string().min(1),
  category: z.string().min(1),
});

export const singleTaskPlanSchema = plannedTaskSchema;

export const derivedTaskPlanSchema = z.object({
  derivedTaskId: z.string().min(1),
  taskOrdinal: z.number().int().positive(),
  title: z.string().min(1),
  realWorldContext: z.string().min(1),
  referenceData: z.string().min(1),
  taskGoal: z.string().min(1),
  inputAssets: z.string().min(1),
  requiredOutputs: z.string().min(1),
  verifierFocus: z.string().min(1),
  skillBenefitRationale: z.string().min(1),
  difficulty: z.string().min(1),
  category: z.string().min(1),
  templateId: z.string().min(1),
  skillMode: skillModeSchema,
  targetSkillDirName: z.string(),
  targetSkillName: z.string(),
});

export const writerSummarySchema = z.object({
  derivedTaskId: z.string().min(1),
  draftRelativePath: z.string().min(1),
  filesWritten: z.array(z.string().min(1)).min(1),
  summary: z.string().min(1),
});

export const blockingReviewerTaskResultSchema = z.object({
  derivedTaskId: z.string().min(1),
  blockingPass: z.boolean(),
  blockingIssues: z.array(z.string()),
});

export const blockingReviewResultSchema = z.object({
  taskResults: z.array(blockingReviewerTaskResultSchema),
});

export const repairTurnResultSchema = z.object({
  summary: z.string().min(1),
  repairReason: z.string().min(1).optional(),
  changedFiles: z.array(z.string().min(1)),
});

export type PlannedTask = z.infer<typeof plannedTaskSchema>;
export type SingleTaskPlan = PlannedTask;
export type DerivedTaskPlan = z.infer<typeof derivedTaskPlanSchema>;
export type WriterSummary = z.infer<typeof writerSummarySchema>;
export type BlockingReviewerTaskResult = z.infer<typeof blockingReviewerTaskResultSchema>;
export type BlockingReviewResult = z.infer<typeof blockingReviewResultSchema>;
export type RepairTurnResult = z.infer<typeof repairTurnResultSchema>;

const plannedTaskJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: [
    "title",
    "realWorldContext",
    "referenceData",
    "taskGoal",
    "inputAssets",
    "requiredOutputs",
    "verifierFocus",
    "skillBenefitRationale",
    "difficulty",
    "category",
  ],
  properties: {
    title: { type: "string" },
    realWorldContext: { type: "string" },
    referenceData: { type: "string" },
    taskGoal: { type: "string" },
    inputAssets: { type: "string" },
    requiredOutputs: { type: "string" },
    verifierFocus: { type: "string" },
    skillBenefitRationale: { type: "string" },
    difficulty: { type: "string" },
    category: { type: "string" },
  },
} as const;

export const singleTaskPlanJsonSchema = plannedTaskJsonSchema;

export const writerSummaryJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: ["derivedTaskId", "draftRelativePath", "filesWritten", "summary"],
  properties: {
    derivedTaskId: { type: "string" },
    draftRelativePath: { type: "string" },
    filesWritten: {
      type: "array",
      items: { type: "string" },
    },
    summary: { type: "string" },
  },
} as const;

export const blockingReviewResultJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: ["taskResults"],
  properties: {
    taskResults: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["derivedTaskId", "blockingPass", "blockingIssues"],
        properties: {
          derivedTaskId: { type: "string" },
          blockingPass: { type: "boolean" },
          blockingIssues: {
            type: "array",
            items: { type: "string" },
          },
        },
      },
    },
  },
} as const;

export const repairTurnResultJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: ["summary", "repairReason", "changedFiles"],
  properties: {
    summary: { type: "string" },
    repairReason: { type: "string" },
    changedFiles: {
      type: "array",
      items: { type: "string" },
    },
  },
} as const;

assertStructuredOutputCompatible(writerSummaryJsonSchema, "writerSummaryJsonSchema");
assertStructuredOutputCompatible(blockingReviewResultJsonSchema, "blockingReviewResultJsonSchema");
assertStructuredOutputCompatible(repairTurnResultJsonSchema, "repairTurnResultJsonSchema");
